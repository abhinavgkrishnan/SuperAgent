from abc import ABC, abstractmethod
from typing import Generator, Dict, Any, List, Optional, Callable, Union
import requests
import logging
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class Tool:
    name: str
    description: str
    method: Callable[..., Any]
    parameters: Dict[str, str]
    agent_type: str  # Added to track tool's origin

class BaseAgent(ABC):
    def __init__(self, temperature=0.7):
        self.model = "Meta-Llama-3.1-70B-Instruct"
        self.api_endpoint = "https://api-user.ai.aitech.io/api/v1/user/products/3/use/chat/completions"
        self.api_key = "eDsBy2D9vSFWtXZBEAHTPqrvMm7BJqTe2LJ4BhsUHVECir28rKq6dPLK2k7sScQb"
        self.temperature = temperature
        self.tools: Dict[str, Tool] = {}
        self.confidence_score: float = 0.5
        self.agent_type = self.__class__.__name__.lower().replace('agent', '')
        logger.info(f"Initialized {self.__class__.__name__} with temperature {temperature}")

    def safe_parse_json(self, input_data: Any) -> Any:
        """Safely parse potential JSON input"""
        if isinstance(input_data, str):
            try:
                return json.loads(input_data)
            except json.JSONDecodeError:
                # If it's a quoted string literal, remove quotes
                if input_data.startswith('"') and input_data.endswith('"'):
                    return input_data[1:-1]
        return input_data

    def standardize_response(self, content: Any, content_type: str = 'json') -> Union[str, Dict[str, Any]]:
        """Standardize response format"""
        try:
            if content_type == 'json':
                if isinstance(content, str):
                    content = self.safe_parse_json(content)
                result = {
                    'status': 'success',
                    'data': content
                }
                return result  # Return Dict directly instead of JSON string
            else:
                return {
                    'status': 'success',
                    'content': str(content),
                    'format': 'text'
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def use_tool(self, tool_id: str, **kwargs) -> Any:
        """Use a tool by its ID with enhanced validation"""
        tool = self.tools.get(tool_id)
        if tool is None:
            raise ValueError(f"Tool not found: {tool_id}")

        try:
            # Validate and process parameters
            validated_params = {}
            for param_name, param_type in tool.parameters.items():
                if param_name not in kwargs and param_name != 'input_data':
                    raise ValueError(f"Missing required parameter: {param_name}")

                value = kwargs.get(param_name)
                if param_name == 'input_data' and value is None:
                    validated_params[param_name] = None
                    continue

                # Process potential JSON parameters
                if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                    value = self.safe_parse_json(value)

                validated_params[param_name] = value

            # Execute tool with validated parameters
            result = tool.method(**validated_params)
            return self.standardize_response(result)

        except Exception as e:
            logger.error(f"Error executing tool {tool_id}: {str(e)}")
            return self.standardize_response({'error': str(e)})

    def register_tool(self, name: str, description: str, method: Callable[..., Any], parameters: Dict[str, str]):
        """Register a new tool for the agent to use"""
        # Don't add agent type prefix if it's already there
        if not name.startswith(f"{self.agent_type}_"):
            tool_id = f"{self.agent_type}_{name}"
        else:
            tool_id = name

        self.tools[tool_id] = Tool(
            name=name,
            description=description,
            method=method,
            parameters=parameters,
            agent_type=self.agent_type
        )
        logger.info(f"Registered tool: {tool_id} for agent type: {self.agent_type}")

    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all tools available to this agent"""
        return {
            tool_id: {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "agent_type": tool.agent_type
            }
            for tool_id, tool in self.tools.items()
        }

    def _call_api(self, messages: list, stream: bool = True) -> requests.Response:
        """Call the LLM API with enhanced error handling and logging"""
        try:
            logger.debug(f"Calling API for {self.__class__.__name__} with messages: {messages}")
            response = requests.post(
                self.api_endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "messages": messages,
                    "model": self.model,
                    "stream": stream,
                    "temperature": self.temperature,
                    "max_tokens": 3000 if stream else 1000
                },
                stream=stream
            )

            if not response.ok:
                logger.error(f"API error: {response.status_code} - {response.text}")
                raise Exception(f"API request failed with status {response.status_code}")

            return response

        except requests.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            raise Exception(f"Failed to call API: {str(e)}")

    def think(self, context: str) -> str:
        """Analyze the context and decide on next actions"""
        messages = [
            {
                "role": "system",
                "content": f"""You are an autonomous agent with access to these tools:
                {self._format_tools_description()}

                Analyze the context and decide:
                1. What tools (if any) would help complete the task
                2. What information is needed
                3. What steps to take next

                Respond in JSON format with:
                {{"reasoning": "your thought process",
                  "tool_needed": "tool name or null",
                  "tool_params": {{"param": "value"}},
                  "next_steps": ["list", "of", "steps"]
                }}"""
            },
            {
                "role": "user",
                "content": context
            }
        ]

        response = self._call_api(messages, stream=False)
        return response.json()['choices'][0]['message']['content']

    def _format_tools_description(self) -> str:
        """Format available tools for system prompt"""
        tool_descriptions = []
        for tool_id, tool in self.tools.items():
            params = ", ".join(f"{k}: {v}" for k, v in tool.parameters.items())
            tool_descriptions.append(
                f"- {tool_id}:\n"
                f"  Description: {tool.description}\n"
                f"  Parameters: {params}\n"
                f"  Owner: {tool.agent_type}"
            )
        return "\n".join(tool_descriptions)

    def generate(self, prompt: str, max_retries: int = 3) -> Generator[str, None, None]:
        """Common generate method for all agents."""
        for attempt in range(max_retries):
            try:
                # Get all tools for this agent type
                agent_tools = self.get_available_tools()
                if not agent_tools:
                    raise ValueError(f"No tools registered for agent type: {self.agent_type}")

                # Find the primary generation tool
                generation_tools = [
                    tool_id for tool_id in agent_tools
                    if any(term in tool_id.lower() for term in ['generate', 'create', 'write'])
                ]

                if not generation_tools:
                    raise ValueError(f"No generation tool found for agent type: {self.agent_type}")

                # Use the first matching generation tool
                tool_id = generation_tools[0]
                tool = self.tools[tool_id]

                # Map parameters correctly based on tool's expected parameters
                params = {}
                if 'topic' in tool.parameters:
                    params['topic'] = prompt
                elif 'query' in tool.parameters:
                    params['query'] = prompt

                # Always include input_data if tool accepts it
                if 'input_data' in tool.parameters:
                    params['input_data'] = None

                # Execute the tool with mapped parameters
                result = tool.method(**params)

                # Handle different result types
                if isinstance(result, str):
                    chunk_size = 1000
                    for i in range(0, len(result), chunk_size):
                        chunk = result[i:i + chunk_size]
                        yield json.dumps({
                            'type': self.agent_type,
                            'content': chunk
                        })
                else:
                    yield json.dumps({
                        'type': self.agent_type,
                        'content': json.dumps(result)
                    })

                return  # Successful completion

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed in {self.__class__.__name__}: {str(e)}")
                if attempt == max_retries - 1:  # Last attempt
                    yield json.dumps({
                        'type': self.agent_type,
                        'error': f"All attempts failed: {str(e)}"
                    })
                continue

    def execute_tool_chain(self, context: str, tool_chain: List[Dict[str, Any]]) -> Any:
        """Execute a chain of tools"""
        result = context
        for step in tool_chain:
            try:
                tool_id = step['tool_id']
                parameters = step.get('parameters', {})
                parameters['input_data'] = result  # Pass previous result as input
                result = self.use_tool(tool_id, **parameters)
            except Exception as e:
                logger.error(f"Error in tool chain execution: {str(e)}")
                raise

        return result

    def validate_tool_parameters(self, tool_id: str, parameters: Dict[str, Any]) -> bool:
        """Validate parameters for a tool"""
        if tool_id not in self.tools:
            return False

        tool = self.tools[tool_id]
        required_params = set(tool.parameters.keys())
        provided_params = set(parameters.keys())

        return required_params.issubset(provided_params)
