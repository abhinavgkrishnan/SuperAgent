from .base_agent import BaseAgent
from typing import Generator, List, Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)

class ThesisAgent(BaseAgent):
    AGENT_DESCRIPTION = """
    Specialized in creating long-form academic and research content. Best suited for:
    - Complex academic topics requiring detailed analysis
    - Research papers and scholarly articles
    - Literature reviews and systematic analyses
    - Technical documentation and white papers
    - In-depth explanatory content
    - Topics requiring citations and references
    - Multi-section structured documents
    - Comprehensive study analyses
    """

    def __init__(self):
        super().__init__()
        self.agent_type = 'thesis'  # Add agent type
        self._register_thesis_tools()
        logger.info("ThesisAgent initialized with analysis capabilities")
    
    def _register_thesis_tools(self):
        self.register_tool(
            name="thesis_analyze_sources",  # Match log pattern
            description="Analyze and synthesize research sources",
            method=self._analyze_sources,
            parameters={
                "sources": "List of research sources",
                "input_data": "Optional previous analysis result"
            }
        )
        
        self.register_tool(
            name="thesis_generate",
            description="Generate structured thesis content",
            method=self._generate_thesis_content,
            parameters={
                "topic": "Main thesis topic",
                "analysis": "Research analysis to base thesis on",
                "input_data": "Optional previous content"
            }
        )

    def _generate_thesis_content(self, topic: str, analysis: str, input_data: Optional[str] = None) -> str:
        """Separated thesis generation into its own tool method"""
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
                "content": f"Topic: {topic}\n\nResearch Analysis:\n{analysis}\nPrevious Content:\n{input_data if input_data else 'None'}"
            }
        ]

        response = self._call_api(messages, stream=False)
        return response.json()['choices'][0]['message']['content']

    def _analyze_sources(self, sources: Optional[List[Dict[str, Any]]] = None, input_data: Optional[str] = None) -> str:
        # Original implementation, just added input_data parameter
        try:
            if not sources and not input_data:
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
                    "content": f"Analyze these sources:\n{json.dumps(sources, indent=2)}\nPrevious Analysis:\n{input_data if input_data else 'None'}"
                }
            ]

            response = self._call_api(analysis_messages, stream=False)
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"Source analysis error: {str(e)}")
            return "Error analyzing sources"