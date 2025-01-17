from .base_agent import BaseAgent
from typing import Generator, List, Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)

class ThesisAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self._register_thesis_tools()
        logger.info("ThesisAgent initialized with analysis capabilities")

    def _register_thesis_tools(self):
        """Register thesis-specific tools"""
        self.register_tool(
            name="analyze_sources",
            description="Analyze and synthesize research sources",
            method=self._analyze_sources,
            parameters={"sources": "List of research sources"}
        )

    def _analyze_sources(self, sources: Optional[List[Dict[str, Any]]] = None) -> str:
        """Analyze and synthesize research sources"""
        try:
            if not sources:
                return "No research sources available for analysis."

            analysis_messages = [
                {
                    "role": "system",
                    "content": """Analyze these research sources and synthesize key findings:
                    1. Identify main themes and patterns
                    2. Note any conflicting information
                    3. Extract key statistics and data points
                    4. Highlight research gaps
                    Provide a structured analysis."""
                },
                {
                    "role": "user",
                    "content": f"Analyze these sources:\n{json.dumps(sources, indent=2)}"
                }
            ]

            response = self._call_api(analysis_messages, stream=False)
            response_text = response.text
            logger.debug(f"Source analysis response: {response_text}")
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"Source analysis error: {str(e)}")
            return "Error analyzing sources"

    def generate(self, prompt: str, search_results: Optional[List[Dict[str, Any]]] = None) -> Generator[str, None, None]:
        """Generate thesis content using provided search results"""
        try:
            # Analyze sources if available
            source_analysis = self._analyze_sources(search_results) if search_results else "No scholarly sources available."
            logger.info("Completed source analysis")

            # Generate thesis with analyzed information
            messages = [
                {
                    "role": "system",
                    "content": """Generate a focused thesis following this structure:
                    # Title
                    ## Abstract
                    ## Introduction
                    ## Methodology
                    ## Results
                    ## Discussion
                    ## Conclusion
                    ## References"""
                },
                {
                    "role": "user",
                    "content": f"Topic: {prompt}\n\nResearch Analysis:\n{source_analysis}"
                }
            ]

            response = self._call_api(messages)

            for line in response.iter_lines():
                if line:
                    content = line.decode('utf-8')
                    if content.startswith('data: '):
                        data_str = content[6:]
                        if data_str == '[DONE]':
                            logger.debug("Received [DONE] message, ending stream")
                            break
                        try:
                            data = json.loads(data_str)
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    yield json.dumps({
                                        'type': 'thesis',
                                        'content': delta['content']
                                    })
                        except Exception as e:
                            logger.error(f"Error parsing response line: {str(e)}")
                            logger.error(f"Response line causing error: {content}")
                            continue

        except Exception as e:
            logger.error(f"Error generating thesis: {str(e)}")
            yield json.dumps({
                'type': 'thesis',
                'error': str(e)
            })
