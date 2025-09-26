import time
import logging
import praw

logger = logging.getLogger(__name__)

class RedditAPI:
    def __init__(self, client_id, client_secret, user_agent):
        try:
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
                check_for_async=False
            )
            
            # Test the connection with a simple request
            test_subreddit = self.reddit.subreddit('test')
            _ = test_subreddit.display_name
            logger.info("Reddit API initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Reddit API: {e}")
            logger.error(f"Error details: {str(e)}")
            self.reddit = None
    
    def search_disaster_posts(self, keywords, limit=10):
        if not self.reddit:
            logger.warning("Reddit API not available")
            return []
        
        # Focus on more active subreddits with disaster/weather content
        subreddits = [
            "india", "IndiaSpeaks", "indianews", "mumbai", "chennai", 
            "Kerala", "delhi", "bangalore", "kolkata", "pune",
            "weather", "naturaldisasters", "worldnews", "news"
        ]
        
        disaster_posts = []
        posts_per_subreddit = max(1, limit // len(subreddits))
        
        focused_keywords = ['tsunami', 'cyclone', 'flood', 'storm', 'disaster']
        
        for subreddit_name in subreddits:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                logger.info(f"Searching in r/{subreddit_name}")
                
                for keyword in focused_keywords:
                    try:
                        search_results = list(subreddit.search(
                            keyword, 
                            limit=posts_per_subreddit,
                            sort="new",
                            time_filter="month"
                        ))
                        
                        logger.info(f"Found {len(search_results)} posts for '{keyword}' in r/{subreddit_name}")
                        
                        for post in search_results:
                            try:
                                post_data = {
                                    'platform': 'reddit',
                                    'id': post.id,
                                    'title': post.title,
                                    'selftext': post.selftext[:500] if post.selftext else "",
                                    'url': post.url,
                                    'score': post.score,
                                    'created_utc': post.created_utc,
                                    'subreddit': str(post.subreddit),
                                    'author': str(post.author) if post.author else "deleted",
                                    'num_comments': post.num_comments,
                                    'keyword_matched': keyword,
                                    'permalink': f"https://reddit.com{post.permalink}"
                                }
                                disaster_posts.append(post_data)
                                
                            except Exception as e:
                                logger.error(f"Error processing post {post.id}: {e}")
                                continue
                                
                    except Exception as e:
                        logger.error(f"Error searching for '{keyword}' in r/{subreddit_name}: {e}")
                        continue
                    
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Error accessing subreddit r/{subreddit_name}: {e}")
                continue
                
            time.sleep(1)
        
        logger.info(f"Total Reddit posts collected: {len(disaster_posts)}")
        return disaster_posts

    def test_connection(self):
        """Test Reddit API connection"""
        if not self.reddit:
            return False
            
        try:
            test_sub = self.reddit.subreddit('test')
            _ = test_sub.display_name
            logger.info("Reddit API test successful")
            return True
        except Exception as e:
            logger.error(f"Reddit API test failed: {e}")
            return False