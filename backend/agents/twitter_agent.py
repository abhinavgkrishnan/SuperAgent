from .base_agent import BaseAgent
from typing import Generator, List, Dict, Any, Optional
import json
import logging
import requests

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

        self.register_tool(
            name="sentiment_search",
            description="Fetch recent tweets for sentiment analysis",
            method=self._fetch_tweets,
            parameters={
                "query": "Search query for fetching tweets"
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
                    "content": """Generate engaging tweets about the topic. Each tweet should:
                    1. Be factual and informative
                    2. Use clear, concise language
                    3. Include relevant hashtags and emojis
                    4. Stay under 280 characters
                    5. Focus on key insights/findings
                    
                    Do NOT generate questions or clarifications.
                    Format: One tweet per line, prefixed with 🧵"""
                },
                {
                    "role": "user",
                    "content": f"Create a Twitter thread about: {topic}\nPrevious Content: {input_data if input_data else 'None'}"
                }
            ]
            
            response = self._call_api(messages, stream=False)
            return response.json()['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"Error generating tweets: {str(e)}")
            return f"Error generating tweets: {str(e)}"

    def _fetch_tweets(self, query: str) -> str:
        """
        Fetches tweets related to the input query and returns processed tweet texts.

        Parameters:
            query (str): The search query for fetching tweets.

        Returns:
            str: A string of tweet texts separated by two new lines or an error message.
        """
        try:
            url = "https://twitter154.p.rapidapi.com/search/search"
            querystring = {
                "query": query,
                "section": "top",
                "limit": "10",
                "language": "en"
            }
            headers = {
                "x-rapidapi-host": "twitter154.p.rapidapi.com",
                "x-rapidapi-key": "6515c7e475msh0ed450cd255b854p18231djsnc17678d20da3"
            }

            response = requests.get(url, headers=headers, params=querystring)

            if response.status_code == 200:
                output = response.json()
                tweet_texts = []
                for tweet in output.get("results", []):
                    tweet_text = tweet.get("text", "")
                    if tweet_text:
                        tweet_texts.append(tweet_text)
                        
                if tweet_texts:
                    logger.info(f"Fetched {len(tweet_texts)} tweets for query: {query}")
                    return "\n\n".join(tweet_texts)
                else:
                    logger.warning(f"No tweets found for query: {query}")
                    return "No tweets found for the given query."

            else:
                logger.error(f"Failed to fetch data. Status code: {response.status_code}, Response: {response.text}")
                return f"Failed to fetch data. Status code: {response.status_code}, Response: {response.text}"

        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching tweets: {e}")
            return f"An unexpected error occurred: {e}"
