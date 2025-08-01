from .base_agent import BaseAgent
from typing import Dict, Any, List
import json
import asyncio

# Optional DB import
try:
    from db.db_utils import save_agent_output_to_db
except ImportError:
    save_agent_output_to_db = None

class CoordinatorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Coordinator",
            description="Coordinates tasks between multiple agents and creates execution plans"
        )
        self.available_agents = ["search", "summary", "memory", "analysis"]
    
    def create_plan(self, user_input: str) -> List[Dict[str, Any]]:
        """Create a plan for handling the user input"""
        try:
            planning_prompt = f"""
            User request: "{user_input}"
            
            Available agents: {', '.join(self.available_agents)}
            
            Create a step-by-step plan to handle this request. Return a JSON list of tasks.
            Each task should have: agent, action, description, priority (1-5).
            
            Example format:
            [
                {{"agent": "search", "action": "web_search", "description": "Search for information", "priority": 1}},
                {{"agent": "summary", "action": "summarize", "description": "Summarize findings", "priority": 2}}
            ]
            """
            
            system_prompt = "You are a task coordinator. Create efficient execution plans."
            response = self.get_llm_response(planning_prompt, system_prompt)
            
            # Try to parse JSON response
            try:
                plan = json.loads(response)
                if isinstance(plan, list):
                    return plan
            except json.JSONDecodeError:
                pass
            
            # Fallback plan
            return [
                {
                    "agent": "search",
                    "action": "research",
                    "description": f"Research information about: {user_input}",
                    "priority": 1
                },
                {
                    "agent": "analysis",
                    "action": "analyze",
                    "description": "Analyze the gathered information",
                    "priority": 2
                },
                {
                    "agent": "summary",
                    "action": "summarize",
                    "description": "Create a comprehensive summary",
                    "priority": 3
                }
            ]
            
        except Exception as e:
            self.logger.error(f"Plan creation error: {e}")
            return [{
                "agent": "search",
                "action": "basic_search",
                "description": f"Basic search for: {user_input}",
                "priority": 1
            }]

    async def log_plan_to_db(self, context: Dict[str, Any], plan: List[Dict[str, Any]]):
        """Save plan steps to DB collection"""
        if save_agent_output_to_db:
            try:
                session_id = context.get('session_id', 'unknown')
                task_id = context.get('task_id', 'coordinator-plan')
                result = {
                    'agent': self.name,
                    'task_plan': plan,
                    'status': 'created'
                }
                await save_agent_output_to_db(session_id, self.name, task_id, result)
                self.logger.info("Coordinator plan logged to DB")
            except Exception as e:
                self.logger.warning(f"CoordinatorAgent DB log failed: {e}")    
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process coordination request"""
        try:
            message = input_data.get('message', '')
            
            # Create execution plan
            plan = self.create_plan(message)
            
            coordination_response = f"""
            I've analyzed your request: "{message}"
            
            Here's my execution plan:
            """
            
            for i, task in enumerate(plan, 1):
                coordination_response += f"\n{i}. {task['agent'].title()} Agent: {task['description']}"
            
            coordination_response += "\n\nI'll coordinate with the other agents to execute this plan."
            
            result = {
                'agent': self.name,
                'response': coordination_response,
                'plan': plan,
                'status': 'completed',
                'context': input_data.get('context', {})
            }

            # Async log to DB
            if save_agent_output_to_db:
                asyncio.create_task(self.log_plan_to_db(input_data.get('context', {}), plan))
                
                return result
            
        except Exception as e:
            self.logger.error(f"Coordination error: {e}")
            return {
                'agent': self.name,
                'response': f"Coordination error: {str(e)}",
                'status': 'error',
                'context': input_data.get('context', {})
            }
