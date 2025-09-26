import logging
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class YoutubeAPI:
    def __init__(self, youtube_api_key):
        self.youtube = build('youtube', 'v3', developerKey=youtube_api_key)
        
    def search_ocean_disaster_videos(self, keywords, region_code='IN', max_results=10):
        try:
            search_response = self.youtube.search().list(
                q=' OR '.join(keywords),
                part='id,snippet',
                maxResults=max_results,
                type='video',
                regionCode=region_code,
                relevanceLanguage='en'
            ).execute()
            
            return self.process_youtube_videos(search_response)
        except Exception as e:
            logger.error(f"Error searching YouTube videos: {e}")
            return []
    
    def process_youtube_videos(self, search_response):
        videos = []
        for item in search_response.get('items', []):
            try:
                video_id = item['id']['videoId']
                video_details = self.get_video_details(video_id)
                if video_details:
                    videos.append(video_details)
            except Exception as e:
                logger.error(f"Error processing YouTube video: {e}")
                continue
        return videos
    
    def get_video_details(self, video_id):
        try:
            video_response = self.youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=video_id
            ).execute()
            
            if not video_response['items']:
                return None
                
            item = video_response['items'][0]
            snippet = item['snippet']
            stats = item['statistics']
            
            return {
                'platform': 'youtube',
                'id': video_id,
                'title': snippet['title'],
                'description': snippet.get('description', ''),
                'published_at': snippet['publishedAt'],
                'channel_title': snippet['channelTitle'],
                'view_count': stats.get('viewCount', 0),
                'like_count': stats.get('likeCount', 0),
                'comment_count': stats.get('commentCount', 0),
                'url': f'https://www.youtube.com/watch?v={video_id}'
            }
        except Exception as e:
            logger.error(f"Error getting YouTube video details: {e}")
            return None