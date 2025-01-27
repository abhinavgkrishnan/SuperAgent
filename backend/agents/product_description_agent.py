from .base_agent import BaseAgent
from typing import Generator, Dict, Any, List, Optional
import logging
import json

logger = logging.getLogger(__name__)

class ProductDescriptionAgent(BaseAgent):
    AGENT_DESCRIPTION = """
        Specialized in creating compelling product content. Best suited for:
        - Product descriptions and features
        - Technical specifications
        - Marketing copy and sales content
        - Product comparisons
        - User manuals and guides
        - Feature highlights
        - Benefits analysis
        - E-commerce listings
        """
    def __init__(self):
        super().__init__(temperature=0.7)  # Higher temperature for creative descriptions
        self._register_description_tools()
        logger.info("ProductDescriptionAgent initialized with description capabilities")

    def _register_description_tools(self):
        """Register description-specific tools"""
        self.register_tool(
            name="generate_specs",
            description="Generate technical specifications",
            method=self._generate_specs,
            parameters={"product_info": "JSON product information"}
        )

        self.register_tool(
            name="create_marketing_copy",
            description="Create marketing copy for product",
            method=self._create_marketing_copy,
            parameters={"product_info": "JSON product information", "tone": "Desired tone"}
        )

    def _generate_specs(self, product_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate technical specifications"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """Generate detailed technical specifications including:
                    1. Physical specifications
                    2. Technical features
                    3. Performance metrics
                    4. Compatibility information
                    5. System requirements

                    Return in structured JSON format."""
                },
                {
                    "role": "user",
                    "content": f"Generate specs for: {json.dumps(product_info)}"
                }
            ]

            response = self._call_api(messages, stream=False)
            return json.loads(response.json()['choices'][0]['message']['content'])
        except Exception as e:
            logger.error(f"Specs generation error: {str(e)}")
            return {"error": str(e)}

    def _create_marketing_copy(self, product_info: Dict[str, Any], tone: str) -> Dict[str, Any]:
        """Create marketing copy"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": f"""Create compelling marketing copy in a {tone} tone. Include:
                    1. Headlines
                    2. Product description
                    3. Key benefits
                    4. Unique selling points
                    5. Call to action

                    Return in structured JSON format."""
                },
                {
                    "role": "user",
                    "content": f"Create marketing copy for: {json.dumps(product_info)}"
                }
            ]

            response = self._call_api(messages, stream=False)
            return json.loads(response.json()['choices'][0]['message']['content'])
        except Exception as e:
            logger.error(f"Marketing copy generation error: {str(e)}")
            return {"error": str(e)}

    def generate(self, prompt: str, search_results: Optional[List[Dict[str, Any]]] = None) -> Generator[str, None, None]:
        """Generate product description based on prompt and search results"""
        try:
            context = "No additional context available."
            if search_results:
                context = "\n".join([
                    f"Source {i+1}:\n{result.get('snippet', '')}"
                    for i, result in enumerate(search_results[:3])
                ])

            messages = [
                {
                    "role": "system",
                    "content": """Generate a comprehensive product description including:
                    1. Product Overview
                    2. Key Features and Benefits
                    3. Technical Specifications
                    4. Target Audience
                    5. Use Cases and Applications
                    6. Unique Selling Points
                    7. Pricing and Value Proposition
                    8. Warranty and Support Information

                    Format the output professionally and include all relevant details."""
                },
                {
                    "role": "user",
                    "content": f"Product to describe: {prompt}\n\nContext:\n{context}"
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
                                        'type': 'product',
                                        'content': delta['content']
                                    })
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing response: {str(e)}")
                            logger.error(f"Response line causing error: {content}")
                            continue

        except Exception as e:
            logger.error(f"Product description generation error: {str(e)}")
            yield json.dumps({
                'type': 'product',
                'error': str(e)
            })
