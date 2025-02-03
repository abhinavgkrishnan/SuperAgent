from .base_agent import BaseAgent
from typing import Generator, Dict, Any, List, Optional
import logging
from logging.handlers import RotatingFileHandler
import json
import asyncio
from datetime import datetime
from models import db, AgentMemory
import re
import traceback
from .shared_tools import ToolRegistry

# Clear any existing log handlers to prevent duplicate logging issues
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Create a rotating log file handler
log_file = "super_agent.log"
rotating_handler = RotatingFileHandler(log_file, mode="a", maxBytes=5*1024*1024, backupCount=2, encoding=None, delay=False)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
    handlers=[
        rotating_handler,
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)
logger.info("Logging system initialized successfully")

class SuperAgent(BaseAgent):
    def __init__(self, search_agent=None, specialized_agents=None):
        super().__init__(temperature=0.3)
        self.memory = []
        self.tools_used = []  # Initialize at class level
        self.execution_path = []  # Initialize at class level
        self.performance_metrics = {
            "decisions_made": 0,
            "successful_executions": 0,
            "tool_usage": {},
            "average_confidence": 0.0,
        }
        self.search_agent = search_agent
        self.specialized_agents = specialized_agents or {}
        self.tool_registry = ToolRegistry()
        self._register_all_agent_tools()
        logger.info("SuperAgent initialized with enhanced orchestration capabilities")

    def _register_all_agent_tools(self):
        """Register tools from all specialized agents"""
        # First register tools from specialized agents
        for agent_type, agent in self.specialized_agents.items():
            agent_tools = agent.get_available_tools()
            for tool_id, tool_info in agent_tools.items():
                self.tool_registry.register_tool(
                    name=tool_id,
                    description=tool_info["description"],
                    method=agent.tools[tool_id].method,
                    parameters=tool_info["parameters"],
                    agent_type=agent.agent_type,
                )
    
        # Then register Serper tools if available
        if self.search_agent:
            serper_tools = self.search_agent.get_available_tools()
            for tool_id, tool_info in serper_tools.items():
                # Keep original tool_id for method lookup
                logger.info(f"Registering Serper tool: {tool_id}")
                self.tool_registry.register_tool(
                    name=tool_id,
                    description=tool_info["description"],
                    method=self.search_agent.tools[tool_id].method,  # Use original tool_id
                    parameters=tool_info["parameters"],
                    agent_type='serper'
                )

    def _execute_tool_sequence(self, tool_sequence: List[Dict[str, Any]], content_type: str) -> Generator[str, None, None]:
        accumulated_result = None
        step_outputs = {}

        for step_index, step in enumerate(tool_sequence, 1):
            try:
                tool_id = step.get('tool_id')
                if not tool_id:
                    logger.warning("No tool_id in step")
                    continue

                # Get the tool
                tool = self.tool_registry.get_tool(tool_id)
                if tool is None:
                    logger.error(f"Tool {tool_id} not found in registry")
                    continue

                # Prepare parameters
                params = step.get('parameters', {}).copy()

                # Replace step references
                for param_name, param_value in params.items():
                    if isinstance(param_value, str) and '$STEP[' in param_value:
                        ref_step = re.search(r'\$STEP\[(\d+)\]', param_value)
                        if ref_step:
                            step_num = int(ref_step.group(1))
                            if step_num in step_outputs:
                                params[param_name] = step_outputs[step_num]

                # Add input_data if supported
                if 'input_data' in tool.parameters:
                    params['input_data'] = accumulated_result if accumulated_result else None

                # Track execution
                self.tools_used.append({
                    "tool_id": tool_id,
                    "parameters": params,
                    "step": step_index
                })

                # Execute tool
                result = tool.method(**params)

                # Clean any standardized response wrappers
                if isinstance(result, dict):
                    if 'status' in result and 'data' in result:
                        result = result['data'].get('message', result['data'])
                    elif 'message' in result and 'possible_interpretations' in result:
                        result = result['message']

                # Store result
                step_outputs[step_index] = result
                accumulated_result = result

                # Only yield final step results
                if step_index == len(tool_sequence):
                    # Return clean content
                    output = {
                        'type': content_type,
                        'content': result if isinstance(result, str) else json.dumps(result, indent=2)
                    }
                    yield json.dumps(output)

            except Exception as step_error:
                error_msg = f"Error in step {step_index}: {str(step_error)}"
                logger.error(error_msg)
                yield json.dumps({
                    'type': content_type,
                    'error': error_msg,
                    'step': step_index
                })

    def generate(self, prompt: str, max_retries: int = 3) -> Generator[str, None, None]:
        for attempt in range(max_retries):
            try:
                content_type = self.determine_content_type(prompt)
                logger.info(f"Content type determined: {content_type}")

                if content_type == "fallback":
                    yield from self.specialized_agents["fallback"].generate(prompt)
                    return

                tool_sequence = self._get_tool_sequence(prompt, content_type)
                if not tool_sequence:
                    # Try direct generation with appropriate agent instead of fallback
                    agent = self.get_agent_for_type(content_type)
                    if agent:
                        yield from agent.generate(prompt)
                        return

                # Execute tool sequence with better error handling
                yield from self._execute_tool_sequence(tool_sequence, content_type)
                return

            except Exception as e:
                logger.error(f"Generation attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    yield from self.specialized_agents["fallback"].generate(prompt)

    def _get_tool_sequence(self, task: str, content_type: str) -> List[Dict[str, Any]]:
        """Get sequence of tools to execute"""
        try:
            # Convert tools to serializable format
            tools_info = {}
            for tool_id, tool in self.tool_registry.get_all_tools().items():
                tools_info[tool_id] = {
                    "description": tool.description,
                    "parameters": tool.parameters,
                    "agent_type": tool.agent_type,
                }

            messages = [
                {
                    "role": "system",
                    "content": f"""Plan the tool sequence for a {content_type} task.
                    IMPORTANT: Consider search tools first for current information.
                    Recommended search sequence:
                    1. Use scholar_search for academic/technical content
                    2. Use general_search for recent information
                    3. Use sentiment_search for public opinion

                    Current search tools available:
                    - serper_scholar_search: Academic sources
                    - serper_general_search: Web content
                    - twitter_sentiment_search: Public sentiment

                    Available tools: {json.dumps(tools_info, indent=2)}

                    When creating the sequence:
                    1. Consider if searches would improve the output
                    2. Think about what specific information would be most valuable
                    3. Plan how to use the search results in later steps
                    4. Consider multiple searches if different types of information are needed

                    IMPORTANT: Your response must be a valid JSON array in this exact format:
                    [
                        {{
                            "tool_id": "exact_tool_id",
                            "reason": "why this tool is needed",
                            "parameters": {{
                                "param1": "value1"
                            }},
                            "expected_output": "what this step produces"
                        }}
                    ]

                    Do not include any explanatory text before or after the JSON array.
                    """
                },
                {"role": "user", "content": f"Task: {task}"}
            ]

            response = self._call_api(messages, stream=False)
            content = response.json()['choices'][0]['message']['content']

            # Clean the content - remove any markdown code block indicators
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)

            # Find the JSON array
            matches = re.findall(r'\[\s*\{.*?\}\s*\]', content, re.DOTALL)
            if not matches:
                logger.error("No JSON array found in response")
                logger.debug(f"Response content: {content}")
                return []

            # Initialize json_str before the try block
            json_str = matches[0].strip()

            try:
                # Clean and parse the JSON
                # Remove trailing commas before closing brackets/braces
                json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                # Remove any remaining whitespace between brackets
                json_str = re.sub(r'\]\s*\[', '][', json_str)

                sequence = json.loads(json_str)

                # Validate sequence structure
                if not isinstance(sequence, list):
                    logger.error(f"Parsed result is not a list: {type(sequence)}")
                    return []

                # Validate each step in the sequence
                required_keys = {"tool_id", "parameters", "reason", "expected_output"}
                for i, step in enumerate(sequence):
                    if not isinstance(step, dict):
                        logger.error(f"Step {i} is not a dictionary: {type(step)}")
                        return []

                    missing_keys = required_keys - set(step.keys())
                    if missing_keys:
                        logger.error(f"Step {i} missing required keys: {missing_keys}")
                        return []

                    if not isinstance(step["parameters"], dict):
                        logger.error(f"Step {i} parameters is not a dictionary: {type(step['parameters'])}")
                        return []

                logger.info(f"Successfully parsed tool sequence with {len(sequence)} steps")
                return sequence

            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {str(e)}")
                logger.error(f"Problematic JSON string: {json_str}")

                # Attempt more aggressive cleaning if initial parse fails
                try:
                    # Remove all whitespace and newlines
                    json_str = re.sub(r'\s+', ' ', json_str)
                    # Ensure proper quote usage
                    json_str = re.sub(r'(?<!\\)"', '\\"', json_str)
                    json_str = re.sub(r"'", '"', json_str)
                    # Remove escape characters
                    json_str = json_str.encode().decode('unicode-escape')

                    sequence = json.loads(json_str)
                    if isinstance(sequence, list) and all(isinstance(step, dict) for step in sequence):
                        logger.info("Successfully parsed JSON after cleaning")
                        return sequence
                except Exception as fix_error:
                    logger.error(f"Failed to fix JSON: {str(fix_error)}")
                    return []

                return []  # Return empty list if JSON parsing fails

        except Exception as e:
            logger.error(f"Error in tool sequence generation: {str(e)}")
            logger.error(f"Full error context: {traceback.format_exc()}")
            return []

    def get_tools_used(self) -> List[str]:
        """Get list of tools used in last execution"""
        return self.tools_used

    def get_execution_path(self) -> List[Dict[str, Any]]:
        """Get detailed execution path of last run"""
        return self.execution_path

    def get_agent_for_type(self, content_type: str) -> BaseAgent:
        """Get the appropriate agent for the content type with fallback"""
        try:
            return self.specialized_agents.get(
                content_type, self.specialized_agents["thesis"]
            )
        except Exception as e:
            logger.error(f"Error getting agent for type {content_type}: {str(e)}")
            return self.specialized_agents["thesis"]

    def _analyze_task_complexity(self, task: str) -> Dict[str, Any]:
        """Enhanced task complexity analysis with self-improvement capability"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are an autonomous task analyzer.
                        Consider these aspects while maintaining independence in decision-making:
                        1. Information Density: How much data processing is needed?
                        2. Research Depth: What level of investigation is required?
                        3. Technical Complexity: What specialized knowledge is needed?
                        4. Tool Requirements: What tools might be needed?
                        5. Previous Performance: How have similar tasks been handled?

                        Return a structured JSON analysis matching this format:
                        {
                            "complexity_score": float (0-1),
                            "required_tools": ["tool1", "tool2"],
                            "confidence": float (0-1)
                        }""",
                },
                {"role": "user", "content": f"Analyze this task autonomously: {task}"},
            ]

            response = self._call_api(messages, stream=False)
            response_text = response.text
            logger.debug(f"Task analysis response: {response_text}")

            try:
                result = json.loads(response_text)
                return result
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in task analysis: {str(e)}")
                return {"error": "Invalid JSON response"}

        except Exception as e:
            logger.error(f"Task analysis error: {str(e)}")
            return {"error": str(e)}

    def _update_agent_performance(self, agent: BaseAgent, success: bool):
        """Update agent performance metrics"""
        try:
            agent_type = agent.__class__.__name__
            if not hasattr(agent, "confidence_score"):
                agent.confidence_score = 0.5

            if success:
                agent.confidence_score = min(1.0, agent.confidence_score + 0.05)
                logger.info(
                    f"Agent {agent_type} succeeded. Confidence increased to {agent.confidence_score:.2f}"
                )
            else:
                agent.confidence_score = max(0.1, agent.confidence_score - 0.05)
                logger.warning(
                    f"Agent {agent_type} failed. Confidence decreased to {agent.confidence_score:.2f}"
                )

            memory_entry = AgentMemory(
                type="performance",
                content={
                    "agent_type": agent_type,
                    "success": success,
                    "confidence_score": agent.confidence_score,
                    "timestamp": datetime.now().isoformat(),
                },
            )
            db.session.add(memory_entry)
            db.session.commit()
            logger.info(f"Updated performance metrics for {agent_type}")

        except Exception as e:
            logger.error(f"Error updating agent performance: {str(e)}")

    def _get_relevant_memories(self, prompt: str, limit: int = 5) -> List[Dict]:
        """Retrieve relevant past decisions"""
        try:
            recent_memories = (
                AgentMemory.query.order_by(AgentMemory.timestamp.desc())
                .limit(limit)
                .all()
            )
            return [memory.to_dict() for memory in recent_memories]
        except Exception as e:
            logger.error(f"Error retrieving memories: {str(e)}")
            return []

    def _update_memory(self, entry: Dict[str, Any]):
        """Update agent's memory in database"""
        try:
            logger.info(f"Creating memory entry for type: {entry['type']}")
            memory_entry = AgentMemory(
                type=entry["type"],
                content=entry["content"],
                metrics_snapshot={
                    "decisions_made": self.performance_metrics["decisions_made"],
                    "average_confidence": self.performance_metrics["average_confidence"],
                    "successful_executions": self.performance_metrics["successful_executions"],
                },
            )
            db.session.add(memory_entry)
            db.session.commit()
            # Access id after commit when the object is properly persisted
            if hasattr(memory_entry, 'id'):
                logger.info(f"Created memory entry with ID: {memory_entry.id} for type: {entry['type']}")
    
            # Clean up old entries keeping only last 100
            old_entries = (
                AgentMemory.query.order_by(AgentMemory.timestamp.desc())
                .offset(100)
                .all()
            )
            for old_entry in old_entries:
                if hasattr(old_entry, 'id'):
                    logger.info(f"Cleaning up memory entry with ID: {old_entry.id}")
                db.session.delete(old_entry)
            db.session.commit()
            logger.info("Old memory entries cleaned up")
    
        except Exception as e:
            logger.error(f"Error updating memory: {str(e)}")

    def _update_performance_metrics(self, action_type: str, confidence: float = 0.0):
        """Update performance metrics"""
        self.performance_metrics["decisions_made"] += 1
        self.performance_metrics["tool_usage"][action_type] = (
            self.performance_metrics["tool_usage"].get(action_type, 0) + 1
        )

        old_avg = self.performance_metrics["average_confidence"]
        n = self.performance_metrics["decisions_made"]
        self.performance_metrics["average_confidence"] = (
            (old_avg * (n - 1)) + confidence
        ) / n

    def determine_content_type(self, prompt: str) -> str:
        """Determine the most appropriate content type for the given prompt"""
        try:
            past_decisions = self._get_relevant_memories(prompt)

            complexity = self._analyze_task_complexity(prompt)
            logger.info(f"Task complexity analysis: {complexity}")
            self._update_memory({"type": "analysis", "content": complexity})

            agent_descriptions = {
                "thesis": self.specialized_agents["thesis"].AGENT_DESCRIPTION,
                "twitter": self.specialized_agents["twitter"].AGENT_DESCRIPTION,
                "financial": self.specialized_agents["financial"].AGENT_DESCRIPTION,
                "product": self.specialized_agents["product"].AGENT_DESCRIPTION,
                "fallback": self.specialized_agents["fallback"].AGENT_DESCRIPTION,
            }

            decision_history = "\n".join(
                [
                    f"Past decision: {m['type']}: {m['content']}"
                    for m in past_decisions
                    if m["type"] == "decision"
                ]
            )

            messages = [
                {
                    "role": "system",
                    "content" : f"""You are an autonomous decision-making agent.
                    Analyze the prompt and determine the most appropriate agent based on their specializations and research needs.

                    Agent specializations:
                    {json.dumps(agent_descriptions, indent=2)}

                    Search capabilities:
                    - Quick web searches for current information
                    - Academic searches for research content
                    - News searches for recent developments

                    Consider:
                    1. Topic complexity and scope
                    2. Required detail level
                    3. Target audience expectations
                    4. Information density needed
                    5. Best format for engagement
                    6. Primary focus of the content
                    7. Would current information improve the output?
                    8. Are there facts that should be verified?
                    9. Would examples help?
                    10. Is background research needed?
                    Return your decision in JSON format:
                    {{
                        "thoughts": {{
                            "text": "Content type decision",
                            "reasoning": "Detailed explanation of why this format fits best",
                            "plan": ["- How to proceed with this format"],
                            "criticism": "Potential drawbacks of this choice",
                            "speak": "Brief explanation for user"
                        }},
                        "content_type": "thesis|twitter|financial|product|fallback",
                        "confidence": float
                    }}

                    Only use fallback if MOST of these are true:
                        1. The query is extremely vague (e.g., "help", "do something")
                        2. No clear content type can be determined
                        3. Multiple very different interpretations are equally likely
                        4. No keywords match any agent's specialization""",
                },
                {
                    "role": "user",
                    "content": f"Task: {prompt}\n\nPrevious Decisions:\n{decision_history}",
                },
            ]

            response = self._call_api(messages, stream=False)

            try:
                if hasattr(response, "json"):
                    result = response.json()
                    if isinstance(result, dict) and "choices" in result:
                        content = result["choices"][0]["message"]["content"]
                        try:
                            parsed_result = json.loads(content)
                            content_type = parsed_result.get(
                                "content_type", "fallback"
                            ).lower()
                            confidence = parsed_result.get("confidence", 0.0)

                            if confidence < 0.5:
                                logger.info(
                                    f"Low confidence ({confidence}), using fallback"
                                )
                                content_type = "fallback"

                        except json.JSONDecodeError:
                            match = re.search(r'"content_type":\s*"([^"]+)"', content)
                            content_type = (
                                match.group(1).lower() if match else "fallback"
                            )
                    else:
                        content_type = "fallback"
                else:
                    response_text = str(response)
                    try:
                        parsed_result = json.loads(response_text)
                        content_type = parsed_result.get(
                            "content_type", "fallback"
                        ).lower()
                    except json.JSONDecodeError:
                        match = re.search(r'"content_type":\s*"([^"]+)"', response_text)
                        content_type = match.group(1).lower() if match else "fallback"

            except Exception as parse_error:
                logger.error(f"Error parsing response: {parse_error}")
                content_type = "fallback"

            logger.info(f"Content type decision: {content_type}")

            valid_types = ["thesis", "twitter", "financial", "product", "fallback"]
            return content_type if content_type in valid_types else "fallback"

        except Exception as e:
            logger.error(f"Content type determination error: {str(e)}")
            logger.error(f"Full error context: {traceback.format_exc()}")
            return "fallback"
