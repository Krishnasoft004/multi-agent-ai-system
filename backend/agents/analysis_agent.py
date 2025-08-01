from .base_agent import BaseAgent
from typing import Dict, Any, List
from db.db_utils import save_agent_output_to_db

class AnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Analysis",
            description="Performs detailed analysis and provides insights on complex topics"
        )
    
    def analyze_data(self, data: str, analysis_type: str = "general") -> str:
        """Perform different types of analysis"""
        try:
            if analysis_type == "sentiment":
                prompt = f"Perform sentiment analysis on: {data}"
            elif analysis_type == "trend":
                prompt = f"Analyze trends and patterns in: {data}"
            elif analysis_type == "comparative":
                prompt = f"Perform comparative analysis of: {data}"
            else:  # general
                prompt = f"Perform comprehensive analysis of: {data}"
            
            system_prompt = "You are an analysis expert. Provide detailed, insightful analysis with clear conclusions."
            return self.get_llm_response(prompt, system_prompt)
            
        except Exception as e:
            self.logger.error(f"Analysis error: {e}")
            return f"Analysis error: {str(e)}"
    
    def generate_insights(self, information: List[Dict[str, Any]]) -> str:
        """Generate insights from multiple information sources"""
        try:
            combined_info = ""
            for i, info in enumerate(information, 1):
                agent_name = info.get('agent', 'Unknown')
                response = info.get('response', '')
                combined_info += f"\nInformation {i} from {agent_name}: {response}\n"
            
            insights_prompt = f"""
            Multiple information sources:
            {combined_info}
            
            Generate key insights, identify patterns, and provide actionable conclusions.
            Focus on:
            1. Key patterns and trends
            2. Important relationships
            3. Actionable recommendations
            4. Potential implications
            """
            
            system_prompt = "You are an insights specialist. Generate valuable, actionable insights from complex information."
            return self.get_llm_response(insights_prompt, system_prompt)
            
        except Exception as e:
            self.logger.error(f"Insights generation error: {e}")
            return f"Insights error: {str(e)}"
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process analysis request"""
        try:
            message = input_data.get('message', '')
            task = input_data.get('task', {})
            previous_results = input_data.get('previous_results', [])
            analysis_type = input_data.get('analysis_type', 'general')
            
            if previous_results:
                # Generate insights from previous results
                analysis_result = self.generate_insights(previous_results)
                analysis_method = "insights_generation"
            else:
                # Analyze the original message
                analysis_result = self.analyze_data(message, analysis_type)
                analysis_method = "direct_analysis"
            
            output = {
                'agent': self.name,
                'response': analysis_result,
                'analysis_type': analysis_type,
                'analysis_method': analysis_method,
                'status': 'completed',
                'context': input_data.get('context', {})
            }

            # Save to MongoDB
            session_id = input_data.get("context", {}).get("session_id")
            task_id = task.get("id")
            save_agent_output_to_db(
                session_id=session_id,
                agent_name=self.name,
                task_id=task_id,
                output_data=output
            )

            return output

        except Exception as e:
            self.logger.error(f"Analysis processing error: {e}")
            return {
                'agent': self.name,
                'response': f"Analysis error: {str(e)}",
                'status': 'error',
                'context': input_data.get('context', {})
            }