from .base_agent import BaseAgent, Tool
from typing import Dict, Any, List, Generator, Optional
import os
import logging
import requests

logger = logging.getLogger(__name__)

class SerperAgent(BaseAgent):
    """Agent responsible for handling all Serper API interactions"""
    
    def __init__(self):
        super().__init__()
        self._register_search_tools()
        logger.info("SerperAgent initialized with search capabilities")
    
    def _register_search_tools(self):
        """Register search-specific tools"""
        self.register_tool(
            name="scholar_search",
            description="Search academic sources using Serper Scholar API",
            method=self._search_scholar,
            parameters={"query": "Academic search query"}
        )
        
        self.register_tool(
            name="general_search",
            description="Search general information using Serper API",
            method=self._search_general,
            parameters={"query": "General search query"}
        )

    def _search_scholar(self, query: str) -> List[Dict[str, Any]]:
        """Search academic sources using Serper Scholar API"""
        serper_key = os.environ.get("SERPER_API_KEY")
        if not serper_key:
            logger.warning("SERPER_API_KEY not set, scholar search disabled")
            return []

        try:
            response = requests.post(
                "https://google.serper.dev/scholar",
                headers={
                    "X-API-KEY": serper_key,
                    "Content-Type": "application/json"
                },
                json={"q": query, "num": 5}
            )
            if not response.ok:
                logger.error(f"Scholar search failed: {response.status_code} - {response.text}")
                return []

            return response.json().get('organic', [])
        except Exception as e:
            logger.error(f"Scholar search error: {str(e)}")
            return []

    def _search_general(self, query: str) -> List[Dict[str, Any]]:
        """Search general information using Serper API"""
        serper_key = os.environ.get("SERPER_API_KEY")
        if not serper_key:
            logger.warning("SERPER_API_KEY not set, search disabled")
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
            if not response.ok:
                logger.error(f"General search failed: {response.status_code} - {response.text}")
                return []

            return response.json().get('organic', [])
        except Exception as e:
            logger.error(f"General search error: {str(e)}")
            return []

    def search(self, query: str, search_type: str = "general") -> List[Dict[str, Any]]:
        """Unified search method that delegates to appropriate search type"""
        if search_type == "scholar":
            return self._search_scholar(query)
        return self._search_general(query)

    def generate(self, prompt: str, search_results: Optional[List[Dict[str, Any]]] = None) -> Generator[str, None, None]:
        """
        SerperAgent doesn't generate content, it only provides search functionality.
        This method is implemented to satisfy the abstract base class.
        """
        if False:
            yield ""