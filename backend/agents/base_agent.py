from abc import ABC, abstractmethod
from typing import Generator, Dict, Any, List, Optional, Callable
import os
import requests
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Tool:
    name: str
    description: str
    method: Callable[..., Any]
    parameters: Dict[str, str]

class BaseAgent(ABC):
    def __init__(self, temperature=0.7):
        self.model = "Meta-Llama-3.1-70B-Instruct"
        self.api_endpoint = "https://api-user.ai.aitech.io/api/v1/user/products/3/use/chat/completions"
        self.api_key = "eDsBy2D9vSFWtXZBEAHTPqrvMm7BJqTe2LJ4BhsUHVECir28rKq6dPLK2k7sScQb"
        self.temperature = temperature
        self.tools: Dict[str, Tool] = {}
        self.confidence_score: float = 0.5  # Initialize confidence score
        self._register_default_tools()
        logger.info(f"Initialized {self.__class__.__name__} with temperature {temperature}")

    def _register_default_tools(self):
        """Register default tools available to all agents"""
        self.register_tool(
            name="search",
            description="Search for information using Serper API",
            method=self._search_with_serper,
            parameters={"query": "Search query string"}
        )

    def register_tool(self, name: str, description: str, method: Callable[..., Any], parameters: Dict[str, str]):
        """Register a new tool for the agent to use"""
        self.tools[name] = Tool(
            name=name,
            description=description,
            method=method,
            parameters=parameters
        )
        logger.info(f"Registered tool: {name}")

    def _search_with_serper(self, query: str) -> List[Dict[str, Any]]:
        """Default search tool using Serper API"""
        serper_key = os.environ.get("SERPER_API_KEY")
        if not serper_key:
            logger.warning("SERPER_API_KEY not found, search functionality disabled")
            return []

        try:
            response = requests.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": serper_key,
                    "Content-Type": "application/json"
                },
                json={"q": query, "num": 5}
            )
            return response.json().get('organic', [])
        except Exception as e:
            logger.error(f"Serper API error: {str(e)}")
            return []

    def _call_api(self, messages: list, stream: bool = True) -> requests.Response:
        """Call the LLM API with enhanced error handling and logging"""
        try:
            logger.debug(f"Calling API for {self.__class__.__name__} with messages: {messages}")
            response = requests.post(
                self.api_endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "messages": messages,
                    "model": self.model,
                    "stream": stream,
                    "temperature": self.temperature,
                    "max_tokens": 3000 if stream else 1000
                },
                stream=stream
            )

            if not response.ok:
                logger.error(f"API error: {response.status_code} - {response.text}")
                raise Exception(f"API request failed with status {response.status_code}")

            return response

        except requests.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            raise Exception(f"Failed to call API: {str(e)}")

    def think(self, context: str) -> str:
        """Analyze the context and decide on next actions"""
        messages = [
            {
                "role": "system",
                "content": f"""You are an autonomous agent with access to these tools:
                {self._format_tools_description()}

                Analyze the context and decide:
                1. What tools (if any) would help complete the task
                2. What information is needed
                3. What steps to take next

                Respond in JSON format with:
                {{"reasoning": "your thought process",
                  "tool_needed": "tool name or null",
                  "tool_params": {{"param": "value"}},
                  "next_steps": ["list", "of", "steps"]
                }}"""
            },
            {
                "role": "user",
                "content": context
            }
        ]

        response = self._call_api(messages, stream=False)
        return response.json()['choices'][0]['message']['content']

    def _format_tools_description(self) -> str:
        """Format available tools for system prompt"""
        return "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in self.tools.values()
        ])

    @abstractmethod
    def generate(self, prompt: str, search_results: Optional[List[Dict[str, Any]]] = None) -> Generator[str, None, None]:
        """Generate content based on the prompt"""
        pass