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
        super().__init__(temperature=0.7)
        self.agent_type = 'product'  # Add agent type
        self._register_description_tools()
        logger.info("ProductDescriptionAgent initialized with description capabilities")

    def _register_description_tools(self):
        self.register_tool(
            name="product_generate_specs",
            description="Generate technical specifications",
            method=self._generate_specs,
            parameters={
                "product_info": "JSON product information",
                "input_data": "Optional previous specs"
            }
        )


        self.register_tool(
                name="product_create_marketing_copy",
                description="Create marketing copy for product",
                method=self._create_marketing_copy,
                parameters={
                    "product_info": "JSON product information",
                    "tone": "Desired tone",
                    "input_data": "Optional previous copy"
                }
            )

        self.register_tool(
            name="product_generate",
            description="Generate complete product description",
            method=self._generate_full_description,
            parameters={
                "product": "Product information",  # Changed from topic
                "specs": "Technical specifications",
                "marketing": "Marketing copy",
                "input_data": "Optional previous content"
            }
        )


    def _generate_specs(self, product_info: Dict[str, Any], input_data: Optional[str] = None) -> Dict[str, Any]:
        """Generate technical specifications with enhanced error handling"""
        try:
            # Parse and validate input data
            data = self.safe_parse_json(product_info)
            prev_data = self.safe_parse_json(input_data) if input_data else None


            # Add context to API call
            context = f"Previous specifications:\n{json.dumps(prev_data)}\n" if prev_data else ""
            messages = [
                {
                    "role": "system",
                    "content": """Generate detailed technical specifications..."""
                },
                {
                    "role": "user",
                    "content": f"{context}Generate specs for: {json.dumps(data)}"
                }
            ]

            response = self._call_api(messages, stream=False)
            result = response.json()['choices'][0]['message']['content']

            # Ensure result is valid JSON
            return self.safe_parse_json(result)

        except Exception as e:
            logger.error(f"Specs generation error: {str(e)}")
            return {"error": str(e)}

    def _create_marketing_copy(self, product_info: Dict[str, Any], tone: str = "exciting", input_data: Optional[str] = None) -> str:
        try:
            if isinstance(product_info, str):
                product_info = json.loads(product_info)
            
            context = f"Previous marketing copy:\n{input_data}\n" if input_data else ""
            
            messages = [
                {
                    "role": "system",
                    "content": f"""Create compelling marketing copy in a {tone} tone. 
                    Output should be a clean, formatted text with:
                    - A compelling headline
                    - An engaging subheadline
                    - A descriptive paragraph
                    - Clear benefits list
                    - Unique product points
                    - A strong call to action
    
                    Format as plain text, avoiding JSON or markdown."""
                },
                {
                    "role": "user", 
                    "content": f"{context}Create marketing copy for: {json.dumps(product_info)}"
                }
            ]
    
            response = self._call_api(messages, stream=False)
            return response.json()['choices'][0]['message']['content']
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON input: {str(e)}")
            return "Error: Invalid input format"
        except Exception as e:
            logger.error(f"Marketing copy generation error: {str(e)}")
            return f"Marketing Copy Generation Error: {str(e)}"

    def _generate_full_description(self, product: str, specs: Dict[str, Any], marketing: Dict[str, Any], input_data: Optional[str] = None) -> str:
        """Generate complete product description"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """Generate a comprehensive product description by combining:
                    1. Technical specifications
                    2. Marketing copy
                    3. Additional product details
                    Format as a complete, cohesive description."""
                },
                {
                    "role": "user",
                    "content": f"Product: {product}\nSpecs: {json.dumps(specs)}\nMarketing: {json.dumps(marketing)}\nPrevious content: {input_data if input_data else 'None'}"
                }
            ]
            response = self._call_api(messages, stream=False)
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"Full description generation error: {str(e)}")
            return "Error generating full description"
