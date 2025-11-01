"""Music analyzer with advanced recommendations and playlist management."""
import utils
import pandas as pd
import time
from typing import List, Dict, Any, Optional, Set
from collections import Counter
import wikipedia
import difflib
from urllib.parse import quote_plus
import re
from discogs_search import search_discogs_release
from metadata_sources import get_metadata_from_sources
from retry_utils import retry_with_backoff
from spotify_helpers import (
    safe_get_tracks,
    safe_get_artist_info,
    safe_get_recommendations,
    safe_api_call,
    validate_tracks,
    validate_playlist
)

class EnhancedMusicAnalyzer:
    def __init__(self):
        """Initialize clients with necessary scopes for playlist modification."""
        self.sp = utils.init_spotify_client(scope='playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private')
        self.discogs = utils.init_discogs_client()
        
    def search_music(self, query: str) -> Dict[str, List[Dict]]:
        """Search for tracks, artists, and playlists matching a query."""
        results = {
            'tracks': [],
            'artists': [],
            'playlists': []
        }
        
        # Search tracks
        track_results = self.sp.search(q=query, type='track', limit=5)
        if track_results and 'tracks' in track_results:
            results['tracks'] = track_results['tracks']['items']
            
        # Search artists
        artist_results = self.sp.search(q=query, type='artist', limit=5)
        if artist_results and 'artists' in artist_results:
            results['artists'] = artist_results['artists']['items']
            
        # Search playlists
        playlist_results = self.sp.search(q=query, type='playlist', limit=5)
        if playlist_results and 'playlists' in playlist_results:
            results['playlists'] = playlist_results['playlists']['items']
            
        return results

    def get_artist_history(self, artist_name: str) -> Dict[str, Any]:
        """Get artist's history including previous bands and collaborations."""
        try:
            # Try to find the most relevant Wikipedia page
            search_results = wikipedia.search(f"{artist_name} musician", results=5)
            best_match = None
            highest_ratio = 0
            
            for result in search_results:
                ratio = difflib.SequenceMatcher(None, artist_name.lower(), result.lower()).ratio()
                if ratio > highest_ratio:
                    highest_ratio = ratio
                    best_match = result
            
            if not best_match or highest_ratio < 0.5:
                return {'previous_bands': [], 'related_artists': [], 'source': None}
            
            # Get the Wikipedia page
            wiki_page = wikipedia.page(best_match, auto_suggest=False)
            content = wiki_page.content.lower()
            
            # Extract band information
            previous_bands = set()
            member_of_patterns = [
                r"member of ([^\.]+)",
                r"performed with ([^\.]+)",
                r"played (in|with) ([^\.]+)",
                r"formed ([^\.]+)",
                r"joined ([^\.]+)"
            ]
            
            for pattern in member_of_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    band = match.group(1).strip()
                    if len(band) > 3 and 'their' not in band and 'who' not in band:
                        previous_bands.add(band.title())
            
            return {
                'previous_bands': list(previous_bands),
                'related_artists': self._get_related_artists(artist_name),
                'source': wiki_page.url
            }
            
        except Exception as e:
            print(f"Error getting artist history: {str(e)}")
            return {'previous_bands': [], 'related_artists': [], 'source': None}

    def _get_related_artists(self, artist_name: str) -> List[str]:
        """Get related artists from Spotify."""
        try:
            results = self.sp.search(q=artist_name, type='artist', limit=1)
            if results and results['artists']['items']:
                artist_id = results['artists']['items'][0]['id']
                related = self.sp.artist_related_artists(artist_id)
                return [artist['name'] for artist in related['artists']]
        except Exception:
            pass
        return []

    @safe_api_call
    def get_recommendations(self, seed_tracks: List[str], seed_artists: List[str], 
                          seed_genres: List[str], limit: int = 20) -> List[Dict]:
        """Get track recommendations based on seeds."""
        return safe_get_recommendations(
            self.sp,
            seed_tracks=seed_tracks,
            seed_artists=seed_artists,
            seed_genres=seed_genres,
            limit=limit
        )

    def create_playlist(self, name: str, description: str = "") -> Optional[str]:
        """Create a new playlist and return its ID."""
        try:
            user_id = self.sp.current_user()['id']
            playlist = self.sp.user_playlist_create(
                user=user_id,
                name=name,
                description=description,
                public=False
            )
            return playlist['id']
        except Exception as e:
            print(f"Error creating playlist: {str(e)}")
            return None

    def add_tracks_to_playlist(self, playlist_id: str, track_uris: List[str]) -> bool:
        """Add tracks to a playlist."""
        try:
            # Add tracks in batches of 100 (Spotify API limit)
            for i in range(0, len(track_uris), 100):
                batch = track_uris[i:i + 100]
                self.sp.playlist_add_items(playlist_id, batch)
            return True
        except Exception as e:
            print(f"Error adding tracks: {str(e)}")
            return False

    @safe_api_call
    def merge_playlists(self, source_ids: List[str], target_id: str) -> bool:
        """Merge multiple playlists into a target playlist."""
        try:
            all_tracks = set()
            for playlist_id in source_ids:
                tracks = safe_get_tracks(self.sp, playlist_id)
                track_uris = [track['uri'] for track in tracks 
                            if not track.get('is_local', False)]
                all_tracks.update(track_uris)
            
            return self.add_tracks_to_playlist(target_id, list(all_tracks))
        except Exception as e:
            print(f"Error merging playlists: {str(e)}")
            return False

    def suggest_playlist_name(self, seed_tracks: List[Dict]) -> str:
        """Suggest a playlist name based on track analysis."""
        try:
            # Get genres and artists
            genres = []
            artists = []
            for track in seed_tracks:
                if 'artists' in track:
                    artists.append(track['artists'][0]['name'])
                    artist_info = self.sp.artist(track['artists'][0]['id'])
                    genres.extend(artist_info.get('genres', []))
            
            # Count most common elements
            top_genre = Counter(genres).most_common(1)[0][0] if genres else ""
            top_artist = Counter(artists).most_common(1)[0][0] if artists else ""
            
            # Generate name suggestions
            suggestions = [
                f"Mix: {top_artist} & Similar Artists",
                f"Inspired by {top_genre.title()}",
                f"Your {top_genre.title()} Mix",
                f"{top_artist}'s Genre Journey",
                "Your Custom Mix"
            ]
            
            return suggestions[0]  # Return first suggestion
            
        except Exception:
            return "Your Custom Mix"

    def get_artist_top_tracks(self, artist_name: str, limit: int = 5) -> List[Dict]:
        """Get an artist's top tracks."""
        try:
            results = self.sp.search(q=artist_name, type='artist', limit=1)
            if results and results['artists']['items']:
                artist_id = results['artists']['items'][0]['id']
                top_tracks = self.sp.artist_top_tracks(artist_id)
                return top_tracks['tracks'][:limit]
        except Exception:
            pass
        return []

    @safe_api_call
    def analyze_and_recommend(self, input_query: str, recommendation_type: str = 'track') -> Dict[str, Any]:
        """Main analysis and recommendation function."""
        results = self.search_music(input_query)
        recommendations = {
            'query': input_query,
            'type': recommendation_type,
            'found_items': results,
            'recommendations': [],
            'artist_history': {},
            'suggested_playlist_names': []
        }
        
        if recommendation_type == 'track' and results['tracks']:
            # Get recommendations based on the track
            track = validate_tracks(results['tracks'])[0]
            if track:
                seed_tracks = [track['id']]
                seed_artists = [artist['id'] for artist in track['artists'][:2]]
                seed_genres = []
                
                # Get artist genres
                for artist in track['artists'][:2]:
                    artist_info = safe_get_artist_info(self.sp, artist['id'])
                    seed_genres.extend(artist_info.get('genres', [])[:2])
                
                recommendations['recommendations'] = self.get_recommendations(
                    seed_tracks=seed_tracks,
                    seed_artists=seed_artists,
                    seed_genres=seed_genres
                )
            
        elif recommendation_type == 'artist' and results['artists']:
            # Get artist's history and top tracks
            artist = results['artists'][0]
            recommendations['artist_history'] = self.get_artist_history(artist['name'])
            
            # Get recommendations based on the artist
            recommendations['recommendations'] = self.get_recommendations(
                seed_tracks=[],
                seed_artists=[artist['id']],
                seed_genres=artist.get('genres', [])[:2]
            )
            
        elif recommendation_type == 'playlist' and results['playlists']:
            # Analyze playlist and get recommendations
            playlist = results['playlists'][0]
            tracks = self.sp.playlist_tracks(playlist['id'])
            
            # Get unique artists and genres
            artists = set()
            genres = set()
            seed_tracks = []
            
            for item in tracks['items'][:5]:  # Analyze first 5 tracks
                if item['track']:
                    track = item['track']
                    if len(seed_tracks) < 2:
                        seed_tracks.append(track['id'])
                    for artist in track['artists']:
                        artists.add(artist['id'])
                        artist_info = self.sp.artist(artist['id'])
                        genres.update(artist_info.get('genres', []))
            
            recommendations['recommendations'] = self.get_recommendations(
                seed_tracks=seed_tracks,
                seed_artists=list(artists)[:2],
                seed_genres=list(genres)[:2]
            )
        
        # Suggest playlist names based on recommendations
        if recommendations['recommendations']:
            recommendations['suggested_playlist_names'] = [
                self.suggest_playlist_name(recommendations['recommendations']),
                "Your Discovery Mix",
                f"Based on: {input_query}"
            ]
        
        return recommendations