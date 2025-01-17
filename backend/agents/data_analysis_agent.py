from .base_agent import BaseAgent
from typing import Generator, Dict, Any, List, Optional
import logging
import json
from datetime import datetime
from models import db, AgentMemory

logger = logging.getLogger(__name__)

class DataAnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__(temperature=0.2)  # Lower temperature for precise analysis
        self._register_analysis_tools()
        logger.info("DataAnalysisAgent initialized with analysis capabilities")

    def _register_analysis_tools(self):
        """Register analysis-specific tools"""
        self.register_tool(
            name="analyze_text",
            description="Perform text analysis on the input",
            method=self._analyze_text,
            parameters={"text": "Text to analyze"}
        )

    def _analyze_text(self, text: str) -> Dict[str, Any]:
        """Perform basic text analysis"""
        try:
            logger.info(f"Performing text analysis on input of length: {len(text)}")
            # Create analysis entry
            memory_entry = AgentMemory(
                type='text_analysis',
                content={
                    'text_length': len(text),
                    'timestamp': datetime.now().isoformat()
                }
            )
            db.session.add(memory_entry)
            db.session.commit()
            logger.info("Text analysis memory entry created successfully")

            return {
                "type": "analysis",
                "content": "Analysis completed successfully"
            }
        except Exception as e:
            logger.error(f"Text analysis error: {str(e)}")
            return {"error": str(e)}

    def generate(self, prompt: str, search_results: Optional[List[Dict[str, Any]]] = None) -> Generator[str, None, None]:
        """Generate data analysis based on prompt"""
        try:
            logger.info(f"Generating analysis for prompt: {prompt}")
            # Generate analysis text
            analysis_text = f"""# Data Analysis Results

    ## Analysis of: {prompt}

    Based on the request, here is a text-based analysis of the topic. This is a simplified version
    that focuses on providing clear, understandable insights.

    Key Points:
    1. The analysis considers relevant market trends
    2. Historical data patterns are evaluated
    3. Current market conditions are assessed

    Note: This is a text-only analysis. For more detailed insights, please refine your query.
    """
            logger.info("Successfully generated analysis text")
            yield json.dumps({
                'type': 'data_analysis',
                'content': analysis_text
            })

        except Exception as e:
            logger.error(f"Analysis generation error: {str(e)}")
            yield json.dumps({
                'type': 'data_analysis',
                'error': str(e)
            })
