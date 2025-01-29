from .base_agent import BaseAgent
from typing import Generator, Dict, Any, List, Optional, Union
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class FinancialReportAgent(BaseAgent):
    AGENT_DESCRIPTION = """
        Specialized in financial analysis and reporting. Best suited for:
        - Financial statements and reports
        - Market analysis and trends
        - Investment recommendations
        - Economic forecasts
        - Stock market analysis
        - Cryptocurrency market analysis
        - Risk assessments
        - Portfolio performance reviews
        """
    def __init__(self):
        super().__init__(temperature=0.2)  # Lower temperature for precision
        self.agent_type = 'financial'
        self._register_financial_tools()
        logger.info("FinancialReportAgent initialized with analysis capabilities")

    def _register_financial_tools(self):
        self.register_tool(
            name="financial_ratio_analysis",  # Changed to match logs
            description="Calculate and analyze financial ratios",
            method=self._analyze_ratios,
            parameters={
                "financial_data": "JSON financial data",
                "input_data": "Optional previous analysis"
            }
        )

        self.register_tool(
            name="financial_trend_analysis",
            description="Analyze financial trends over time",
            method=self._analyze_trends,
            parameters={
                "historical_data": "JSON historical financial data",
                "input_data": "Optional previous analysis"
            }
        )

        self.register_tool(
            name="financial_generate",
            description="Generate comprehensive financial report",
            method=self._generate_financial_report,
            parameters={
                "topic": "Report topic",
                "analysis": "Financial analysis data",
                "input_data": "Optional previous content"
            }
        )


    def _analyze_ratios(self, financial_data: Union[str, Dict], input_data: Optional[str] = None) -> Dict[str, Any]:
        """Calculate key financial ratios with enhanced error handling"""
        try:
            # Parse and validate input data
            data = self.safe_parse_json(financial_data)
            prev_data = self.safe_parse_json(input_data) if input_data else None


            # Add context to API call
            context = f"Previous analysis:\n{json.dumps(prev_data)}\n" if prev_data else ""
            messages = [
                {
                    "role": "system",
                    "content": """Analyze financial ratios including:
                    - Liquidity ratios
                    - Profitability ratios
                    - Solvency ratios
                    - Efficiency ratios

                    Return analysis in JSON format with insights."""
                },
                {
                    "role": "user",
                    "content": f"{context}Analyze these financials: {json.dumps(data)}"
                }
            ]

            response = self._call_api(messages, stream=False)
            result = response.json()['choices'][0]['message']['content']

            # Ensure result is valid JSON
            return self.safe_parse_json(result)

        except Exception as e:
            logger.error(f"Ratio analysis error: {str(e)}")
            return {"error": str(e)}

    def _analyze_trends(self, historical_data: Union[str, List, Dict], input_data: Optional[str] = None) -> Dict[str, Any]:
        """Analyze financial trends"""
        try:
            # Ensure historical_data is in the right format
            if isinstance(historical_data, str):
                try:
                    # Try to parse if it's a JSON string
                    data = json.loads(historical_data)
                except json.JSONDecodeError:
                    # If not JSON, treat it as raw data
                    data = {"raw_data": historical_data}
            else:
                # If already a dict or list, use as is
                data = historical_data

            # Incorporate input_data if provided
            context = f"Previous analysis:\n{input_data}\n" if input_data else ""

            messages = [
                {
                    "role": "system",
                    "content": """Analyze historical financial trends including:
                    - Price movements and volatility
                    - Trading volumes
                    - Market sentiment
                    - Major price levels and support/resistance
                    - Comparative performance

                    Return analysis in JSON format with insights."""
                },
                {
                    "role": "user",
                    "content": f"{context}Analyze these trends: {json.dumps(data)}"
                }
            ]

            response = self._call_api(messages, stream=False)
            result = response.json()['choices'][0]['message']['content']

            # Try to parse the result as JSON
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                # If not valid JSON, wrap in a structured format
                return {
                    "analysis": result,
                    "format": "text",
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Trend analysis error: {str(e)}")
            return {
                "error": str(e),
                "input_type": str(type(historical_data)),
                "timestamp": datetime.now().isoformat()
            }

    def _generate_financial_report(self, topic: str, analysis: Dict[str, Any], input_data: Optional[str] = None) -> str:
        """Generate comprehensive financial report without JSON output"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """Generate a professional financial report including:
                    1. Executive Summary
                    2. Financial Analysis
                    3. Recommendations
                    Use formal business language and specific metrics.
                    Do not include JSON output in the report."""
                },
                {
                    "role": "user",
                    "content": f"Topic: {topic}\nAnalysis: {json.dumps(analysis)}\nPrevious content: {input_data if input_data else 'None'}"
                }
            ]
            response = self._call_api(messages, stream=False)
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"Financial report generation error: {str(e)}")
            return "Error generating financial report"
