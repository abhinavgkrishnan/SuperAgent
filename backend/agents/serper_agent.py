from .base_agent import BaseAgent, Tool
from typing import Dict, Any, List, Generator, Optional
import os
import logging
import requests
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class SerperAgent(BaseAgent):
    AGENT_DESCRIPTION = """
    Specialized in search and information retrieval. Best suited for:
    - Academic research and scholarly articles
    - General web search
    - News and current events
    - Real-time information gathering
    - Comprehensive data collection
    """

    def __init__(self):
        super().__init__(temperature=0.3)  # Lower temperature for more precise results
        self.agent_type = 'serper'
        self._register_search_tools()
        logger.info("SerperAgent initialized")

    def _register_search_tools(self):
        # Register search tools
        self.register_tool(
            name="scholar_search",  # Original name
            description="Search academic sources using Serper Scholar API",
            method=self._search_scholar,
            parameters={
                "query": "Academic search query",
                "input_data": "Optional previous search context"
            }
        )

        self.register_tool(
            name="general_search",  # Original name
            description="Search general information using Serper API",
            method=self._search_general,
            parameters={
                "query": "General search query",
                "input_data": "Optional previous search context"
            }
        )

        self.register_tool(
            name="serper_generate",  # Keep this prefix since it's part of main name
            description="Generate formatted search results response",
            method=self._generate_search_response,
            parameters={
                "query": "Search query",
                "search_type": "Type of search (general or scholar)",
                "input_data": "Optional previous results"
            }
        )

    def _search_scholar(self, query: str, input_data: Optional[str] = None) -> List[Dict[str, Any]]:
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

            results = response.json().get('organic', [])
            logger.info(f"Scholar search completed for query: {query}")
            return results

        except Exception as e:
            logger.error(f"Scholar search error: {str(e)}")
            return []

    def _search_general(self, query: str, input_data: Optional[str] = None) -> List[Dict[str, Any]]:
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

            results = response.json().get('organic', [])
            logger.info(f"General search completed for query: {query}")
            return results

        except Exception as e:
            logger.error(f"General search error: {str(e)}")
            return []

    def search(self, query: str, search_type: str = "general") -> List[Dict[str, Any]]:
        """Unified search method that delegates to appropriate search type"""
        if search_type == "scholar":
            return self._search_scholar(query)
        return self._search_general(query)

    def _generate_search_response(self, query: str, search_type: str = "general", input_data: Optional[str] = None) -> str:
        """
        Generate a formatted search response. This is the primary generation method used by BaseAgent.generate()

        Args:
            query: The search query
            search_type: Type of search to perform ("general" or "scholar")
            input_data: Optional previous search results

        Returns:
            str: JSON string containing formatted search results
        """
        try:
            # Check if we have previous results in input_data
            previous_results = None
            if input_data:
                try:
                    previous_results = json.loads(input_data)
                except json.JSONDecodeError:
                    logger.warning("Could not parse previous results")

            # Perform new search
            results = self.search(query, search_type)

            # Combine with previous results if available
            if previous_results and isinstance(previous_results, list):
                # Remove duplicates based on title
                existing_titles = {r.get('title') for r in previous_results}
                new_results = [r for r in results if r.get('title') not in existing_titles]
                results = previous_results + new_results

            # Format the response
            response = {
                "query": query,
                "search_type": search_type,
                "timestamp": datetime.now().isoformat(),
                "results": results,
                "result_count": len(results)
            }

            return json.dumps(response, indent=2)

        except Exception as e:
            logger.error(f"Error generating search response: {str(e)}")
            return json.dumps({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
