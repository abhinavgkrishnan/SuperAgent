from .base_agent import BaseAgent
from typing import Generator, List, Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)

class TwitterAgent(BaseAgent):
    AGENT_DESCRIPTION = """
        Specialized in creating engaging social media content. Best suited for:
        - Short-form, impactful messages
        - Viral marketing content
        - Social media threads and discussions
        - Breaking news and updates
        - Quick tips and insights
        - Trending topics
        - Hashtag-optimized content
        - Community engagement posts
        """
    def __init__(self):
        super().__init__()
        self.agent_type = 'twitter'
        self._register_twitter_tools()
        logger.info("TwitterAgent initialized")
    
    def _register_twitter_tools(self):
        self.register_tool(
            name="twitter_generate",
            description="Generate Twitter thread from content",
            method=self._generate_thread,
            parameters={
                "topic": "Thread topic",
                "input_data": "Optional previous content"
            }
        )

    def _generate_thread(self, topic: str, input_data: Optional[str] = None) -> str:
        """Generate a Twitter thread on the given topic
        
        Args:
            topic (str): The main topic/subject for the thread
            input_data (Optional[str], optional): Previous content or context. Defaults to None.
            
        Returns:
            str: Generated Twitter thread with tweets separated by newlines
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are a Twitter thread writer. Create engaging, informative threads that:
                    1. Start with a hook
                    2. Break complex topics into digestible tweets
                    3. Use clear, concise language
                    4. Include relevant emojis and hashtags
                    5. End with a call to action
                    Each tweet should be prefixed with 🧵 and limited to 280 characters.
                    Format each tweet on a new line."""
                },
                {
                    "role": "user",
                    "content": f"Create a Twitter thread about: {topic}\nPrevious Content: {input_data if input_data else 'None'}"
                }
            ]
            
            response = self._call_api(messages, stream=False)
            return response.json()['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"Error generating Twitter thread: {str(e)}")
            return f"Error generating Twitter thread: {str(e)}"