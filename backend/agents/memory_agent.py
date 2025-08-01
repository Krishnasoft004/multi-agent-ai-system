from .base_agent import BaseAgent
from typing import Dict, Any, List
import json
from datetime import datetime
import asyncio

try:
    from db.db_utils import save_agent_output_to_db
except ImportError:
    save_agent_output_to_db = None

class MemoryAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Memory",
            description="Manages conversation memory and context across sessions"
        )
        self.conversation_memory = {}
        self.context_memory = {}
    
    def store_memory(self, session_id: str, memory_type: str, content: Dict[str, Any]) -> bool:
        """Store memory for a session"""
        try:
            if session_id not in self.conversation_memory:
                self.conversation_memory[session_id] = []
            
            memory_entry = {
                'timestamp': datetime.now().isoformat(),
                'type': memory_type,
                'content': content
            }
            
            self.conversation_memory[session_id].append(memory_entry)
            self.logger.info(f"Stored memory for session {session_id}: {memory_type}")
            if save_agent_output_to_db:
                task_id = f"memory_{memory_type}_{datetime.utcnow().timestamp()}"
                asyncio.create_task(
                    save_agent_output_to_db(
                        session_id=session_id,
                        agent_name=self.name,
                        task_id=task_id,
                        output={
                            "type": memory_type,
                            "content": content,
                            "status": "stored"
                        }
                    )
                )

            return True
            
        except Exception as e:
            self.logger.error(f"Memory storage error: {e}")
            return False
    
    def retrieve_memory(self, session_id: str, memory_type: str = None) -> List[Dict[str, Any]]:
        """Retrieve memory for a session"""
        try:
            if session_id not in self.conversation_memory:
                return []
            
            memories = self.conversation_memory[session_id]
            
            if memory_type:
                memories = [m for m in memories if m['type'] == memory_type]
            
            return memories
            
        except Exception as e:
            self.logger.error(f"Memory retrieval error: {e}")
            return []
    
    def get_context_summary(self, session_id: str) -> str:
        """Get a summary of the conversation context"""
        try:
            memories = self.retrieve_memory(session_id)
            
            if not memories:
                return "No previous conversation context available."
            
            context_prompt = f"""
            Conversation history for session {session_id}:
            
            {json.dumps(memories, indent=2)}
            
            Provide a brief summary of the conversation context and key points discussed.
            """
            
            system_prompt = "You are a memory specialist. Summarize conversation context clearly."
            summary = self.get_llm_response(context_prompt, system_prompt)
             # Log to DB
            if save_agent_output_to_db:
                task_id = f"context_summary_{datetime.utcnow().timestamp()}"
                asyncio.create_task(
                    save_agent_output_to_db(
                        session_id=session_id,
                        agent_name=self.name,
                        task_id=task_id,
                        output={
                            "summary": summary,
                            "status": "context_summary"
                        }
                    )
                )
           
           
            return summary
            
        except Exception as e:
            self.logger.error(f"Context summary error: {e}")
            return f"Context summary error: {str(e)}"
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process memory request"""
        try:
            message = input_data.get('message', '')
            session_id = input_data.get('session_id', 'default')
            action = input_data.get('action', 'retrieve')
            
            if action == 'store':
                # Store new memory
                memory_content = {
                    'message': message,
                    'context': input_data.get('context', {})
                }
                success = self.store_memory(session_id, 'user_interaction', memory_content)
                
                response = "Memory stored successfully." if success else "Failed to store memory."
                
            elif action == 'context':
                # Get context summary
                response = self.get_context_summary(session_id)
                
            else:  # retrieve
                # Retrieve memories
                memories = self.retrieve_memory(session_id)
                response = f"Retrieved {len(memories)} memory entries for session {session_id}."
                
                if memories:
                    response += "\n\nRecent context:\n"
                    for memory in memories[-3:]:  # Last 3 memories
                        response += f"- {memory['content'].get('message', 'N/A')}\n"
                if save_agent_output_to_db:
                    task_id = f"memory_retrieval_{datetime.utcnow().timestamp()}"
                    asyncio.create_task(
                        save_agent_output_to_db(
                            session_id=session_id,
                            agent_name=self.name,
                            task_id=task_id,
                            output={
                                "retrieved_count": len(memories),
                                "status": "retrieved"
                            }
                        )
                    )
             
            
            return {
                'agent': self.name,
                'response': response,
                'memories': self.retrieve_memory(session_id) if action == 'retrieve' else [],
                'status': 'completed',
                'context': input_data.get('context', {})
            }
            
        except Exception as e:
            self.logger.error(f"Memory processing error: {e}")
            return {
                'agent': self.name,
                'response': f"Memory error: {str(e)}",
                'status': 'error',
                'context': input_data.get('context', {})
            }
