from .base_agent import BaseAgent
from typing import Generator, Dict, Any, List, Optional
import logging
import json
import statistics
from datetime import datetime, timezone
from models import db, AgentMemory

logger = logging.getLogger(__name__)

class DataAnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__(temperature=0.2)  # Lower temperature for precise analysis
        self._register_analysis_tools()
        logger.info("DataAnalysisAgent initialized with advanced data analysis capabilities")

    def _register_analysis_tools(self):
        """Register advanced analysis-specific tools"""
        self.register_tool(
            name="analyze_text",
            description="Perform text sentiment and keyword analysis",
            method=self._analyze_text,
            parameters={"text": "Text to analyze"}
        )

        self.register_tool(
            name="analyze_numbers",
            description="Perform statistical analysis on numerical data",
            method=self._analyze_numbers,
            parameters={"data": "List of numerical values"}
        )

    def _analyze_text(self, text: str) -> Dict[str, Any]:
        """Perform text analysis: sentiment, keyword extraction"""
        try:
            logger.info(f"Performing text analysis on input of length: {len(text)}")

            # Tokenize and normalize text
            words = text.lower().split()
            word_freq = {word: words.count(word) for word in set(words)}

            # Sort words by frequency
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            key_terms = [word for word, _ in sorted_words[:5]]

            analysis_result = {
                "text_length": len(text),
                "key_terms": key_terms
            }

            # Store in memory
            memory_entry = AgentMemory(
                type='text_analysis',
                content=analysis_result  # No timestamp needed, SQLAlchemy handles it
            )
            db.session.add(memory_entry)
            db.session.commit()
            logger.info("Text analysis memory entry created successfully")

            return {
                "type": "analysis",
                "content": f"Text Analysis Completed. Key Terms: {', '.join(key_terms)}"
            }

        except Exception as e:
            logger.error(f"Text analysis error: {str(e)}")
            return {"error": str(e)}

    def _analyze_numbers(self, data: List[float]) -> Dict[str, Any]:
        """Perform basic statistical analysis on numerical data"""
        try:
            if not data or len(data) < 2:
                raise ValueError("Insufficient data for statistical analysis")

            mean = statistics.mean(data)
            median = statistics.median(data)
            std_dev = statistics.stdev(data)

            analysis_result = {
                "mean": mean,
                "median": median,
                "standard_deviation": std_dev
            }

            # Store in memory
            memory_entry = AgentMemory(
                type='numerical_analysis',
                content=analysis_result
            )
            db.session.add(memory_entry)
            db.session.commit()
            logger.info("Numerical analysis memory entry created successfully")

            return {
                "type": "analysis",
                "content": f"Numerical Analysis Completed. Mean: {mean:.2f}, Median: {median:.2f}, Std Dev: {std_dev:.2f}"
            }

        except Exception as e:
            logger.error(f"Numerical analysis error: {str(e)}")
            return {"error": str(e)}

    def generate(self, prompt: str, search_results: Optional[List[Dict[str, Any]]] = None) -> Generator[str, None, None]:
        """Generate data analysis based on prompt"""
        try:
            logger.info(f"Generating analysis for prompt: {prompt}")

            # Example analysis execution
            analysis_text = f"""# Data Analysis Results

## Analysis of: {prompt}

### Key Findings:
- Extracted insights from text or numerical data.
- Highlighted trends and key observations.
- Provided a structured overview for deeper insights.

### Recommendations:
1. Explore additional data for verification.
2. Use statistical models for predictive insights.
3. Further refine based on historical trends.

---
*Note: This is a text-based analysis. Advanced predictive modeling can be added upon request.*
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