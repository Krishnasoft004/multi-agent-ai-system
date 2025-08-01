from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from typing import TypedDict, List, Dict, Any
import asyncio
from datetime import datetime
try:
    from db.db_utils import save_agent_output_to_db
except ImportError:
    save_agent_output_to_db = None


from .search_agent import SearchAgent
from .summary_agent import SummaryAgent
from .memory_agent import MemoryAgent
from memory.store import MemoryStore

class AgentState(TypedDict):
    session_id: str
    user_id: str
    user_message: str
    messages: List[Dict[str, Any]]
    tasks: List[Dict[str, Any]]
    current_plan: List[Dict[str, Any]]
    memory_context: Dict[str, Any]
    current_agent: str
    agent_output: Dict[str, Any]
    final_response: str

class CoordinatorAgent:
    def __init__(self, memory_store: MemoryStore):
        self.memory_store = memory_store
        self.search_agent = SearchAgent()
        self.summary_agent = SummaryAgent()
        self.memory_agent = MemoryAgent(memory_store)
    
    async def plan_tasks(self, state: AgentState) -> AgentState:
        """Planner agent - creates task plan and delegates"""
        user_message = state["user_message"]
        memory_context = state["memory_context"]
        
        # Emit planning event
        state["messages"].append({
            "type": "agent_thinking",
            "agent": "coordinator",
            "message": f"Planning tasks for: {user_message}",
            "timestamp": datetime.now().isoformat()
        })
        
        # Create task plan based on user message
        plan = await self._create_plan(user_message, memory_context)
        state["current_plan"] = plan
        state["current_agent"] = "coordinator"
        
        # Add plan to messages
        state["messages"].append({
            "type": "plan_created",
            "agent": "coordinator",
            "plan": plan,
            "timestamp": datetime.now().isoformat()
        })
           # DB Logging for Plan
        if save_agent_output_to_db:
            try:
                session_id = state.get("session_id", "unknown")
                task_id = "task_plan"
                output = {
                    "agent": "coordinator",
                    "task_plan": plan,
                    "status": "planned"
                }
                asyncio.create_task(save_agent_output_to_db(session_id, "coordinator", task_id, output))
            except Exception as e:
                print(f"[CoordinatorAgent] Failed to log task plan: {e}")
        
        return state
    
    async def delegate_task(self, state: AgentState) -> AgentState:
        """Delegate tasks to appropriate sub-agents"""
        current_plan = state["current_plan"]
        
        if not current_plan:
            state["current_agent"] = "complete"
            return state
        
        # Get next task
        next_task = current_plan[0]
        task_type = next_task.get("type", "search")
        
        state["messages"].append({
            "type": "task_delegation",
            "agent": "coordinator",
            "message": f"Delegating {task_type} task: {next_task['description']}",
            "timestamp": datetime.now().isoformat()
        })
        
        # Set current agent based on task type
        if task_type == "search":
            state["current_agent"] = "search"
        elif task_type == "summary":
            state["current_agent"] = "summary"
        elif task_type == "memory":
            state["current_agent"] = "memory"
        else:
            state["current_agent"] = "search"  # default
        
        return state
    
    async def _create_plan(self, user_message: str, memory_context: Dict) -> List[Dict]:
        """Create a task plan based on user input"""
        # Simple planning logic - in production, use LLM for planning
        plan = []
        
        if "search" in user_message.lower() or "find" in user_message.lower():
            plan.append({
                "id": "task_1",
                "type": "search",
                "description": f"Search for information about: {user_message}",
                "status": "pending"
            })
        
        if "summarize" in user_message.lower() or "summary" in user_message.lower():
            plan.append({
                "id": "task_2",
                "type": "summary",
                "description": f"Summarize findings for: {user_message}",
                "status": "pending"
            })
        
        # Always include memory task
        plan.append({
            "id": "task_memory",
            "type": "memory",
            "description": "Store conversation and results in memory",
            "status": "pending"
        })
        
        return plan

def create_agent_graph(memory_store: MemoryStore) -> StateGraph:
    """Create the LangGraph workflow"""
    coordinator = CoordinatorAgent(memory_store)
    search_agent = SearchAgent()
    summary_agent = SummaryAgent()
    memory_agent = MemoryAgent(memory_store)
    
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("planner", coordinator.plan_tasks)
    workflow.add_node("delegator", coordinator.delegate_task)
    workflow.add_node("search_agent", search_agent.execute)
    workflow.add_node("summary_agent", summary_agent.execute)
    workflow.add_node("memory_agent", memory_agent.execute)
    workflow.add_node("aggregator", aggregate_results)
    
    # Add edges
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "delegator")
    
    # Conditional routing from delegator
    workflow.add_conditional_edges(
        "delegator",
        route_to_agent,
        {
            "search": "search_agent",
            "summary": "summary_agent", 
            "memory": "memory_agent",
            "complete": "aggregator"
        }
    )
    
    # All agents go to aggregator
    workflow.add_edge("search_agent", "aggregator")
    workflow.add_edge("summary_agent", "aggregator")
    workflow.add_edge("memory_agent", "aggregator")
    
    # Aggregator can loop back to delegator or end
    workflow.add_conditional_edges(
        "aggregator",
        check_completion,
        {
            "continue": "delegator",
            "end": END
        }
    )
    
    return workflow.compile()

def route_to_agent(state: AgentState) -> str:
    """Route to appropriate agent based on current_agent"""
    return state["current_agent"]

async def aggregate_results(state: AgentState) -> AgentState:
    """Aggregate results from sub-agents"""
    # Mark current task as complete
    current_plan = state["current_plan"]
    if current_plan:
        current_plan[0]["status"] = "completed"
        current_plan[0]["completed_at"] = datetime.now().isoformat()
        
        # Add to tasks list
        state["tasks"].append(current_plan[0])
        
        # Remove from plan
        state["current_plan"] = current_plan[1:]
    
    state["messages"].append({
        "type": "task_completed",
        "agent": "coordinator",
        "message": "Task completed, checking for more tasks...",
        "timestamp": datetime.now().isoformat()
    })
    
    return state

def check_completion(state: AgentState) -> str:
    """Check if all tasks are complete"""
    if state["current_plan"]:
        return "continue"
    else:
        # Generate final response
        state["final_response"] = "All tasks completed successfully!"
        state["messages"].append({
            "type": "completion",
            "agent": "coordinator",
            "message": state["final_response"],
            "timestamp": datetime.now().isoformat()
        })

       
    # Log final response to DB
    if save_agent_output_to_db:
        try:
            session_id = state.get("session_id", "unknown")
            task_id = "final_response"
            output = {
                "agent": "coordinator",
                "final_message": state["final_response"],
                "status": "complete"
            }
            asyncio.create_task(save_agent_output_to_db(session_id, "coordinator", task_id, output))
        except Exception as e:
            print(f"[Completion] Failed to log final response: {e}")


        return "end"
