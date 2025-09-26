
import time
import logging
import tweepy

logger = logging.getLogger(__name__)

class TwitterAPI:
    def __init__(self, twitter_api_key):
        self.client = tweepy.Client(bearer_token=twitter_api_key)
        self.last_request_time = 0
        self.request_count = 0
        self.RATE_LIMIT_DELAY = 1  
        self.MAX_REQUESTS_PER_15_MIN = 1  
    
    def fetch_ocean_disaster_tweets(self, keywords, max_results=10):
        try:

            self._check_rate_limit()
            

            adjusted_max_results = 10
            
            query = self.build_query(keywords)
            logger.info(f"Using Twitter query: {query}")

            tweets_response = self.client.search_recent_tweets(
                query=query,
                max_results=adjusted_max_results,

                tweet_fields=['created_at', 'public_metrics'],
            )
            
            if not tweets_response.data:
                logger.info("No tweets found")
                return []
                
            return self.process_tweets(tweets_response)
            
        except tweepy.TooManyRequests as e:
            logger.warning(f"Twitter rate limit exceeded. Waiting 15 minutes...")
            time.sleep(900)  # Wait 15 minutes
            return []
        except tweepy.Forbidden as e:
            logger.error(f"Twitter API access forbidden - check your API tier: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching Twitter data: {e}")
            return []
    
    def _check_rate_limit(self):
        """Implement very conservative rate limiting for free tier"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        min_delay = 60  
        if elapsed < min_delay:
            sleep_time = min_delay - elapsed
            logger.info(f"Free tier rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def build_query(self, keywords):
        main_keywords = ['tsunami', 'cyclone', 'flood']

        return ' OR '.join(main_keywords)
    
    def process_tweets(self, tweets_response):
        tweets = []

        for tweet in tweets_response.data:            
            tweet_data = {
                'platform': 'twitter',
                'id': tweet.id,
                'text': tweet.text,
                'created_at': tweet.created_at.isoformat() if tweet.created_at else None,
                'like_count': tweet.public_metrics.get('like_count', 0) if tweet.public_metrics else 0,
                'retweet_count': tweet.public_metrics.get('retweet_count', 0) if tweet.public_metrics else 0,
                'url': f'https://twitter.com/user/status/{tweet.id}'
            }
            
            tweets.append(tweet_data)
        
        return tweets