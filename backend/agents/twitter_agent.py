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
        logger.info("TwitterAgent initialized")

    def generate(self, prompt: str, search_results: Optional[List[Dict[str, Any]]] = None) -> Generator[str, None, None]:
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are a Twitter thread writer. Create engaging, informative threads that:
                    1. Start with a hook
                    2. Break complex topics into digestible tweets
                    3. Use clear, concise language
                    4. Include relevant emojis
                    5. End with a call to action
                    Each tweet should be prefixed with 🧵 and limited to 280 characters.
                    Format each tweet on a new line."""
                },
                {
                    "role": "user",
                    "content": f"Create a Twitter thread about: {prompt}\nSearch Results: {json.dumps(search_results, indent=2) if search_results else 'No search results available.'}"
                }
            ]
    
            response = self._call_api(messages)
    
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
                                        'type': 'twitter',
                                        'content': delta['content']
                                    })
                        except Exception as e:
                            logger.error(f"Error parsing response line: {str(e)}")
                            logger.error(f"Response line causing error: {content}")
                            continue
    
        except Exception as e:
            logger.error(f"Error generating Twitter thread: {str(e)}")
            yield json.dumps({
                'type': 'twitter',
                'error': str(e)
            })