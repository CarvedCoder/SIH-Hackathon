from fastapi import APIRouter
import re
from typing import List, Dict, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import asyncio
from collections import Counter
try:
    from langdetect import detect as _ld_detect
except Exception:
    _ld_detect = None
from collections import Counter


def detect_language(text: str) -> str:
    """Detect language of `text` with a safe fallback.

    Tries langdetect if available; on error or short/empty text falls back to simple heuristics
    and ultimately returns 'en' as the default.
    """
    if not text:
        return 'en'
    if _ld_detect:
        try:
            return _ld_detect(text)
        except Exception:
            pass

    # very small heuristic fallbacks for a few Indic scripts/words
    tl = text.lower()
    # Devanagari (hi) quick check
    if any(ch in text for ch in 'ऀॿ'):
        return 'hi'
    # common Hindi words
    if any(word in tl for word in ['है', 'और', 'तूफान', 'बाढ़', 'सुनामी', 'समुद्री']):
        return 'hi'
    # Tamil (very rough)
    if any(ch in text for ch in '஀௿'):
        return 'ta'
    # Malayalam
    if any(ch in text for ch in 'ഀൿ'):
        return 'ml'

    # default
    return 'en'
from concurrent.futures import ThreadPoolExecutor

router = APIRouter()

@dataclass
class HazardAlert:
    hazard_type: str
    confidence: float
    urgency_level: str  # low, medium, high, critical
    location_mentions: List[str]
    sentiment_score: float
    affected_areas: List[str]
    key_phrases: List[str]


class AdvancedHazardNLP:
    """NLP analyzer with lazy-loading of heavy ML libraries.

    This avoids importing torch / sentence-transformers / pyarrow at module import time,
    which prevents uvicorn from crashing when those native libs are incompatible or
    not installed in the environment.
    """

    def __init__(self):
        # placeholders for heavy objects (populated by load_models)
        self.sentiment_analyzer = None
        self.tokenizer = None
        self.classifier = None
        self.sentence_model = None
        self.nlp = None
        self.translator = None

        # light-weight data that can be initialized eagerly
        self.hazard_patterns = self._initialize_hazard_patterns()
        self.coastal_locations = self._load_coastal_locations()
        self.urgency_indicators = {
            'critical': ['emergency', 'urgent', 'immediate', 'critical', 'danger', 'evacuate', 'warning', 'alert', 'sos', 'help'],
            'high': ['severe', 'major', 'significant', 'rapidly', 'quickly', 'rising'],
            'medium': ['moderate', 'increasing', 'developing', 'expected', 'possible'],
            'low': ['minor', 'small', 'light', 'minimal', 'slight']
        }

        self.executor = ThreadPoolExecutor(max_workers=4)
        self.models_loaded = False

    def load_models(self):
        """Synchronous model loading. Call in a background thread (not on the event loop).

        This imports heavy libraries and initializes model objects.
        """
        if self.models_loaded:
            return

        # Import heavy dependencies here (deferred)
        # Any ImportError here will be raised inside the executor/thread instead of at module import time
        from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
        from sentence_transformers import SentenceTransformer
        import spacy
        from googletrans import Translator

        # Initialize models (these calls may take time and RAM)
        self.sentiment_analyzer = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment")
        self.tokenizer = AutoTokenizer.from_pretrained("bert-base-multilingual-cased")
        self.classifier = AutoModelForSequenceClassification.from_pretrained("bert-base-multilingual-cased", num_labels=8)
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.nlp = spacy.load("en_core_web_sm")
        self.translator = Translator()

        self.models_loaded = True

    async def ensure_models_loaded(self):
        """Async-friendly wrapper to ensure models are loaded.

        Loads models in a thread pool so the event loop is not blocked.
        """
        if not self.models_loaded:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.load_models)

    def _initialize_hazard_patterns(self) -> Dict:
        return {
            'tsunami': {
                'en': r'(tsunami|tidal wave|seismic sea wave|harbor wave)',
                'hi': r'(सुनामी|समुद्री लहर|ज्वार की लहर)',
                'ta': r'(சுனாமி|கடல் அலை)',
                'ml': r'(സുനാമി|കടൽ തിരമാല)'
            },
            'cyclone': {
                'en': r'(cyclone|hurricane|typhoon|storm|tempest)',
                'hi': r'(चक्रवात|तूफान|आंधी)',
                'ta': r'(புயல்|சூறாவளி)',
                'ml': r'(ചുഴലിക്കാറ്റ്|കൊടുങ്ങാറ്റ്)'
            },
            'flood': {
                'en': r'(flood|flooding|inundation|deluge|submerg|overflow)',
                'hi': r'(बाढ़|जलप्रलय|सैलाब)',
                'ta': r'(வெள்ளம்|பெருவெள்ளம்)',
                'ml': r'(വെള്ളപ്പൊക്കം|പ്രളയം)'
            },
            'storm_surge': {
                'en': r'(storm surge|coastal flood|high tide|tidal surge)',
                'hi': r'(तूफानी लहर|उच्च ज्वार)',
                'ta': r'(புயல் எழுச்சி)',
                'ml': r'(കൊടുങ്കാറ്റ് തിരമാല)'
            }
        }

    def _load_coastal_locations(self) -> Dict:
        return {
            'major_cities': [
                'Mumbai', 'Chennai', 'Kolkata', 'Kochi', 'Visakhapatnam', 'Thiruvananthapuram', 'Mangalore', 'Puri', 'Goa', 'Surat', 'Pondicherry', 'Paradip', 'Kandla', 'Tuticorin', 'Calicut'
            ],
            'states': [
                'Gujarat', 'Maharashtra', 'Goa', 'Karnataka', 'Kerala', 'Tamil Nadu', 'Andhra Pradesh', 'Odisha', 'West Bengal', 'Andaman and Nicobar', 'Lakshadweep'
            ],
            'regions': ['Konkan', 'Malabar', 'Coromandel', 'Sundarbans']
        }

    async def analyze_social_media_post(self, text: str, platform: str, metadata: Dict = None) -> HazardAlert:
        # Ensure heavy models are loaded before any model operations
        await self.ensure_models_loaded()

        # Detect language
        try:
            language = detect_language(text)
        except Exception:
            language = 'en'

        # Translate if not English
        if language != 'en':
            translated_text = self.translator.translate(text, dest='en').text
        else:
            translated_text = text

        # Parallel processing of different analyses
        tasks = [
            self._detect_hazard_type(translated_text, language),
            self._calculate_urgency(translated_text),
            self._extract_locations(translated_text),
            self._analyze_sentiment(translated_text),
            self._extract_key_phrases(translated_text)
        ]

        results = await asyncio.gather(*tasks)

        hazard_type, confidence = results[0]
        urgency_level = results[1]
        locations = results[2]
        sentiment = results[3]
        key_phrases = results[4]

        affected_areas = self._identify_affected_areas(locations, translated_text)

        return HazardAlert(
            hazard_type=hazard_type,
            confidence=confidence,
            urgency_level=urgency_level,
            location_mentions=locations,
            sentiment_score=sentiment,
            affected_areas=affected_areas,
            key_phrases=key_phrases
        )

    async def _detect_hazard_type(self, text: str, language: str) -> Tuple[str, float]:
        # assumes models are loaded
        pattern_scores = {}
        for hazard, patterns in self.hazard_patterns.items():
            score = 0
            for lang, pattern in patterns.items():
                if re.search(pattern, text, re.IGNORECASE):
                    score += 1
            pattern_scores[hazard] = score

        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        import torch
        with torch.no_grad():
            outputs = self.classifier(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)

        hazard_types = ['tsunami', 'cyclone', 'flood', 'storm_surge', 'high_waves', 'coastal_erosion', 'rip_current', 'other']

        ml_scores = predictions[0].cpu().numpy()
        combined_scores = {}

        for i, hazard in enumerate(hazard_types):
            pattern_weight = pattern_scores.get(hazard, 0) * 0.3
            ml_weight = ml_scores[i] * 0.7
            combined_scores[hazard] = pattern_weight + ml_weight

        best_hazard = max(combined_scores, key=combined_scores.get)
        confidence = combined_scores[best_hazard]

        return best_hazard, float(confidence)

    async def _calculate_urgency(self, text: str) -> str:
        text_lower = text.lower()

        urgency_scores = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}

        for level, indicators in self.urgency_indicators.items():
            for indicator in indicators:
                if indicator in text_lower:
                    urgency_scores[level] += 1

        if any(word in text_lower for word in ['now', 'immediate', 'current', 'happening']):
            urgency_scores['critical'] += 2
        elif any(word in text_lower for word in ['soon', 'coming', 'approaching']):
            urgency_scores['high'] += 1
        elif any(word in text_lower for word in ['expected', 'predicted', 'forecast']):
            urgency_scores['medium'] += 1

        return max(urgency_scores, key=urgency_scores.get)

    async def _extract_locations(self, text: str) -> List[str]:
        doc = self.nlp(text)
        locations = []

        for ent in doc.ents:
            if ent.label_ in ['GPE', 'LOC']:
                locations.append(ent.text)

        text_lower = text.lower()
        for city in self.coastal_locations['major_cities']:
            if city.lower() in text_lower and city not in locations:
                locations.append(city)

        for state in self.coastal_locations['states']:
            if state.lower() in text_lower and state not in locations:
                locations.append(state)

        return locations

    async def _analyze_sentiment(self, text: str) -> float:
        result = self.sentiment_analyzer(text)[0]
        label = result['label'].upper()
        score = result['score']

        if 'POS' in label:
            return score * 0.5
        elif 'NEG' in label:
            return -score * 0.5
        else:
            return 0.0

    async def _extract_key_phrases(self, text: str) -> List[str]:
        doc = self.nlp(text)
        noun_phrases = [chunk.text for chunk in doc.noun_chunks]

        relevant_phrases = []
        hazard_keywords = ['water', 'wave', 'wind', 'storm', 'flood', 'damage', 'evacuat', 'rescue', 'alert', 'warning', 'rise', 'surge']

        for phrase in noun_phrases:
            if any(keyword in phrase.lower() for keyword in hazard_keywords):
                relevant_phrases.append(phrase)

        return relevant_phrases[:5]

    def _identify_affected_areas(self, locations: List[str], text: str) -> List[str]:
        affected = []
        context_words = ['hit', 'affect', 'impact', 'strike', 'approach', 'near', 'towards']

        for location in locations:
            for context in context_words:
                pattern = f"{context}.*{location}|{location}.*{context}"
                if re.search(pattern, text, re.IGNORECASE):
                    affected.append(location)
                    break

        return affected

class SocialMediaStreamAnalyzer:
    def __init__(self, nlp_analyzer: AdvancedHazardNLP):
        self.nlp_analyzer = nlp_analyzer
        self.alert_threshold = 0.7
        self.trend_window = []
        self.location_clusters = {}
        self.trend_window_hours = 6
        self.max_window_size = 1000

    async def process_stream(self, posts: List[Dict]) -> Dict:
        # Clean old alerts from trend window
        current_time = datetime.now()
        self.trend_window = [
            alert for alert in self.trend_window
            if (current_time - datetime.fromisoformat(alert['timestamp'])).total_seconds() < self.trend_window_hours * 3600
        ]

        alerts = []
        high_priority_alerts = []

        for post in posts:
            alert = await self.nlp_analyzer.analyze_social_media_post(
                post.get('text', ''),
                post.get('platform', 'unknown'),
                post.get('metadata', {})
            )

            # Convert dataclass to dict for JSON serialization
            alert_dict_obj = asdict(alert)

            if alert.confidence >= self.alert_threshold:
                alert_dict = {
                    'post_id': post.get('id'),
                    'platform': post.get('platform', 'unknown'),
                    'timestamp': post.get('timestamp', datetime.now().isoformat()),
                    'alert': alert_dict_obj
                }
                alerts.append(alert_dict)

                if alert.urgency_level in ['critical', 'high']:
                    high_priority_alerts.append(alert_dict)

                # Add to trend window
                self.trend_window.append(alert_dict)

                # Keep trend window size under control
                if len(self.trend_window) > self.max_window_size:
                    self.trend_window = self.trend_window[-self.max_window_size:]

        trends = self._detect_trends(alerts)
        location_clusters = self._cluster_by_location(alerts)

        return {
            'total_posts_analyzed': len(posts),
            'alerts_generated': len(alerts),
            'high_priority_alerts': high_priority_alerts,
            'trending_hazards': trends,
            'location_clusters': location_clusters,
            'analysis_timestamp': datetime.now().isoformat()
        }

    def _detect_trends(self, alerts: List[Dict]) -> List[Dict]:
        if not alerts:
            return []

        hazard_counts = Counter([a['alert']['hazard_type'] for a in alerts])

        area_counts = Counter()
        for alert in alerts:
            area_counts.update(alert['alert'].get('affected_areas', []))

        trends = []
        for hazard, count in hazard_counts.most_common(3):
            if count >= 2:
                trends.append({
                    'hazard_type': hazard,
                    'mention_count': count,
                    'percentage': (count / len(alerts)) * 100,
                    'top_affected_areas': [area for area, _ in area_counts.most_common(3)]
                })

        return trends

    def _cluster_by_location(self, alerts: List[Dict]) -> Dict:
        location_groups = {}

        for alert in alerts:
            for location in alert['alert'].get('location_mentions', []):
                if location not in location_groups:
                    location_groups[location] = {
                        'location': location,
                        'alerts': [],
                        'hazard_types': set(),
                        'max_urgency': 'low'
                    }

                location_groups[location]['alerts'].append(alert['post_id'])
                location_groups[location]['hazard_types'].add(alert['alert'].get('hazard_type'))

                # Update max urgency
                urgency_levels = ['low', 'medium', 'high', 'critical']
                current_urgency = alert['alert'].get('urgency_level', 'low')
                max_urgency = location_groups[location]['max_urgency']
                if urgency_levels.index(current_urgency) > urgency_levels.index(max_urgency):
                    location_groups[location]['max_urgency'] = current_urgency

        # Convert sets to lists for JSON serialization
        for location in location_groups:
            location_groups[location]['hazard_types'] = list(location_groups[location]['hazard_types'])

        return location_groups
# Initialize analyzer instances to be reused
nlp_analyzer = AdvancedHazardNLP()
stream_analyzer = SocialMediaStreamAnalyzer(nlp_analyzer)


@router.post("/api/analyze/social-media")
async def analyze_social_media_batch(posts: List[Dict]):
    """Analyze a batch of social media posts for hazard detection"""

    results = await stream_analyzer.process_stream(posts)
    return results


@router.post("/api/analyze/single-post")
async def analyze_single_post(text: str, platform: str = "unknown"):
    """Analyze a single social media post"""

    alert = await nlp_analyzer.analyze_social_media_post(text, platform)
    alert_dict = asdict(alert)

    return {
        "hazard_detected": alert_dict.get('hazard_type'),
        "confidence": alert_dict.get('confidence'),
        "urgency": alert_dict.get('urgency_level'),
        "locations": alert_dict.get('location_mentions'),
        "affected_areas": alert_dict.get('affected_areas'),
        "sentiment": alert_dict.get('sentiment_score'),
        "key_phrases": alert_dict.get('key_phrases')
    }


@router.get("/api/dashboard/trends")
async def get_trending_hazards():
    """Get trending hazards based on recent social media analysis"""
    recent_alerts = stream_analyzer.trend_window  # Get recent alerts from the analyzer

    if not recent_alerts:
        # Return sample data if no recent alerts
        return {
            "trending": [
                {
                    "hazard_type": "cyclone",
                    "trend_score": 0.85,
                    "affected_regions": ["Tamil Nadu", "Andhra Pradesh"],
                    "post_count": 145,
                    "time_window": "last_6_hours"
                }
            ]
        }

    trends = stream_analyzer._detect_trends(recent_alerts)

    # Format trends for frontend
    trending_hazards = []
    for trend in trends:
        trending_hazards.append({
            "hazard_type": trend["hazard_type"],
            "trend_score": trend["percentage"] / 100,  # Convert to 0-1 scale
            "affected_regions": trend["top_affected_areas"],
            "post_count": trend["mention_count"],
            "time_window": "last_6_hours"  # You can make this dynamic based on your data
        })

    return {"trending": trending_hazards}
