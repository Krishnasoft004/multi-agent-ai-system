from .base_agent import BaseAgent
from typing import Dict, Any
import requests
import json
from datetime import datetime
import asyncio

# Import the MongoDB logging utility
try:
    from db.db_utils import save_agent_output_to_db
except ImportError:
    save_agent_output_to_db = None


class SearchAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Search",
            description="Searches for information using web search and knowledge bases"
        )
    
    def web_search(self, query: str) -> str:
        """Perform web search (simulated)"""
        try:
            # In a real implementation, you'd use a search API like Google Custom Search
            # For now, we'll simulate search results
            search_results = f"""
            Search Results for "{query}":
            
            1. Wikipedia: General information about {query}
            2. News Articles: Recent developments related to {query}
            3. Academic Papers: Research findings on {query}
            4. Official Documentation: Technical details about {query}
            
            Key findings:
            - {query} is a relevant topic with multiple aspects
            - Recent developments show growing interest
            - Multiple perspectives and applications exist
            """
            
            return search_results
            
        except Exception as e:
            self.logger.error(f"Search error: {e}")
            return f"Search error: {str(e)}"
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process search request"""
        try:
            message = input_data.get('message', '')
            task = input_data.get('task', {})
            
            # Determine search query
            if task and 'description' in task:
                search_query = task['description']
            else:
                search_query = message
            
            # Perform search
            search_results = self.web_search(search_query)
            
            # Generate response using LLM
            search_prompt = f"""
            Search Query: {search_query}
            Search Results: {search_results}
            
            Based on these search results, provide a comprehensive answer to the user's query.
            Focus on the most relevant and accurate information.
            """
            
            system_prompt = "You are a search specialist. Provide accurate, well-researched information."
            llm_response = self.get_llm_response(search_prompt, system_prompt)
            task_id = f"search_{datetime.utcnow().timestamp()}"
            asyncio.create_task(
                save_agent_output_to_db(
                    session_id=input_data.get("session_id", "unknown"),
                    agent_name=self.name,
                    task_id=task_id,
                    output={
                        "search_query": search_query,
                        "search_results": search_results,
                        "response": llm_response,
                        "status": "completed"
                    }
                )
            )


            
            return {
                'agent': self.name,
                'response': llm_response,
                'search_results': search_results,
                'status': 'completed',
                'context': input_data.get('context', {})
            }
            
        except Exception as e:
            self.logger.error(f"Search processing error: {e}")
            return {
                'agent': self.name,
                'response': f"Search error: {str(e)}",
                'status': 'error',
                'context': input_data.get('context', {})
            }
