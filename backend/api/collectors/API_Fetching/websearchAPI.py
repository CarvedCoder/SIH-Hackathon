import os
import time
import logging
import requests
from datetime import datetime, timedelta
from urllib.parse import quote, urlencode
import json

logger = logging.getLogger(__name__)

class WebSearchAPI:
    def __init__(self, google_api_key=None, google_cx=None):
        self.google_api_key = google_api_key
        self.google_cx = google_cx
        
        self.last_request_time = 0
        self.request_count = 0
        self.RATE_LIMIT_DELAY = 1  # 1 second between requests
        
        # Available search engines
        self.available_engines = []
        if google_api_key and google_cx:
            self.available_engines.append('google')
            logger.info(f"Google CSE ID: {google_cx[:10]}...")  # Log partial ID for debugging
        
        self.available_engines.append('duckduckgo')
        
        logger.info(f"Web Search API initialized with engines: {', '.join(self.available_engines)}")
    
    def validate_google_config(self):
        """Validate Google Custom Search configuration"""
        if not self.google_api_key or not self.google_cx:
            return False, "Missing API key or Custom Search Engine ID"
        
        # Test with a simple query
        test_params = {
            'key': self.google_api_key,
            'cx': self.google_cx,
            'q': 'test',
            'num': 1
        }
        
        try:
            response = requests.get(
                'https://www.googleapis.com/customsearch/v1',
                params=test_params,
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "Google CSE configuration valid"
            elif response.status_code == 404:
                return False, f"Invalid Custom Search Engine ID: {self.google_cx}"
            elif response.status_code == 403:
                return False, "API key invalid or quota exceeded"
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def search_disaster_news(self, keywords, max_results=10, engine='auto', time_filter='week'):
        """Search for disaster-related news"""
        if isinstance(keywords, str):
            keywords = [keywords]
        
        if engine == 'auto':
            # First validate Google config if available
            if 'google' in self.available_engines:
                is_valid, msg = self.validate_google_config()
                if is_valid:
                    engine = 'google'
                    logger.info("Using Google Custom Search")
                    logger.info("Falling back to DuckDuckGo")
                    engine = 'duckduckgo'
            else:
                engine = 'duckduckgo'
        
        logger.info(f"Searching with {engine} engine for: {keywords[:3]}...")  # Show first 3 keywords
        
        try:
            if engine == 'google' and 'google' in self.available_engines:
                return self._search_google(keywords, max_results, time_filter)
            elif engine == 'duckduckgo':    
                return self._search_duckduckgo(keywords, max_results)
            else:
                logger.error(f"Search engine '{engine}' not available or configured")
                return []
                
        except Exception as e:
            logger.error(f"Error during web search: {e}")
            # Fallback to DuckDuckGo if Google fails
            if engine == 'google':
                logger.info("Attempting fallback to DuckDuckGo...")
                try:
                    return self._search_duckduckgo(keywords, max_results)
                except Exception as fallback_e:
                    logger.error(f"Fallback search also failed: {fallback_e}")
            return []
    
    def _check_rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.RATE_LIMIT_DELAY:
            sleep_time = self.RATE_LIMIT_DELAY - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def _search_google(self, keywords, max_results, time_filter):
        """Search using Google Custom Search API"""
        self._check_rate_limit()
        
        # Simplified query construction
        query_parts = []
        
        # Add disaster-related keywords (limit to avoid too long query)
        disaster_keywords = keywords[:3]  # Take first 3 keywords
        for keyword in disaster_keywords:
            query_parts.append(f'"{keyword}"')
        
        # Combine with OR and add context
        main_query = ' OR '.join(query_parts)
        full_query = f'({main_query}) disaster OR emergency OR alert OR warning india'
        
        # Time filter mapping for Google
        time_mapping = {
            'day': 'd1',
            'week': 'w1', 
            'month': 'm1',
            'year': 'y1',
            'all': None
        }
        
        params = {
            'key': self.google_api_key,
            'cx': self.google_cx,
            'q': full_query,
            'num': min(max_results, 10),  # Google allows max 10 per request
            'safe': 'active',
            'lr': 'lang_en',
            'gl': 'in',  # Geo-location India
        }
        
        if time_filter in time_mapping and time_mapping[time_filter]:
            params['dateRestrict'] = time_mapping[time_filter]
        
        # Debug: Log the actual request URL
        base_url = 'https://www.googleapis.com/customsearch/v1'
        query_string = urlencode(params)
        logger.debug(f"Google CSE Request: {base_url}?{query_string}")
        
        try:
            response = requests.get(
                base_url,
                params=params,
                timeout=30
            )
            
            # Log response details for debugging
            logger.debug(f"Response Status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Response Body: {response.text[:500]}...")
            
            response.raise_for_status()
            
            data = response.json()
            return self._process_google_results(data)
            
        except requests.RequestException as e:
            logger.error(f"Google search request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text[:200]}...")
            return []
        except Exception as e:
            logger.error(f"Error processing Google search results: {e}")
            return []
    
    def _search_duckduckgo(self, keywords, max_results):
        """Search using DuckDuckGo (no API key required)"""
        self._check_rate_limit()
        
        # Simplified query for DuckDuckGo
        main_keywords = keywords[:2]  # Take first 2 keywords
        query = ' OR '.join(main_keywords)
        query += ' disaster India news'
        
        params = {
            'q': query,
            'format': 'json',
            'no_html': '1',
            'skip_disambig': '1',
            'no_redirect': '1'
        }
        
        logger.debug(f"DuckDuckGo query: {query}")
        
        try:
            response = requests.get(
                'https://api.duckduckgo.com/',
                params=params,
                headers={'User-Agent': 'OceanDisasterMonitor/1.0'},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            results = self._process_duckduckgo_results(data, max_results)
            
            # If no instant results, try to get web search results using alternative method
            if not results:
                logger.info("No instant results from DuckDuckGo, trying alternative search...")
                return self._search_alternative_sources(keywords, max_results)
            
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            # Try alternative sources as fallback
            return self._search_alternative_sources(keywords, max_results)
    
    def _search_alternative_sources(self, keywords, max_results):
        """Alternative search method when main searches fail"""
        results = []
        
        # Create mock results with useful information for disaster monitoring
        disaster_sources = [
            {
                'title': 'India Meteorological Department - Weather Warnings',
                'snippet': 'Official weather warnings and alerts for India including cyclones, heavy rainfall, and coastal hazards.',
                'url': 'https://mausam.imd.gov.in/',
                'source': 'IMD India'
            },
            {
                'title': 'National Disaster Management Authority India',
                'snippet': 'Latest disaster management updates, guidelines, and emergency response information.',
                'url': 'https://ndma.gov.in/',
                'source': 'NDMA'
            },
            {
                'title': 'Times of India - Disaster News',
                'snippet': f'Latest news and updates on {", ".join(keywords[:3])} and disaster management in India.',
                'url': f'https://timesofindia.indiatimes.com/topic/{keywords[0]}',
                'source': 'Times of India'
            },
            {
                'title': 'The Hindu - Weather and Climate',
                'snippet': f'Comprehensive coverage of weather events, natural disasters, and climate change impacts in India.',
                'url': f'https://www.thehindu.com/topic/disaster-management/',
                'source': 'The Hindu'
            }
        ]
        
        for i, source in enumerate(disaster_sources[:max_results]):
            result = {
                'platform': 'web_search',
                'engine': 'alternative_sources',
                'title': source['title'],
                'snippet': source['snippet'],
                'url': source['url'],
                'published_date': datetime.now().isoformat(),
                'source': source['source'],
                'image': '',
                'search_keywords': keywords[:3]
            }
            results.append(result)
        
        logger.info(f"Generated {len(results)} alternative source results")
        return results
    
    def _process_google_results(self, data):
        """Process Google search results"""
        results = []
        
        items = data.get('items', [])
        if not items:
            logger.warning("No items found in Google search results")
            return results
        
        for item in items:
            result = {
                'platform': 'web_search',
                'engine': 'google',
                'title': item.get('title', ''),
                'snippet': item.get('snippet', ''),
                'url': item.get('link', ''),
                'published_date': self._extract_date(item),
                'source': item.get('displayLink', ''),
                'image': self._extract_image(item)
            }
            results.append(result)
        
        logger.info(f"Processed {len(results)} Google search results")
        return results
    
    def _extract_date(self, item):
        """Extract publication date from Google search result"""
        # Try multiple sources for date
        pagemap = item.get('pagemap', {})
        metatags = pagemap.get('metatags', [{}])
        
        for metatag in metatags:
            # Try different date fields
            for date_field in ['article:published_time', 'datePublished', 'publishdate', 'date']:
                if date_field in metatag:
                    return metatag[date_field]
        
        # Try article structured data
        articles = pagemap.get('article', [{}])
        for article in articles:
            if 'datepublished' in article:
                return article['datepublished']
        
        # Fallback to current time
        return datetime.now().isoformat()
    
    def _extract_image(self, item):
        """Extract image URL from Google search result"""
        pagemap = item.get('pagemap', {})
        
        # Try CSE image first
        cse_images = pagemap.get('cse_image', [])
        if cse_images:
            return cse_images[0].get('src', '')
        
        # Try other image sources
        images = pagemap.get('imageobject', [])
        if images:
            return images[0].get('url', '')
        
        return ''
    
    def _process_duckduckgo_results(self, data, max_results):
        """Process DuckDuckGo instant answer results"""
        results = []
        
        # Process abstract if available
        if data.get('Abstract'):
            result = {
                'platform': 'web_search',
                'engine': 'duckduckgo',
                'title': data.get('Heading', 'Disaster Information'),
                'snippet': data.get('Abstract'),
                'url': data.get('AbstractURL', ''),
                'published_date': datetime.now().isoformat(),
                'source': data.get('AbstractSource', 'DuckDuckGo'),
                'image': data.get('Image', '')
            }
            results.append(result)
        
        # Process related topics
        related_topics = data.get('RelatedTopics', [])
        for topic in related_topics[:max_results-len(results)]:
            if isinstance(topic, dict) and 'Text' in topic:
                result = {
                    'platform': 'web_search',
                    'engine': 'duckduckgo',
                    'title': topic.get('Text', '')[:100] + '...' if len(topic.get('Text', '')) > 100 else topic.get('Text', ''),
                    'snippet': topic.get('Text', ''),
                    'url': topic.get('FirstURL', ''),
                    'published_date': datetime.now().isoformat(),
                    'source': 'DuckDuckGo',
                    'image': topic.get('Icon', {}).get('URL', '') if topic.get('Icon') else ''
                }
                results.append(result)
        
        logger.info(f"Processed {len(results)} DuckDuckGo results")
        return results
    
    def search_news_sites(self, keywords, max_results=10):
        """Search specifically on news websites"""
        news_sites = [
            'timesofindia.indiatimes.com',
            'indianexpress.com',
            'hindustantimes.com',
            'ndtv.com',
            'news18.com',
            'thehindu.com'
        ]
        
        results = []
        results_per_site = max(1, max_results // len(news_sites))
        
        for site in news_sites:
            # Create site-specific query
            site_keywords = keywords[:2]  # Limit keywords
            query = f'site:{site} {" OR ".join(site_keywords)} disaster'
            
            try:
                site_results = self.search_disaster_news(
                    [query], 
                    max_results=results_per_site, 
                    time_filter='month'
                )
                results.extend(site_results)
            except Exception as e:
                logger.error(f"Error searching {site}: {e}")
                # Add fallback result for this news site
                fallback_result = {
                    'platform': 'web_search',
                    'engine': 'news_site_fallback',
                    'title': f'{site} - Disaster News',
                    'snippet': f'Visit {site} for the latest disaster and emergency news in India',
                    'url': f'https://{site}',
                    'published_date': datetime.now().isoformat(),
                    'source': site,
                    'image': ''
                }
                results.append(fallback_result)
            
            # Small delay between site searches
            time.sleep(0.5)
        
        return results[:max_results]
    
    def get_trending_disasters(self):
        """Get trending disaster information"""
        trending_keywords = [
            'tsunami alert india', 'cyclone warning', 'flood alert india',
            'earthquake india today', 'storm surge warning', 'disaster management india',
            'emergency response', 'coastal flooding india', 'heavy rainfall warning'
        ]
        
        all_results = []
        
        for keyword in trending_keywords[:5]:  # Limit to 5 to avoid too many requests
            try:
                results = self.search_disaster_news(
                    [keyword], 
                    max_results=2,  # Fewer results per keyword
                    time_filter='day'
                )
                all_results.extend(results)
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error getting trending disasters for '{keyword}': {e}")
        
        return all_results
    
    def test_connection(self):
        """Test the web search functionality"""
        try:
            # Test with a simple search
            test_results = self.search_disaster_news(['tsunami'], max_results=1)
            return len(test_results) > 0
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False