from .base_agent import BaseAgent
from typing import Generator, Dict, Any, List, Optional
import logging
import json
import asyncio
from datetime import datetime
from models import db, AgentMemory
import re
import traceback

# Clear any existing log handlers to prevent duplicate logging issues
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Create a log file handler
log_file = "super_agent.log"

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Capture all logs (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
    handlers=[
        logging.FileHandler(
            log_file, mode="w"
        ),  # 'w' ensures the file is overwritten for fresh logs
        logging.StreamHandler(),  # Also print logs to the console
    ],
)

logger = logging.getLogger(__name__)
logger.info("Logging system initialized successfully")


class SuperAgent(BaseAgent):
    def __init__(self, search_agent=None, specialized_agents=None):
        # Use lower temperature for more precise decision-making
        super().__init__(temperature=0.3)
        self.memory: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Any] = {
            "decisions_made": 0,
            "successful_executions": 0,
            "tool_usage": {},
            "average_confidence": 0.0,
        }
        self.search_agent = search_agent
        self.specialized_agents = specialized_agents or {}
        self._register_orchestrator_tools()
        logger.info("SuperAgent initialized with enhanced orchestration capabilities")

    def get_agent_for_type(self, content_type: str) -> BaseAgent:
        """Get the appropriate agent for the content type with fallback"""
        try:
            return self.specialized_agents.get(
                content_type, self.specialized_agents["thesis"]
            )
        except Exception as e:
            logger.error(f"Error getting agent for type {content_type}: {str(e)}")
            return self.specialized_agents["thesis"]  # Fallback to thesis agent

    async def execute_tasks(self, task: str) -> Any:
        """Iterate through agents in a chain until final output is generated."""
        task_queue = [{"task": task, "status": "pending", "attempts": 0}]
        final_answer = None
        primary_agent: Optional[BaseAgent] = None

        logger.info(f"Starting task execution: {task}")

        while task_queue:
            current_task = task_queue.pop(0)
            logger.debug(f"Processing task: {current_task}")

            if current_task["attempts"] >= 3:
                logger.warning(f"Task exceeded retry limit: {current_task['task']}")
                continue

            try:
                primary_agent = self.get_agent_for_type(
                    self.determine_content_type(current_task["task"])
                )
                if primary_agent is None:
                    raise ValueError("Failed to get a valid agent for task")

                supporting_agents = self.assign_agents(current_task["task"])
                logger.info(
                    f"Primary agent assigned: {primary_agent.__class__.__name__}"
                )
                logger.info(
                    f"Supporting agents assigned: {[agent.__class__.__name__ for agent in supporting_agents]}"
                )

                # Step 1: Primary Agent Processes Task
                response = await self._process_task_with_agent(
                    primary_agent, current_task["task"]
                )
                intermediate_result = response.get("result", "")

                logger.info(
                    f"Primary agent completed task with status: {response.get('status')}"
                )
                logger.debug(f"Intermediate result: {intermediate_result}")

                # Step 2: Pass Intermediate Results to Supporting Agents
                for agent in supporting_agents:
                    response = await self._process_task_with_agent(
                        agent, intermediate_result
                    )
                    intermediate_result += "\n\n" + response.get("result", "")
                    logger.info(
                        f"Supporting agent {agent.__class__.__name__} completed processing."
                    )

                if response.get("status") == "completed":
                    final_answer = intermediate_result
                    self._update_agent_performance(primary_agent, success=True)
                    logger.info(f"Task execution completed successfully.")
                else:
                    logger.error(f"Unexpected task status: {response.get('status')}")
                    self._update_agent_performance(primary_agent, success=False)

            except Exception as e:
                logger.error(f"Task execution error: {str(e)}")
                current_task["attempts"] += 1
                if current_task["attempts"] < 3:
                    task_queue.append(current_task)

                if primary_agent:
                    self._handle_agent_failure(current_task["task"], primary_agent)

        logger.info(f"Final result for task: {final_answer}")
        return final_answer

    def assign_agents(self, task: str) -> List[BaseAgent]:
        """Determine which agents should handle different aspects of the task."""
        primary_agent = self.get_agent_for_type(self.determine_content_type(task))
        supporting_agents = []

        # Add search agent if research is needed
        if any(
            keyword in task.lower()
            for keyword in ["research", "analyze", "find", "search"]
        ):
            if self.search_agent:
                supporting_agents.append(self.search_agent)

        # Add data analysis agent for analytical tasks
        if any(
            keyword in task.lower()
            for keyword in ["analyze", "compare", "statistics", "data"]
        ):
            data_agent = self.specialized_agents.get("data_analysis")
            if data_agent:
                supporting_agents.append(data_agent)

        return [primary_agent] + supporting_agents

    async def _process_task_with_agent(
        self, agent: BaseAgent, task: str
    ) -> Dict[str, Any]:
        """Process a single task with an agent"""
        try:
            # Convert the generator to async
            response = ""
            async for chunk in self._agent_generate(agent, task):
                response += chunk

            return {"status": "completed", "result": response}
        except Exception as e:
            logger.error(f"Agent processing error: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _agent_generate(self, agent: BaseAgent, task: str):
        """Wrapper to make agent.generate async"""
        for chunk in agent.generate(task):
            yield chunk

    def _handle_agent_failure(self, task: str, failed_agent: BaseAgent):
        """Handle agent failures with fallback mechanisms"""
        logger.warning(
            f"Agent {failed_agent.__class__.__name__} failed, attempting recovery for task: {task}"
        )

        try:
            fallback_agent = self.specialized_agents.get("thesis")
            if fallback_agent and fallback_agent != failed_agent:
                logger.info(f"Attempting fallback with thesis agent")
                return fallback_agent.generate(task)

            if self.search_agent and self.search_agent != failed_agent:
                logger.info(f"Attempting fallback with search agent")
                search_results = self.search_agent.search(task)
                if search_results:
                    return json.dumps(
                        {
                            "type": "fallback",
                            "content": f"Based on search results: {json.dumps(search_results[:2])}",
                        }
                    )

            logger.error("All fallback mechanisms failed")
            return json.dumps(
                {
                    "type": "error",
                    "content": "Unable to process task after multiple attempts",
                }
            )

        except Exception as e:
            logger.error(f"Error in fallback handling: {str(e)}")
            return json.dumps(
                {
                    "type": "error",
                    "content": f"Critical error in fallback handling: {str(e)}",
                }
            )

    def _update_agent_performance(self, agent: BaseAgent, success: bool):
        """Update agent performance metrics"""
        try:
            agent_type = agent.__class__.__name__
            if not hasattr(agent, "confidence_score"):
                agent.confidence_score = 0.5  # Initialize if not exists

            # Update confidence score
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

            # Store performance metrics
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

    def determine_content_type(self, prompt: str) -> str:
            """Determine the most appropriate content type for the given prompt"""
            try:
                # Get relevant past decisions
                past_decisions = self._get_relevant_memories(prompt)

                # First, analyze task complexity with autonomous capabilities
                complexity = self._analyze_task_complexity(prompt)
                logger.info(f"Task complexity analysis: {complexity}")
                self._update_memory({"type": "analysis", "content": complexity})

                # Include past decisions in the context
                decision_history = "\n".join([
                    f"Past decision: {m['type']}: {m['content']}"
                    for m in past_decisions if m['type'] == 'decision'
                ])

                # Create execution plan autonomously
                plan = self._create_execution_plan(prompt, complexity)
                logger.info(f"Execution plan: {plan}")
                self._update_memory({"type": "plan", "content": plan})

                # Enhanced decision making for content type
                messages = [
                    {
                        "role": "system",
                        "content": """You are an autonomous decision-making agent.
                        Analyze the prompt and determine the most appropriate content format
                        based on these criteria:

                        For Twitter format (return "twitter"):
                        - Short, concise topics that can be expressed in a few sentences
                        - News, announcements, or quick updates
                        - Personal experiences or opinions
                        - Content that benefits from hashtags and viral sharing

                        For Thesis format (return "thesis"):
                        - Complex topics requiring detailed explanation
                        - Academic or research-heavy subjects
                        - Topics needing multiple sections or chapters
                        - Subjects requiring citations and references

                        For Data Analysis format (return "data_analysis"):
                        - Pure statistical analysis requests
                        - Data visualization needs
                        - Pattern recognition in datasets
                        - General trend analysis without financial context
                        - Scientific data interpretation

                        For Financial Report format (return "financial"):
                        - Financial analysis and reporting
                        - Market research and trends
                        - Cryptocurrency and digital asset analysis
                        - Investment analysis and recommendations
                        - Economic insights and forecasts
                        - Price trends and market behavior
                        - Trading patterns and market indicators
                        - Asset valuation and performance metrics

                        For Product Description format (return "product"):
                        - Product features and specifications
                        - Marketing copy and product positioning
                        - Technical product documentation
                        - Product comparisons and reviews

                        Consider:
                        1. Topic complexity and scope
                        2. Required detail level
                        3. Target audience expectations
                        4. Information density needed
                        5. Best format for engagement
                        6. Primary focus (financial vs purely statistical)

                        Return your decision in JSON format:
                        {
                            "thoughts": {
                                "text": "Content type decision",
                                "reasoning": "Detailed explanation of why this format fits best",
                                "plan": ["- How to proceed with this format"],
                                "criticism": "Potential drawbacks of this choice",
                                "speak": "Brief explanation for user"
                            },
                            "content_type": "thesis|twitter|data_analysis|financial|product",
                            "confidence": float
                        }"""
                    },
                    {
                        "role": "user",
                        "content": f"Task: {prompt}\n\nPrevious Decisions:\n{decision_history}"
                    }
                ]

                response = self._call_api(messages, stream=False)
                result = response.json()['choices'][0]['message']['content']
                # Properly parse the JSON string from the content
                result = json.loads(result)

                content_type = result.get("content_type", "thesis").lower()
                logger.info(f"Content type decision: {content_type}, confidence: {result.get('confidence', 0.5)}")

                valid_types = ['thesis', 'twitter', 'data_analysis', 'financial', 'product']
                return content_type if content_type in valid_types else 'thesis'

            except Exception as e:
                logger.error(f"Content type determination error: {str(e)}")
                logger.error(f"Full error context: {traceback.format_exc()}")  # Add more detailed error logging
                return 'thesis'

    def _update_memory(self, entry: Dict[str, Any]):
        """Update agent's memory in database"""
        try:
            memory_entry = AgentMemory(
                type=entry["type"],
                content=entry["content"],
                metrics_snapshot={
                    "decisions_made": self.performance_metrics["decisions_made"],
                    "average_confidence": self.performance_metrics[
                        "average_confidence"
                    ],
                    "successful_executions": self.performance_metrics[
                        "successful_executions"
                    ],
                },
            )
            db.session.add(memory_entry)
            db.session.commit()
            logger.info(f"Memory entry added: {entry['type']}")

            # Clean up old entries keeping only last 100
            old_entries = (
                AgentMemory.query.order_by(AgentMemory.timestamp.desc())
                .offset(100)
                .all()
            )
            for entry in old_entries:
                db.session.delete(entry)
            db.session.commit()
            logger.info("Old memory entries cleaned up")

        except Exception as e:
            logger.error(f"Error updating memory: {str(e)}")
            # Continue execution even if memory update fails
            pass

    def _register_orchestrator_tools(self):
        """Register orchestrator-specific tools"""
        self.register_tool(
            name="analyze_task",
            description="Analyze task complexity and requirements",
            method=self._analyze_task_complexity,
            parameters={"task": "Task description"},
        )

        self.register_tool(
            name="search_and_analyze",
            description="Search for information and analyze findings",
            method=self._search_and_analyze,
            parameters={
                "query": "Search query",
                "analysis_type": "Type of analysis needed",
            },
        )

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

            # Attempt to parse the JSON response
            try:
                result = json.loads(response_text)
                return result
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in task analysis: {str(e)}")
                return {"error": "Invalid JSON response"}

        except Exception as e:
            logger.error(f"Task analysis error: {str(e)}")
            return {"error": str(e)}

    def _search_and_analyze(
        self, query: str, analysis_type: str
    ) -> List[Dict[str, Any]]:
        """Integrated search and analysis capabilities using SerperAgent"""
        try:
            # Use SerperAgent for search if available
            if self.search_agent:
                search_type = "scholar" if analysis_type == "academic" else "general"
                search_results = self.search_agent.search(query, search_type)
                return search_results
            return []  # Return empty list if search agent not available
        except Exception as e:
            logger.error(f"Search and analysis error: {str(e)}")
            return []

    def _create_execution_plan(
        self, task: str, complexity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhanced execution planning with autonomous decision-making"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """Create a detailed execution plan.
                        Return a JSON plan with:
                        {
                            "execution_steps": [
                                {
                                    "order": int,
                                    "description": str,
                                    "tools_needed": [str],
                                    "success_criteria": str
                                }
                            ],
                            "confidence": float
                        }""",
                },
                {
                    "role": "user",
                    "content": f"Task: {task}\nComplexity Analysis: {json.dumps(complexity)}",
                },
            ]

            response = self._call_api(messages, stream=False)
            response_text = response.text
            logger.debug(f"Plan creation response: {response_text}")

            # Attempt to parse the JSON response
            try:
                result = json.loads(response_text)
                self._update_performance_metrics(
                    "plan_creation", result.get("confidence", 0.5)
                )
                return result
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in plan creation: {str(e)}")
                return {"error": "Invalid JSON response"}

        except Exception as e:
            logger.error(f"Plan creation error: {str(e)}")
            return {"error": str(e)}

    def _update_performance_metrics(self, action_type: str, confidence: float = 0.0):
        """Update performance metrics"""
        self.performance_metrics["decisions_made"] += 1
        self.performance_metrics["tool_usage"][action_type] = (
            self.performance_metrics["tool_usage"].get(action_type, 0) + 1
        )

        # Update running average of confidence
        old_avg = self.performance_metrics["average_confidence"]
        n = self.performance_metrics["decisions_made"]
        self.performance_metrics["average_confidence"] = (
            (old_avg * (n - 1)) + confidence
        ) / n

    def generate(
        self, prompt: str, search_results: Optional[List[Dict[str, Any]]] = None
    ) -> Generator[str, None, None]:
        """
        SuperAgent's generate method now supports the enhanced task execution system
        """
        event_loop = None
        try:
            # Create event loop for async execution
            event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(event_loop)

            # Execute tasks and get result
            result = event_loop.run_until_complete(self.execute_tasks(prompt))

            if result:
                yield json.dumps({"type": "super_agent", "content": result})
            else:
                yield json.dumps(
                    {
                        "type": "error",
                        "content": "Task execution failed to produce results",
                    }
                )

        except Exception as e:
            logger.error(f"Error in SuperAgent generate: {str(e)}")
            yield json.dumps({"type": "error", "content": str(e)})
        finally:
            if event_loop:
                try:
                    event_loop.close()
                except:
                    pass
