
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Import our custom API modules
from API_Fetching.youtubeAPI import YoutubeAPI
from API_Fetching.twitterAPI import TwitterAPI
from API_Fetching.redditAPI import RedditAPI
from API_Fetching.websearchAPI import WebSearchAPI

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class SocialMediaCollector:
    def __init__(self):
        # Load API keys from environment
        youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        twitter_bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
        reddit_client_secret = os.getenv('REDDIT_SECRET_KEY')
        reddit_user_agent = os.getenv('REDDIT_USER_AGENT', 'OceanDisasterMonitor/1.0')
        google_api_key = os.getenv('GOOGLE_CUSTOM_SEARCH_API')
        google_cx = os.getenv('GOOGLE_CUSTOM_SEARCH_ID')
        
        logger.info(f"YouTube API key: {'Available' if youtube_api_key else 'Missing'}")
        logger.info(f"Twitter Bearer Token: {'Available' if twitter_bearer_token else 'Missing'}")
        logger.info(f"Reddit Client ID: {'Available' if reddit_client_id else 'Missing'}")
        logger.info(f"Reddit Client Secret: {'Available' if reddit_client_secret else 'Missing'}")
        logger.info(f"Google Custom Search Key: {'Available' if google_api_key else 'Missing'}")
        logger.info(f"Google Custom Search ID: {'Available' if google_cx else 'Missing'}")
        # Initialize APIs
        self.youtube_api = YoutubeAPI(youtube_api_key) if youtube_api_key else None
        self.twitter_api = TwitterAPI(twitter_bearer_token) if twitter_bearer_token else None
        
        # Initialize Reddit API only if all credentials are provided
        if all([reddit_client_id, reddit_client_secret, reddit_user_agent]):
            self.reddit_api = RedditAPI(reddit_client_id, reddit_client_secret, reddit_user_agent)
        else:
            self.reddit_api = None
            logger.warning("Reddit API credentials incomplete - skipping Reddit")
        # Initialize Google API only if all credentials are provided
        if all([google_api_key,google_cx]):
            self.web_search_api = WebSearchAPI(google_api_key,google_cx)
        # Ocean disaster keywords
        self.keywords = [
            'tsunami', 'storm surge', 'coastal flooding', 'high waves',
            'cyclone', 'hurricane', 'sea level rise', 'tidal waves',
            'coastal erosion', 'storm tide', 'rogue waves', 'flood',
            'monsoon', 'heavy rain', 'landslide', 'disaster', 'emergency',
            'ocean warning', 'marine alert', 'coastal danger',
            # Proper Hindi keywords (fixed encoding)
            'सुनामी', 'तूफान', 'बाढ़', 'चक्रवात', 'आपदा', 'समुद्री तूफान'
        ]
    
    def collect_youtube_data(self, max_results=10):
        """Collect data from YouTube"""
        if not self.youtube_api:
            logger.warning("YouTube API not configured")
            return []
        
        try:
            logger.info("Fetching YouTube data...")
            data = self.youtube_api.search_ocean_disaster_videos(
                self.keywords, max_results=max_results
            )
            logger.info(f"Collected {len(data)} YouTube videos")
            return data
        except Exception as e:
            logger.error(f"Error collecting YouTube data: {e}")
            return []
    
    def collect_twitter_data(self, max_results=10):
        """Collect data from Twitter"""
        if not self.twitter_api:
            logger.warning("Twitter API not configured")
            return []
        
        try:
            logger.info("Fetching Twitter data...")
            data = self.twitter_api.fetch_ocean_disaster_tweets(
                self.keywords, max_results=max_results
            )
            logger.info(f"Collected {len(data)} Twitter posts")
            return data
        except Exception as e:
            logger.error(f"Error collecting Twitter data: {e}")
            return []
    
    def collect_reddit_data(self, max_results=10):
        """Collect data from Reddit"""
        if not self.reddit_api:
            logger.warning("Reddit API not configured")
            return []
        
        try:
            logger.info("Fetching Reddit data...")
            data = self.reddit_api.search_disaster_posts(
                self.keywords, limit=max_results
            )
            logger.info(f"Collected {len(data)} Reddit posts")
            return data
        except Exception as e:
            logger.error(f"Error collecting Reddit data: {e}")
            return []
        
    def collect_web_search_data(self,max_results=-10):
        if not self.web_search_api:
            logger.warning("Google API not configured")
            return []
        try:
            logger.info("Fetching Web Search Data...")
            data = self.web_search_api.search_disaster_news(
                self.keywords,max_results
            )
            data = self.web_search_api.search_news_sites(
                self.keywords,max_results
            )           
            logger.info(f"Collected {len(data)} Web searches")
            return data
        except Exception as e:
            logger.error(f"Error collecting Web data : {e}")
            return[]
        
    
    def collect_all_data(self, max_results_per_platform=10):
        """Collect data from all available platforms"""
        all_data = {
            'timestamp': datetime.now().isoformat(),
            'twitter_posts': [],
            'reddit_posts': [],
            'youtube_data': [],
            'web_search_data': []
        }
        
        # Collect from each platform
        all_data['twitter_posts'] = self.collect_twitter_data(max_results_per_platform)
        all_data['reddit_posts'] = self.collect_reddit_data(max_results_per_platform)
        all_data['youtube_data'] = self.collect_youtube_data(max_results_per_platform)
        all_data['web_search_data'] = self.collect_web_search_data(max_results_per_platform)
        return all_data
    
    def collect_specific_platform(self, platform, max_results=10):
        """Collect data from a specific platform only"""
        platform = platform.lower()
        
        if platform == 'twitter':
            return self.collect_twitter_data(max_results)
        elif platform == 'reddit':
            return self.collect_reddit_data(max_results)
        elif platform == 'youtube':
            return self.collect_youtube_data(max_results)
        else:
            logger.error(f"Unknown platform: {platform}")
            return []
    
    def save_raw_data(self, data, filename="routes/FetchedData/*"):
        """Save collected data to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = 'FetchedData'
            filename = os.path.join(output_dir,f"FetchedData_{timestamp}.json")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Raw data saved to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error saving data to {filename}: {e}")
            return None
    
    def test_all_apis(self):
        """Test all API connections"""
        results = {}
        
        # Test YouTube
        if self.youtube_api:
            try:
                test_data = self.youtube_api.search_ocean_disaster_videos(['tsunami'], max_results=1)
                results['youtube'] = len(test_data) > 0
            except:
                results['youtube'] = False
        else:
            results['youtube'] = False
        
        # Test Twitter
        if self.twitter_api:
            try:
                test_data = self.twitter_api.fetch_ocean_disaster_tweets(['tsunami'], max_results=1)
                results['twitter'] = len(test_data) >= 0  # Even 0 results is success
            except:
                results['twitter'] = False
        else:
            results['twitter'] = False
        
        # Test Reddit
        if self.reddit_api:
            results['reddit'] = self.reddit_api.test_connection()
        else:
            results['reddit'] = False
        
        # Test Google
        if self.web_search_api:
            try:
                web_test_data = self.web_search_api.search_disaster_news(['tsunami'],max_results=1)
                results['Web Search'] = len(web_test_data) >= 0
            except:
                results['Web Search'] = False
        else:
            results['Web Search'] = False

def main():
    """Main function to demonstrate usage"""
    # Initialize the collector
    collector = SocialMediaCollector()
    
    # Test API connections first
    logger.info("Testing API connections...")
    api_status = collector.test_all_apis()
    for platform, status in api_status.items():
        logger.info(f"{platform.capitalize()} API: {'✓ Working' if status else '✗ Failed'}")
        
    # Collect data from all platforms
    logger.info("\n" + "="*50)
    logger.info("Starting data collection...")
    data = collector.collect_all_data(max_results_per_platform=5)
    
    # Save the data
    filename = collector.save_raw_data(data)

    print(f"\n=== COLLECTION SUMMARY ===")
    print(f"Collection completed at {data['timestamp']}")
    print(f"Twitter posts: {len(data['twitter_posts'])}")
    print(f"Reddit posts: {len(data['reddit_posts'])}")
    print(f"YouTube videos: {len(data['youtube_data'])}")
    print(f"Web Search data: {len(data['web_search_data'])}")
    print(f"Data saved to: {filename}")
    
    # Print sample data
    if data['twitter_posts']:
        print(f"\nSample Twitter post: {data['twitter_posts'][0]['text'][:100]}...")
    if data['reddit_posts']:
        print(f"Sample Reddit post: {data['reddit_posts'][0]['title'][:100]}...")
    if data['youtube_data']:
        print(f"Sample YouTube video: {data['youtube_data'][0]['title'][:100]}...")
    if data['web_search_data']:
        print(f"Sample Web Search data: {data['web_search_data'][0]['title'][:100]}...")
if __name__ == "__main__":
    main()