from .base_agent import BaseAgent
from typing import Generator, Dict, Any, List, Optional
import logging
import json

logger = logging.getLogger(__name__)

class FinancialReportAgent(BaseAgent):
    def __init__(self):
        super().__init__(temperature=0.2)  # Lower temperature for more precise financial outputs
        self._register_financial_tools()
        logger.info("FinancialReportAgent initialized with analysis capabilities")

    def _register_financial_tools(self):
        """Register finance-specific tools"""
        self.register_tool(
            name="ratio_analysis",
            description="Calculate and analyze financial ratios",
            method=self._analyze_ratios,
            parameters={"financial_data": "JSON financial data"}
        )

        self.register_tool(
            name="trend_analysis",
            description="Analyze financial trends over time",
            method=self._analyze_trends,
            parameters={"historical_data": "JSON historical financial data"}
        )

    def _analyze_ratios(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate key financial ratios"""
        try:
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
                    "content": f"Analyze these financials: {json.dumps(financial_data)}"
                }
            ]

            response = self._call_api(messages, stream=False)
            return json.loads(response.json()['choices'][0]['message']['content'])
        except Exception as e:
            logger.error(f"Ratio analysis error: {str(e)}")
            return {"error": str(e)}

    def _analyze_trends(self, historical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze financial trends"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """Analyze historical financial trends including:
                    - Revenue growth
                    - Profit margins
                    - Cost structures
                    - Working capital

                    Return analysis in JSON format with forecasts."""
                },
                {
                    "role": "user",
                    "content": f"Analyze these trends: {json.dumps(historical_data)}"
                }
            ]

            response = self._call_api(messages, stream=False)
            return json.loads(response.json()['choices'][0]['message']['content'])
        except Exception as e:
            logger.error(f"Trend analysis error: {str(e)}")
            return {"error": str(e)}

    def generate(self, prompt: str, search_results: Optional[List[Dict[str, Any]]] = None) -> Generator[str, None, None]:
        """Generate financial report based on provided prompt and search results"""
        try:
            # Extract relevant financial data from search results
            context = "No additional context available."
            if search_results:
                context = "\n".join([
                    f"Source {i+1}:\n{result.get('snippet', '')}"
                    for i, result in enumerate(search_results[:3])
                ])
    
            messages = [
                {
                    "role": "system",
                    "content": """Generate a professional financial report including:
                    1. Executive Summary
                    2. Financial Position Analysis
                    3. Performance Metrics
                    4. Trend Analysis
                    5. Recommendations
    
                    Use formal business language and include specific metrics."""
                },
                {
                    "role": "user",
                    "content": f"Generate report for prompt: {prompt}\n\nContext:\n{context}"
                }
            ]
    
            response = self._call_api(messages, stream=True)
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
                                        'type': 'financial',
                                        'content': delta['content']
                                    })
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing response: {str(e)}")
                            logger.error(f"Response line causing error: {content}")
                            continue
    
        except Exception as e:
            logger.error(f"Report generation error: {str(e)}")
            yield json.dumps({
                'type': 'financial',
                'error': str(e)
            })