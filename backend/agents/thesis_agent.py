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

    def _generate_thesis_content(self, topic: str, analysis: Optional[str] = None, input_data: Optional[str] = None) -> str:
        """Generate structured thesis content with enhanced error handling and validation.
        
        Args:
            topic: Main thesis topic
            analysis: Research analysis to base thesis on (optional)
            input_data: Previous content (optional)
            
        Returns:
            str: Generated thesis content
            
        Raises:
            ValueError: If topic is empty
        """
        try:
            # Validate inputs
            if not topic or not topic.strip():
                raise ValueError("Topic cannot be empty")
                
            # Ensure analysis is a string
            analysis = str(analysis) if analysis is not None else ""
            
            # Create system prompt with detailed instructions
            system_prompt = """Generate a focused thesis following this structure:
                # Title
                Provide a clear, specific title that reflects the research focus.
                
                ## Abstract
                A concise summary of the research (250-300 words) covering:
                - Context and importance
                - Research objective
                - Key findings
                - Implications
                
                ## Introduction
                - Background and context
                - Problem statement
                - Research objectives
                - Significance of the study
                
                ## Methodology
                - Research approach
                - Data collection methods
                - Analysis methods
                - Limitations
                
                ## Results
                - Key findings
                - Supporting data
                - Statistical analysis where applicable
                
                ## Discussion
                - Interpretation of results
                - Comparison with existing literature
                - Implications of findings
                - Research limitations
                
                ## Conclusion
                - Summary of key findings
                - Research contributions
                - Future research directions
                - Concluding remarks
                
                ## References
                Use proper academic citation format.
                
                IMPORTANT:
                - Maintain academic tone and style
                - Use evidence-based arguments
                - Include critical analysis
                - Ensure logical flow between sections"""
    
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": f"""Topic: {topic}
                    
                    Research Analysis:
                    {analysis}
                    
                    Previous Content:
                    {input_data if input_data else 'None'}
                    
                    Please generate a comprehensive thesis following the structure provided."""
                }
            ]
    
            # Make API call with error handling
            response = self._call_api(messages, stream=False)
            if not response.ok:
                logger.error(f"API call failed: {response.status_code} - {response.text}")
                raise Exception(f"API request failed with status {response.status_code}")
    
            response_json = response.json()
            if not response_json.get('choices'):
                raise ValueError("Invalid API response format")
    
            content = response_json['choices'][0]['message']['content']
            
            # Validate output
            if not content or len(content.strip()) < 100:  # Basic validation
                raise ValueError("Generated content is too short or empty")
                
            # Basic structure validation
            required_sections = ["Title", "Abstract", "Introduction", "Methodology", 
                               "Results", "Discussion", "Conclusion", "References"]
            
            for section in required_sections:
                if section.lower() not in content.lower():
                    logger.warning(f"Generated content missing section: {section}")
    
            return content
    
        except Exception as e:
            logger.error(f"Error generating thesis content: {str(e)}")
            # Return a structured error message that can be handled by the calling function
            error_content = f"""# Error Generating Thesis Content
    
    ## Error Details
    {str(e)}
    
    ## Suggestions
    - Please try again with a more specific topic
    - Ensure research analysis is provided if required
    - Check network connection if error persists
    
    If the problem continues, please contact support."""
            
            return error_content

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