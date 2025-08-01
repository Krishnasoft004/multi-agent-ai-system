from abc import ABC
import logging
from typing import Dict, Any, Optional
import os
from openai import OpenAI
import google.generativeai as genai
from groq import Groq
# Optional DB logging
try:
    from db.db_utils import save_agent_output_to_db
except ImportError:
    save_agent_output_to_db = None  # In case DB is not yet configured

class BaseAgent:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"agent.{name}")
        
        # Initialize LLM clients
        self.openai_client = None
        self.groq_client = None
        self.gemini_model = None
        
        # Try to initialize available LLM clients
        self._init_llm_clients()
    
    def _init_llm_clients(self):
        """Initialize available LLM clients based on environment variables"""
        try:
            # OpenAI
            if os.getenv("OPENAI_API_KEY"):
                self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                self.logger.info("OpenAI client initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize OpenAI: {e}")
        
        try:
            # Groq
            if os.getenv("GROQ_API_KEY"):
                self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                self.logger.info("Groq client initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Groq: {e}")
        
        try:
            # Google Gemini
            if os.getenv("GOOGLE_API_KEY"):
                genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
                self.gemini_model = genai.GenerativeModel('gemini-pro')
                self.logger.info("Gemini client initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Gemini: {e}")
    
    def get_llm_response(self, prompt: str, system_prompt: str = "") -> str:
        """Get response from available LLM"""
        try:
            # Try OpenAI first
            if self.openai_client:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7
                )
                return response.choices[0].message.content
            
            # Try Groq
            elif self.groq_client:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                response = self.groq_client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7
                )
                return response.choices[0].message.content
            
            # Try Gemini
            elif self.gemini_model:
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                response = self.gemini_model.generate_content(full_prompt)
                return response.text
            
            else:
                # Fallback response
                return f"[{self.name}] Processing: {prompt[:100]}... (Demo mode - no API key configured)"
                
        except Exception as e:
            self.logger.error(f"LLM error: {e}")
            return f"[{self.name}] Error processing request: {str(e)}"
    async def log_result_to_db(self, context: Dict[str, Any], result: Dict[str, Any]):
        """Log result into DB if dbutils is available"""
        if save_agent_output_to_db:
            try:
                session_id = context.get('session_id', 'unknown')
                task_id = context.get('task_id', 'unknown')
                await save_agent_output_to_db(session_id, self.name, task_id, result)
                self.logger.info(f"[{self.name}] Logged result to DB.")
            except Exception as e:
                self.logger.warning(f"[{self.name}] Failed to log to DB: {e}")
        else:
            self.logger.debug(f"[{self.name}] DB logging skipped (save_agent_output_to_db not available)")    
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input and return result"""
        try:
            self.logger.info(f"Processing input: {input_data}")
            
            # Extract message from input
            message = input_data.get('message', '')
            context = input_data.get('context', {})
            
            # Get LLM response
            system_prompt = f"You are {self.name}, a specialized AI agent. {self.description}"
            response = self.get_llm_response(message, system_prompt)
            
            result = {
                'agent': self.name,
                'response': response,
                'status': 'completed',
                'context': context
            }
            
            self.logger.info(f"Processing completed: {result}")
             # DB log happens asynchronously
            if save_agent_output_to_db:
                asyncio.create_task(self.log_result_to_db(context, result))

            self.logger.info(f"Processing completed: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Processing error: {e}")
            return {
                'agent': self.name,
                'response': f"Error: {str(e)}",
                'status': 'error',
                'context': input_data.get('context', {})
            }
