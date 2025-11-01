import utils
import pandas as pd
from datetime import datetime
import time
from collections import Counter

def get_playlist_id(user_input):
    """Extract playlist ID from various input formats"""
    if 'open.spotify.com' in user_input:
        return user_input.split('playlist/')[-1].split('?')[0].strip()
    elif 'spotify:playlist:' in user_input:
        return user_input.split(':')[-1].strip()
    else:
        return user_input.strip()

def analyze_game_soundtrack_playlist(playlist_url):
    """Analyze a video game soundtrack playlist with special handling for OST metadata"""
    try:
        # Initialize Spotify client with necessary permissions
        sp = utils.init_spotify_client(scope='playlist-read-private playlist-read-collaborative user-library-read')
        
        # Get playlist ID and info
        playlist_id = get_playlist_id(playlist_url)
        playlist_info = sp.playlist(playlist_id)
        
        print(f"\nAnalyzing playlist: {playlist_info['name']}")
        print(f"Created by: {playlist_info['owner']['display_name']}")
        print(f"Total tracks: {playlist_info['tracks']['total']}")
        
        # Get all tracks
        tracks = playlist_info['tracks']['items']
        tracks_data = []
        
        print("\nGathering track information...")
        for idx, item in enumerate(tracks, 1):
            if not item['track']:
                continue
                
            track = item['track']
            print(f"\rProcessing track {idx}/{len(tracks)}: {track['name']}")
            
            # Get basic track info
            track_data = {
                'track_name': track['name'],
                'duration_ms': track.get('duration_ms', 0),
                'popularity': track.get('popularity', 0),
                'preview_url': track.get('preview_url'),
                'explicit': track.get('explicit', False)
            }
            
            # Get artist info safely
            if track.get('artists'):
                track_data.update({
                    'artist_name': track['artists'][0]['name'],
                    'artist_id': track['artists'][0]['id']
                })
                try:
                    artist_info = sp.artist(track['artists'][0]['id'])
                    track_data.update({
                        'artist_genres': artist_info.get('genres', []),
                        'artist_popularity': artist_info.get('popularity', 0),
                        'artist_followers': artist_info.get('followers', {}).get('total', 0)
                    })
                except:
                    track_data.update({
                        'artist_genres': [],
                        'artist_popularity': 0,
                        'artist_followers': 0
                    })
            
            # Get album info safely
            if track.get('album'):
                track_data.update({
                    'album_name': track['album']['name'],
                    'album_type': track['album'].get('album_type', 'unknown'),
                    'release_date': track['album'].get('release_date', 'Unknown'),
                    'release_year': track['album'].get('release_date', 'Unknown')[:4] if track['album'].get('release_date') else 'Unknown'
                })
            
            tracks_data.append(track_data)
            time.sleep(0.5)  # Rate limiting
        
        # Convert to DataFrame
        df = pd.DataFrame(tracks_data)
        
        # Generate report
        print("\n=== Soundtrack Analysis Report ===")
        print(f"\nTotal Tracks Analyzed: {len(df)}")
        
        if 'artist_name' in df.columns:
            print("\nComposers/Artists:")
            print(df['artist_name'].value_counts().head())
        
        if 'album_name' in df.columns:
            print("\nFeatured Albums/Collections:")
            print(df['album_name'].value_counts().head())
        
        if 'release_year' in df.columns and df['release_year'].iloc[0] != 'Unknown':
            print("\nRelease Years Distribution:")
            print(df['release_year'].value_counts().sort_index())
        
        if 'duration_ms' in df.columns:
            avg_duration = df['duration_ms'].mean() / 1000  # Convert to seconds
            print(f"\nAverage Track Duration: {avg_duration:.1f} seconds")
        
        if 'popularity' in df.columns:
            print(f"Average Track Popularity: {df['popularity'].mean():.1f}")
        
        if 'artist_genres' in df.columns:
            all_genres = [genre for genres in df['artist_genres'] for genre in genres]
            if all_genres:
                print("\nMost Common Genres:")
                for genre, count in Counter(all_genres).most_common(5):
                    print(f"{genre}: {count} tracks")
        
        # Save detailed analysis
        output_file = f"soundtrack_analysis_{playlist_id}.csv"
        df.to_csv(output_file, index=False)
        print(f"\nDetailed analysis saved to {output_file}")
        
        return df
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        return None

if __name__ == "__main__":
    print("Welcome to the Game Soundtrack Playlist Analyzer!")
    print("This tool is specially designed for analyzing video game music playlists.")
    
    playlist_url = "https://open.spotify.com/playlist/5ZYTwF03e0JemR3IfkjkVd"  # Xenoblade Battle playlist
    analyze_game_soundtrack_playlist(playlist_url)