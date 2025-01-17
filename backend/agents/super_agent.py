from .base_agent import BaseAgent
from typing import Generator, Dict, Any, List, Optional
import logging
import json
from datetime import datetime
from models import db, AgentMemory

logger = logging.getLogger(__name__)

class SuperAgent(BaseAgent):
    def __init__(self, search_agent=None, specialized_agents=None):
        # Use lower temperature for more precise decision-making
        super().__init__(temperature=0.3)
        self.memory: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Any] = {
            "decisions_made": 0,
            "successful_executions": 0,
            "tool_usage": {},
            "average_confidence": 0.0
        }
        self.search_agent = search_agent
        self.specialized_agents = specialized_agents or {}
        self._register_orchestrator_tools()
        logger.info("SuperAgent initialized with enhanced orchestration capabilities")

    def get_agent_for_type(self, content_type: str) -> BaseAgent:
        """Get the appropriate agent for the content type"""
        return self.specialized_agents.get(content_type, self.specialized_agents['thesis'])

    def _get_relevant_memories(self, prompt: str, limit: int = 5) -> List[Dict]:
        """Retrieve relevant past decisions"""
        try:
            recent_memories = AgentMemory.query.order_by(
                AgentMemory.timestamp.desc()
            ).limit(limit).all()
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
            result = json.loads(response.json()['choices'][0]['message']['content'])

            # Update metrics and memory
            self._update_performance_metrics("content_type_decision", result.get("confidence", 0.5))
            self._update_memory({
                "type": "decision",
                "content": result
            })

            content_type = result.get("content_type", "thesis").lower()
            logger.info(f"Content type decision: {content_type}, confidence: {result.get('confidence', 0.5)}")

            # Return the content type if it's valid, otherwise default to thesis
            valid_types = ['thesis', 'twitter', 'data_analysis', 'financial', 'product']
            return content_type if content_type in valid_types else 'thesis'

        except Exception as e:
            logger.error(f"Content type determination error: {str(e)}")
            return 'thesis'  # Default to thesis for safety

    def _update_memory(self, entry: Dict[str, Any]):
        """Update agent's memory in database"""
        try:
            memory_entry = AgentMemory(
                type=entry['type'],
                content=entry['content'],
                metrics_snapshot={
                    'decisions_made': self.performance_metrics["decisions_made"],
                    'average_confidence': self.performance_metrics["average_confidence"],
                    'successful_executions': self.performance_metrics["successful_executions"]
                }
            )
            db.session.add(memory_entry)
            db.session.commit()
            logger.info(f"Memory entry added: {entry['type']}")

            # Clean up old entries keeping only last 100
            old_entries = AgentMemory.query.order_by(
                AgentMemory.timestamp.desc()
            ).offset(100).all()
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
            parameters={"task": "Task description"}
        )

        self.register_tool(
            name="search_and_analyze",
            description="Search for information and analyze findings",
            method=self._search_and_analyze,
            parameters={"query": "Search query", "analysis_type": "Type of analysis needed"}
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
                    }"""
                },
                {
                    "role": "user",
                    "content": f"Analyze this task autonomously: {task}"
                }
            ]

            response = self._call_api(messages, stream=False)
            response_text = response.text
            logger.debug(f"Task analysis response: {response_text}")
            result = json.loads(response_text)
            return result
        except Exception as e:
            logger.error(f"Task analysis error: {str(e)}")
            return {"error": str(e)}

    def _search_and_analyze(self, query: str, analysis_type: str) -> List[Dict[str, Any]]:
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

    def _create_execution_plan(self, task: str, complexity: Dict[str, Any]) -> Dict[str, Any]:
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
                    }"""
                },
                {
                    "role": "user",
                    "content": f"Task: {task}\nComplexity Analysis: {json.dumps(complexity)}"
                }
            ]

            response = self._call_api(messages, stream=False)
            response_text = response.text
            logger.debug(f"Plan creation response: {response_text}")
            result = json.loads(response_text)
            self._update_performance_metrics("plan_creation", result.get("confidence", 0.5))
            return result
        except Exception as e:
            logger.error(f"Plan creation error: {str(e)}")
            return {"error": str(e)}

    def _update_performance_metrics(self, action_type: str, confidence: float = 0.0):
        """Update performance metrics"""
        self.performance_metrics["decisions_made"] += 1
        self.performance_metrics["tool_usage"][action_type] = self.performance_metrics["tool_usage"].get(action_type, 0) + 1

        # Update running average of confidence
        old_avg = self.performance_metrics["average_confidence"]
        n = self.performance_metrics["decisions_made"]
        self.performance_metrics["average_confidence"] = ((old_avg * (n - 1)) + confidence) / n

    def generate(self, prompt: str, search_results: Optional[List[Dict[str, Any]]] = None) -> Generator[str, None, None]:
        """
        SuperAgent doesn't generate content directly, it orchestrates other agents.
        This method is implemented to satisfy the abstract base class.
        """
        yield ""
