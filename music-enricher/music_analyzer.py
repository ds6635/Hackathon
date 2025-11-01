import utils
import pandas as pd
from datetime import datetime
import time
from typing import List, Dict, Any, Optional
from collections import Counter

class MusicAnalyzer:
    def __init__(self):
        """Initialize Spotify and Discogs clients"""
        # Initialize with scopes for private playlist access
        self.sp = utils.init_spotify_client(scope='playlist-read-private playlist-read-collaborative user-library-read')
        self.discogs = utils.init_discogs_client()
        
    def verify_playlist_access(self, playlist_url):
        """Verify access to a playlist and return its details"""
        try:
            playlist_id = playlist_url.split('playlist/')[-1].split('?')[0].strip()
            playlist = self.sp.playlist(playlist_id)
            print(f"\nSuccessfully accessed playlist:")
            print(f"Name: {playlist['name']}")
            print(f"Owner: {playlist['owner']['display_name']}")
            print(f"Total tracks: {playlist['tracks']['total']}")
            return True
        except Exception as e:
            print(f"\nError accessing playlist: {str(e)}")
            return False
        
    def get_detailed_track_info(self, track_id: str) -> Dict[str, Any]:
        """Get detailed information about a single track"""
        track = self.sp.track(track_id)
        artist_info = self.sp.artist(track['artists'][0]['id'])
        album = self.sp.album(track['album']['id'])
        
        # Get Discogs details for more accurate genre information
        discogs_info = self._search_discogs(
            track['name'],
            track['artists'][0]['name'],
            track['album']['name']
        )
        
        return {
            'track_name': track['name'],
            'artist_name': track['artists'][0]['name'],
            'album_name': track['album']['name'],
            'release_date': track['album']['release_date'],
            'album_release_year': track['album']['release_date'][:4],
            'spotify_popularity': track['popularity'],
            'spotify_genres': artist_info['genres'],
            'artist_followers': artist_info['followers']['total'],
            'discogs_genres': discogs_info.get('genres', []),
            'discogs_styles': discogs_info.get('styles', []),
            'all_genres': list(set(artist_info['genres'] + discogs_info.get('genres', []))),
            'is_artist_active': self._check_if_artist_active(artist_info['id']),
            'album_position': self._get_album_chronological_position(album),
            'track_number': track['track_number'],
            'preview_url': track['preview_url']
        }

    def analyze_playlist(self, playlist_url: str) -> pd.DataFrame:
        """Analyze an entire playlist and return detailed information"""
        # Extract playlist ID and remove any query parameters
        playlist_id = playlist_url.split('playlist/')[-1].split('?')[0].strip()
        results = self.sp.playlist_tracks(playlist_id)
        tracks_data = []
        
        print(f"Analyzing playlist tracks...")
        for idx, item in enumerate(results['items']):
            if item['track']:
                print(f"Processing track {idx + 1}/{len(results['items'])}: {item['track']['name']}")
                track_data = self.get_detailed_track_info(item['track']['id'])
                tracks_data.append(track_data)
                time.sleep(1.0)  # Respect API rate limits
        
        return pd.DataFrame(tracks_data)

    def recommend_playlist_changes(self, playlist_url: str) -> Dict[str, List[str]]:
        """Analyze playlist and recommend songs to remove based on various factors"""
        df = self.analyze_playlist(playlist_url)
        
        recommendations = {
            'duplicate_artists': [],
            'low_popularity': [],
            'genre_outliers': [],
            'very_old': []
        }
        
        # Find duplicate artists
        artist_counts = df['artist_name'].value_counts()
        for artist, count in artist_counts.items():
            if count > 2:
                dupes = df[df['artist_name'] == artist]['track_name'].tolist()[2:]
                recommendations['duplicate_artists'].extend(dupes)
        
        # Find low popularity tracks
        low_pop = df[df['spotify_popularity'] < 20]['track_name'].tolist()
        recommendations['low_popularity'].extend(low_pop)
        
        # Find genre outliers
        all_genres = [g for genres in df['all_genres'] for g in genres]
        common_genres = set([g for g, c in Counter(all_genres).items() if c > len(df) * 0.2])
        
        for idx, row in df.iterrows():
            if not any(g in common_genres for g in row['all_genres']):
                recommendations['genre_outliers'].append(row['track_name'])
        
        return recommendations

    def merge_playlists(self, source_playlist_url: str, target_playlist_url: str) -> List[str]:
        """Merge source playlist into target playlist"""
        source_id = source_playlist_url.split('/')[-1].split('?')[0]
        target_id = target_playlist_url.split('/')[-1].split('?')[0]
        
        # Get source playlist tracks
        source_tracks = self.sp.playlist_tracks(source_id)
        track_uris = [item['track']['uri'] for item in source_tracks['items'] if item['track']]
        
        # Add to target playlist in batches of 100 (Spotify API limit)
        added_tracks = []
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i:i + 100]
            self.sp.playlist_add_items(target_id, batch)
            added_tracks.extend([uri.split(':')[-1] for uri in batch])
            
        return added_tracks

    def _search_discogs(self, track_name: str, artist_name: str, album_name: str) -> Dict[str, List[str]]:
        """Search Discogs for detailed genre information"""
        try:
            results = self.discogs.search(
                album_name,
                artist=artist_name,
                type='release'
            )
            
            if results and results.page(1):
                release = results.page(1)[0]
                full_release = self.discogs.release(release.id)
                return {
                    'genres': full_release.genres if hasattr(full_release, 'genres') else [],
                    'styles': full_release.styles if hasattr(full_release, 'styles') else []
                }
            return {'genres': [], 'styles': []}
            
        except Exception as e:
            print(f"Discogs search error: {str(e)}")
            return {'genres': [], 'styles': []}

    def _check_if_artist_active(self, artist_id: str) -> bool:
        """Check if artist is still active based on recent releases"""
        try:
            albums = self.sp.artist_albums(artist_id, limit=5)
            if not albums['items']:
                return False
            
            latest_album_date = datetime.strptime(albums['items'][0]['release_date'], '%Y-%m-%d')
            two_years_ago = datetime.now().replace(year=datetime.now().year - 2)
            
            return latest_album_date > two_years_ago
            
        except Exception:
            return False

    def _get_album_chronological_position(self, album: Dict[str, Any]) -> Optional[int]:
        """Get the chronological position of an album in artist's discography"""
        try:
            artist_id = album['artists'][0]['id']
            all_albums = self.sp.artist_albums(artist_id, album_type='album')
            
            # Sort albums by release date
            sorted_albums = sorted(
                all_albums['items'],
                key=lambda x: x['release_date']
            )
            
            # Find position of current album
            for idx, a in enumerate(sorted_albums, 1):
                if a['id'] == album['id']:
                    return idx
                    
            return None
            
        except Exception:
            return None

def analyze_playlist_usage():
    """Example usage of the MusicAnalyzer class"""
    analyzer = MusicAnalyzer()
    
    # The Bubbly Pink-Haired BFF playlist
    playlist_url = "https://open.spotify.com/playlist/37i9dQZF1DX80RcWXnI2CZ?si=f33fb1a4b5ea4c6e"
    
    print("1. Getting detailed playlist analysis...")
    df = analyzer.analyze_playlist(playlist_url)
    
    print("\n2. Basic Statistics:")
    print(f"Total tracks: {len(df)}")
    print(f"Unique artists: {df['artist_name'].nunique()}")
    print(f"Average track popularity: {df['spotify_popularity'].mean():.2f}")
    
    print("\n3. Genre Distribution:")
    all_genres = [g for genres in df['all_genres'] for g in genres]
    genre_counts = Counter(all_genres).most_common(10)
    for genre, count in genre_counts:
        print(f"{genre}: {count} tracks")
    
    print("\n4. Recommendations for playlist improvement:")
    recommendations = analyzer.recommend_playlist_changes(playlist_url)
    for category, tracks in recommendations.items():
        if tracks:
            print(f"\n{category.replace('_', ' ').title()}:")
            for track in tracks[:5]:  # Show top 5 recommendations
                print(f"- {track}")

if __name__ == "__main__":
    analyze_playlist_usage()