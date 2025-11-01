"""Helper functions for Spotify API error handling and validation."""
from typing import List, Dict, Any, Optional
import time
from functools import wraps

def validate_tracks(tracks: List[Dict]) -> List[Dict]:
    """Filter and validate track objects."""
    return [
        track for track in tracks
        if track and isinstance(track, dict) and 
        all(key in track for key in ['id', 'uri', 'name', 'artists'])
    ]

def validate_playlist(playlist: Optional[Dict]) -> bool:
    """Validate playlist object has required fields."""
    return (
        isinstance(playlist, dict) and
        all(key in playlist for key in ['id', 'name', 'tracks', 'owner'])
    )

def safe_get_tracks(sp, playlist_id: str) -> List[Dict]:
    """Safely get all tracks from a playlist with pagination."""
    tracks = []
    offset = 0
    limit = 100  # Spotify API maximum
    
    while True:
        try:
            results = sp.playlist_items(
                playlist_id,
                offset=offset,
                limit=limit,
                fields='items.track.id,items.track.uri,items.track.name,items.track.artists,total'
            )
            
            if not results or 'items' not in results:
                break
                
            # Filter out None or invalid tracks
            valid_tracks = [
                item['track'] for item in results['items']
                if item and 'track' in item and item['track']
            ]
            tracks.extend(valid_tracks)
            
            if len(results['items']) < limit:
                break
                
            offset += limit
            time.sleep(1)  # Rate limiting
            
        except Exception as e:
            print(f"Error fetching tracks at offset {offset}: {str(e)}")
            break
    
    return validate_tracks(tracks)

def safe_get_artist_info(sp, artist_id: str) -> Dict:
    """Safely get artist information with retries."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            artist = sp.artist(artist_id)
            if artist and isinstance(artist, dict):
                return artist
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Error getting artist info: {str(e)}")
            else:
                time.sleep(1 * (attempt + 1))
    return {'name': 'Unknown', 'genres': [], 'id': artist_id}

def safe_get_recommendations(sp, seed_tracks: List[str],
                           seed_artists: List[str],
                           seed_genres: List[str],
                           limit: int = 20) -> List[Dict]:
    """Safely get recommendations with fallback strategies."""
    try:
        # Ensure we have valid seeds (Spotify requires at least one)
        if not any([seed_tracks, seed_artists, seed_genres]):
            return []
            
        # Limit seeds to Spotify API maximums
        params = {
            'limit': min(limit, 100)  # Spotify maximum
        }
        
        if seed_tracks:
            params['seed_tracks'] = ','.join(seed_tracks[:5])
        if seed_artists:
            params['seed_artists'] = ','.join(seed_artists[:5])
        if seed_genres:
            params['seed_genres'] = ','.join(seed_genres[:5])
            
        recommendations = sp.recommendations(**params)
        if recommendations and 'tracks' in recommendations:
            return validate_tracks(recommendations['tracks'])
            
    except Exception as e:
        print(f"Error getting recommendations: {str(e)}")
        
        # Try alternate approach with fewer seeds
        try:
            if seed_tracks:
                return sp.recommendations(seed_tracks=[seed_tracks[0]], limit=limit)['tracks']
            elif seed_artists:
                return sp.recommendations(seed_artists=[seed_artists[0]], limit=limit)['tracks']
            elif seed_genres:
                return sp.recommendations(seed_genres=[seed_genres[0]], limit=limit)['tracks']
        except Exception:
            pass
            
    return []

def safe_api_call(func):
    """Decorator for safe Spotify API calls with retries."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)
                if result is not None:
                    return result
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                    
        print(f"API call failed after {max_retries} attempts: {str(last_error)}")
        return None
        
    return wrapper