from .base_agent import BaseAgent
from typing import Generator, List, Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)

class FallbackAgent(BaseAgent):
    AGENT_DESCRIPTION = """
        A clarification agent that helps when the task's intent is unclear. Best suited for:
        - Ambiguous queries requiring clarification
        - Low confidence scenarios
        - Error recovery and graceful degradation
        - User intent confirmation
        - Multi-purpose queries that could fit multiple agents
        """
    def __init__(self, available_agents: List[str], selected_agents: List[str]):
        super().__init__(temperature=0.7)
        self.agent_type = 'fallback'
        self.available_agents = available_agents
        self.selected_agents = selected_agents
        self._register_fallback_tools()
        logger.info("FallbackAgent initialized with available and selected agents info")

    def _register_fallback_tools(self):
        self.register_tool(
            name="fallback_generate",
            description="Generate clarifying response",
            method=self._generate_clarification,
            parameters={
                "topic": "Original user query",
                "input_data": "Optional previous clarification"
            }
        )

        self.register_tool(
            name="fallback_format_response",
            description="Format clarification response",
            method=self._format_clarification_response,
            parameters={
                "query": "User query",
                "clarification": "Clarification questions",
                "input_data": "Optional previous response"
            }
        )

    def _generate_clarification(self, topic: str, input_data: Optional[str] = None) -> str:
        try:
            context = f"Previous clarification:\n{input_data}\n" if input_data else ""
            unavailable_agents = [agent for agent in self.available_agents if agent not in self.selected_agents]
            agent_info = ""
            if unavailable_agents:
                agent_info = f"Note: The following agents are not currently selected: {', '.join(unavailable_agents)}. "
                agent_info += "Please consider adding them if they might be relevant to your query."
            
            messages = [
                {
                    "role": "system",
                    "content": f"""Generate clarifying questions and provide information about unavailable agents if relevant.
                    {agent_info}
                    Only mention the specific unavailable agents listed above, if any. Do not suggest or invent new agent types."""
                },
                {
                    "role": "user",
                    "content": f"{context}Generate clarification for: {topic}"
                }
            ]
    
            response = self._call_api(messages, stream=False)
            return response.json()['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"Clarification generation error: {str(e)}")
            return f"Error generating clarification: {str(e)}"


    def _format_clarification_response(self, query: str, clarification: Dict[str, Any], input_data: Optional[str] = None) -> str:
        try:
            unavailable_agents = [agent for agent in self.available_agents if agent not in self.selected_agents]
            agent_info = ""
            if unavailable_agents:
                agent_info = f"The following agents are not currently selected: {', '.join(unavailable_agents)}. "
                agent_info += "Please consider adding them if they might be relevant to your query."
            
            messages = [
                {
                    "role": "system",
                    "content": f"""Create a helpful response that:
                    1. Acknowledges the ambiguity
                    2. Presents clarifying questions
                    3. Suggests possible interpretations
                    4. Mentions unavailable agents if relevant
                    Use a conversational, helpful tone.
                    
                    {agent_info}
                    Only mention the specific unavailable agents listed above, if any. Do not suggest or invent new agent types."""
                },
                {
                    "role": "user",
                    "content": f"Query: {query}\nClarification: {json.dumps(clarification)}\nPrevious response: {input_data if input_data else 'None'}"
                }
            ]
            response = self._call_api(messages, stream=False)
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"Response formatting error: {str(e)}")
            return "Could you please provide more details about what you're looking for?"