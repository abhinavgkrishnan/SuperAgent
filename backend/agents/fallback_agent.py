# fallback_agent.py

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

    def __init__(self):
        super().__init__(temperature=0.7)
        self._register_fallback_tools()
        logger.info("FallbackAgent initialized")

    def _register_fallback_tools(self):
        """Register fallback-specific tools"""
        self.register_tool(
            name="generate_clarification",
            description="Generate clarifying questions for ambiguous queries",
            method=self._generate_clarification,
            parameters={"query": "Original user query"}
        )

    def _generate_clarification(self, query: str) -> Dict[str, Any]:
        """Generate clarifying questions based on the query"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """Generate clarifying questions to understand user intent.
                    Consider different possible interpretations and ask targeted questions.
                    Return questions that would help determine whether the user wants:
                    - A short social media update
                    - An in-depth analysis
                    - Financial analysis
                    - Product information
                    Format your response as a clear message to the user."""
                },
                {
                    "role": "user",
                    "content": f"Generate clarification for: {query}"
                }
            ]

            response = self._call_api(messages, stream=False)

            try:
                if hasattr(response, 'json'):
                    result = response.json()
                    if isinstance(result, dict) and 'choices' in result:
                        content = result['choices'][0]['message']['content']
                        return {
                            "message": content,
                            "possible_interpretations": [
                                "Short social media update",
                                "In-depth analysis",
                                "Financial analysis",
                                "Product information"
                            ]
                        }

                return {
                    "message": "Could you please specify what type of content you're looking for? For example, would you like a quick social media update, an in-depth analysis, financial analysis, or something else?",
                    "possible_interpretations": [
                        "Short social media update",
                        "In-depth analysis",
                        "Financial analysis",
                        "Product information"
                    ]
                }

            except Exception as e:
                logger.error(f"Error parsing clarification response: {str(e)}")
                return {
                    "message": "Could you please provide more details about what kind of content you're looking for?",
                    "possible_interpretations": [
                        "Short social media update",
                        "In-depth analysis",
                        "Financial analysis",
                        "Product information"
                    ]
                }

        except Exception as e:
            logger.error(f"Clarification generation error: {str(e)}")
            return {
                "message": "Could you please provide more details about what kind of content you're looking for?",
                "possible_interpretations": [
                    "Short social media update",
                    "In-depth analysis",
                    "Financial analysis",
                    "Product information"
                ]
            }

    def generate(self, prompt: str, search_results: Optional[List[Dict[str, Any]]] = None) -> Generator[str, None, None]:
        """Generate fallback response for ambiguous queries"""
        try:
            clarification = self._generate_clarification(prompt)

            if "error" in clarification:
                yield json.dumps({
                    "type": "fallback",
                    "content": clarification["message"]
                })
                return

            messages = [
                {
                    "role": "system",
                    "content": """Create a helpful response that:
                    1. Acknowledges the ambiguity
                    2. Explains possible interpretations
                    3. Asks for clarification
                    Use a conversational, helpful tone."""
                },
                {
                    "role": "user",
                    "content": f"Query: {prompt}\nClarification: {json.dumps(clarification)}"
                }
            ]

            response = self._call_api(messages, stream=True)
            for line in response.iter_lines():
                if line:
                    content = line.decode('utf-8')
                    if content.startswith('data: '):
                        data_str = content[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    yield json.dumps({
                                        'type': 'fallback',
                                        'content': delta['content']
                                    })
                        except Exception as e:
                            logger.error(f"Error parsing response: {str(e)}")
                            continue

        except Exception as e:
            logger.error(f"Fallback generation error: {str(e)}")
            yield json.dumps({
                'type': 'fallback',
                'error': "I couldn't determine how to handle your request. Could you please provide more details?"
            })
