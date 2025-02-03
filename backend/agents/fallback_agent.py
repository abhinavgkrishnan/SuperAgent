from .base_agent import BaseAgent
from typing import Generator, List, Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)

class FallbackAgent(BaseAgent):
    AGENT_DESCRIPTION = """
        A clarification agent that helps when the task's intent is unclear or when specific agents are unavailable.
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
            name="fallback_clarify",
            description="Generate clarifying response or agent selection instruction",
            method=self._clarify,
            parameters={
                "topic": "Original user query",
                "input_data": "Optional previous clarification"
            }
        )

    def _clarify(self, topic: str, input_data: Optional[str] = None) -> str:
        try:
            context = f"Previous clarification:\n{input_data}\n" if input_data else ""
            unavailable_agents = [agent for agent in self.available_agents if agent not in self.selected_agents]
            if unavailable_agents:
                return f"Please select the {unavailable_agents[0]} agent to proceed with this task."

            messages = [
                {
                    "role": "system",
                    "content": f"""Generate a response that either:
                    1. Instructs the user to select a specific required agent if one is needed for the query.
                    2. Provides clarifying questions if the query is ambiguous.
                    Only mention specific unavailable agents. Do not suggest new agent types."""
                },
                {
                    "role": "user",
                    "content": f"{context}Clarify or provide instructions for: {topic}"
                }
            ]

            response = self._call_api(messages, stream=False)
            return response.json()['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"Clarification error: {str(e)}")
            return f"Error generating clarification: {str(e)}"

    def generate(self, prompt: str, max_retries: int = 3) -> Generator[str, None, None]:
        for _ in range(max_retries):
            try:
                clarification = self._clarify(prompt)
                yield json.dumps({"type": "fallback", "content": clarification})
                return
            except Exception as e:
                logger.error(f"Generation error: {str(e)}")
        yield json.dumps({"type": "fallback", "error": "Failed to generate clarification"})