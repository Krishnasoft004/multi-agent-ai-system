from .base_agent import BaseAgent
from typing import Dict, Any, List
from datetime import datetime
import asyncio

# Import DB logging utility
try:
    from db.db_utils import save_agent_output_to_db
except ImportError:
    save_agent_output_to_db = None

class SummaryAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Summary",
            description="Creates comprehensive summaries and synthesizes information from multiple sources"
        )
    
    def create_summary(self, content: str, summary_type: str = "comprehensive") -> str:
        """Create different types of summaries"""
        try:
            if summary_type == "brief":
                prompt = f"Create a brief 2-3 sentence summary of: {content}"
            elif summary_type == "detailed":
                prompt = f"Create a detailed summary with key points and insights from: {content}"
            else:  # comprehensive
                prompt = f"Create a comprehensive summary including main points, key insights, and conclusions from: {content}"
            
            system_prompt = "You are a summarization expert. Create clear, concise, and informative summaries."
            return self.get_llm_response(prompt, system_prompt)
            
        except Exception as e:
            self.logger.error(f"Summary creation error: {e}")
            return f"Summary error: {str(e)}"
    
    def synthesize_information(self, information_sources: List[Dict[str, Any]]) -> str:
        """Synthesize information from multiple sources"""
        try:
            combined_content = ""
            for i, source in enumerate(information_sources, 1):
                agent_name = source.get('agent', 'Unknown')
                response = source.get('response', '')
                combined_content += f"\nSource {i} ({agent_name}): {response}\n"
            
            synthesis_prompt = f"""
            Multiple information sources:
            {combined_content}
            
            Synthesize this information into a coherent, comprehensive response.
            Identify common themes, resolve any conflicts, and provide a unified answer.
            """
            
            system_prompt = "You are an information synthesis expert. Combine multiple sources into coherent insights."
            return self.get_llm_response(synthesis_prompt, system_prompt)
            
        except Exception as e:
            self.logger.error(f"Synthesis error: {e}")
            return f"Synthesis error: {str(e)}"
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process summary request"""
        try:
            message = input_data.get('message', '')
            task = input_data.get('task', {})
            previous_results = input_data.get('previous_results', [])

            task_id = f"summary_{datetime.utcnow().timestamp()}"
            session_id = input_data.get("session_id", "unknown")
            
            # Determine what to summarize
            if previous_results:
                # Synthesize information from previous agent results
                summary = self.synthesize_information(previous_results)
                summary_type = "synthesis"
            else:
                # Summarize the original message
                summary = self.create_summary(message)
                summary_type = "direct"
            
            result = {
                'agent': self.name,
                'response': summary,
                'summary_type': summary_type,
                'status': 'completed',
                'context': input_data.get('context', {})
            }

            # Log to database
            if save_agent_output_to_db:
                asyncio.create_task(
                    save_agent_output_to_db(
                        session_id=session_id,
                        agent_name=self.name,
                        task_id=task_id,
                        output={
                            "summary_type": summary_type,
                            "summary": summary,
                            "status": "completed"
                        }
                    )
                )

            return result
            
        except Exception as e:
            self.logger.error(f"Summary processing error: {e}")
            return {
                'agent': self.name,
                'response': f"Summary error: {str(e)}",
                'status': 'error',
                'context': input_data.get('context', {})
            }
