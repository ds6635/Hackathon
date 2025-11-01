"""Helper module for managing multiple music metadata sources."""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional, Tuple
import time
import re
from urllib.parse import quote_plus
from retry_utils import retry_with_backoff

# Define common exceptions that should trigger retries
RETRY_EXCEPTIONS = (
    requests.exceptions.RequestException,  # Base exception for all requests errors
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.HTTPError,
    ConnectionResetError
)

class MusicbrainzClient:
    """Simple client for querying MusicBrainz API."""
    
    def __init__(self, app_name: str = "MusicEnricher/1.0"):
        """Initialize with app name for user agent."""
        self.base_url = "https://musicbrainz.org/ws/2"
        self.user_agent = app_name
        
    @retry_with_backoff(retries=3, backoff_in_seconds=1.0, exceptions=RETRY_EXCEPTIONS)
    def search_release(self,
                      title: str,
                      artist: Optional[str] = None,
                      limit: int = 5) -> List[Dict]:
        """Search for releases matching the title and artist."""
        query_parts = [f'release:"{title}"']
        if artist:
            query_parts.append(f'artist:"{artist}"')
        
        query = quote_plus(' AND '.join(query_parts))
        url = f"{self.base_url}/release/?query={query}&fmt=json&limit={limit}"
        
        response = requests.get(url, headers={'User-Agent': self.user_agent})
        response.raise_for_status()  # Raise exception for bad status codes
        data = response.json()
        return data.get('releases', [])
    
    @retry_with_backoff(retries=3, backoff_in_seconds=1.0, exceptions=RETRY_EXCEPTIONS)
    def search_recording(self,
                        title: str,
                        artist: Optional[str] = None,
                        limit: int = 5) -> List[Dict]:
        """Search for recordings matching the title and artist."""
        query_parts = [f'recording:"{title}"']
        if artist:
            query_parts.append(f'artist:"{artist}"')
            
        query = quote_plus(' AND '.join(query_parts))
        url = f"{self.base_url}/recording/?query={query}&fmt=json&limit={limit}"
        
        response = requests.get(url, headers={'User-Agent': self.user_agent})
        response.raise_for_status()  # Raise exception for bad status codes
        data = response.json()
        return data.get('recordings', [])
    
    @retry_with_backoff(retries=3, backoff_in_seconds=1.0, exceptions=RETRY_EXCEPTIONS)
    def get_artist_tags(self, artist_id: str) -> List[str]:
        """Get tags associated with an artist."""
        url = f"{self.base_url}/artist/{artist_id}?inc=tags&fmt=json"
        
        response = requests.get(url, headers={'User-Agent': self.user_agent})
        response.raise_for_status()  # Raise exception for bad status codes
        data = response.json()
        return [tag['name'] for tag in data.get('tags', [])]

class AllMusicScraper:
    """Scraper for AllMusic metadata. Use as last resort."""
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        return ' '.join(text.split()).lower()
    
    @retry_with_backoff(retries=3, backoff_in_seconds=1.0, exceptions=RETRY_EXCEPTIONS)
    def search(self,
              title: str,
              artist: Optional[str] = None) -> Tuple[List[str], List[str]]:
        """Search AllMusic for genre/style information."""
        try:
            # Build search query
            query = title
            if artist:
                query = f"{artist} {title}"
            search_url = f"https://www.allmusic.com/search/all/{quote_plus(query)}"
            
            # Get search results page
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()  # Raise exception for bad status codes
                
            # Parse results
            soup = BeautifulSoup(response.text, 'html.parser')
            result_link = None
            
            # Look for most relevant result
            for result in soup.select('.search-result'):
                # Prioritize exact matches by title and artist
                result_text = self._clean_text(result.get_text())
                search_text = self._clean_text(query)
                
                if result_text and search_text in result_text:
                    result_link = result.find('a', href=True)
                    if result_link:
                        break
            
            if not result_link:
                return [], []
                
            # Get details page
            details_url = result_link['href']
            response = requests.get(details_url, headers=headers)
            if response.status_code != 200:
                return [], []
                
            # Parse genres and styles
            soup = BeautifulSoup(response.text, 'html.parser')
            genres = []
            styles = []
            
            # Extract genre information
            genre_section = soup.find('div', {'class': 'genre'})
            if genre_section:
                for link in genre_section.find_all('a'):
                    text = link.get_text().strip()
                    if text:
                        genres.append(text)
            
            # Extract style information
            style_section = soup.find('div', {'class': 'styles'})
            if style_section:
                for link in style_section.find_all('a'):
                    text = link.get_text().strip()
                    if text:
                        styles.append(text)
                        
            return genres, styles
            
        except Exception as e:
            print(f"AllMusic scraping error: {str(e)}")
            return [], []

def get_metadata_from_sources(track_name: str,
                            artist_name: str,
                            album_name: Optional[str] = None) -> Tuple[List[str], List[str]]:
    """Try multiple sources to get genre/style information.
    
    Args:
        track_name: Name of the track
        artist_name: Name of the artist/band
        album_name: Optional album name
        
    Returns:
        Tuple of (genres list, styles list)
    """
    # Try MusicBrainz first
    mb = MusicbrainzClient()
    genres = []
    styles = []
    
    try:
        # Try album search first if we have an album name
        if album_name:
            releases = mb.search_release(album_name, artist_name)
            if releases:
                # Get artist tags from the first matching release
                release = releases[0]
                if 'artist-credit' in release:
                    artist_id = release['artist-credit'][0]['artist']['id']
                    genres = mb.get_artist_tags(artist_id)
        
        # If no results, try searching by track
        if not genres:
            recordings = mb.search_recording(track_name, artist_name)
            if recordings:
                recording = recordings[0]
                if 'artist-credit' in recording:
                    artist_id = recording['artist-credit'][0]['artist']['id']
                    genres = mb.get_artist_tags(artist_id)
        
        # Sleep to respect rate limits
        time.sleep(1.0)
        
    except Exception as e:
        print(f"MusicBrainz error: {str(e)}")
    
    # If MusicBrainz fails, try AllMusic as last resort
    if not genres and not styles:
        try:
            am = AllMusicScraper()
            genres, styles = am.search(track_name, artist_name)
        except Exception as e:
            print(f"AllMusic error: {str(e)}")
    
    return genres, styles