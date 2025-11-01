import utils
import pandas as pd
from datetime import datetime
import time
from collections import Counter

def get_playlist_id(user_input):
    """Extract playlist ID from various input formats"""
    if 'open.spotify.com' in user_input:
        # Handle full URLs
        return user_input.split('playlist/')[-1].split('?')[0].strip()
    elif 'spotify:playlist:' in user_input:
        # Handle Spotify URI
        return user_input.split(':')[-1].strip()
    else:
        # Assume it's already an ID
        return user_input.strip()

def get_playlist_choice():
    """Get playlist selection from user"""
    print("\nHow would you like to select a playlist?")
    print("1. List my playlists")
    print("2. Enter playlist URL/ID")
    choice = input("Enter your choice (1 or 2): ").strip()
    
    sp = utils.init_spotify_client(scope='playlist-read-private playlist-read-collaborative user-library-read')
    
    if choice == "1":
        # List user's playlists
        results = sp.current_user_playlists()
        print("\nYour playlists:")
        for idx, playlist in enumerate(results['items'], 1):
            print(f"{idx}. {playlist['name']} ({playlist['tracks']['total']} tracks)")
            print(f"   ID: {playlist['id']}")
        
        while True:
            try:
                playlist_num = int(input("\nEnter the number of the playlist you want to analyze: "))
                if 1 <= playlist_num <= len(results['items']):
                    return results['items'][playlist_num-1]['id']
                else:
                    print("Invalid number. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
    
    else:
        # Get playlist URL or ID from user
        print("\nYou can enter:")
        print("- Spotify playlist URL (https://open.spotify.com/playlist/...)")
        print("- Spotify URI (spotify:playlist:...)")
        print("- Playlist ID")
        user_input = input("Enter playlist URL or ID: ").strip()
        return get_playlist_id(user_input)

def analyze_playlist():
    try:
        # Initialize clients
        sp = utils.init_spotify_client(scope='playlist-read-private playlist-read-collaborative user-library-read')
        discogs = utils.init_discogs_client()
        
        # Get playlist choice from user
        playlist_id = get_playlist_choice()
        
        # Verify playlist access
        try:
            playlist_info = sp.playlist(playlist_id)
            print(f"\nAnalyzing playlist: {playlist_info['name']}")
            print(f"Created by: {playlist_info['owner']['display_name']}")
            print(f"Total tracks: {playlist_info['tracks']['total']}")
        except Exception as e:
            print(f"Error accessing playlist: {str(e)}")
            return
        
        print("Starting playlist analysis...")
        print("(This might take a while due to the large number of tracks)")
        
        # Get playlist tracks
        results = sp.playlist_tracks(playlist_id)
        tracks_data = []
        total_tracks = len(results['items'])
        
        for idx, item in enumerate(results['items'], 1):
            if not item['track']:
                continue
                
            track = item['track']
            print(f"\rProcessing track {idx}/{total_tracks}: {track['name']}", end='')
            
            try:
                # Get artist info
                artist_info = sp.artist(track['artists'][0]['id'])
                
                # Get album info
                album_info = sp.album(track['album']['id'])
                
                # Search Discogs
                search_results = discogs.search(
                    track['album']['name'],
                    artist=track['artists'][0]['name'],
                    type='release'
                )
                
                discogs_genres = []
                discogs_styles = []
                
                if search_results and search_results.page(1):
                    release = search_results.page(1)[0]
                    if hasattr(release, 'genres'):
                        discogs_genres = release.genres
                    if hasattr(release, 'styles'):
                        discogs_styles = release.styles
                
                track_data = {
                    'track_name': track['name'],
                    'artist_name': track['artists'][0]['name'],
                    'album_name': track['album']['name'],
                    'release_date': track['album']['release_date'],
                    'release_year': track['album']['release_date'][:4],
                    'popularity': track['popularity'],
                    'duration_ms': track['duration_ms'],
                    'spotify_genres': artist_info.get('genres', []),
                    'artist_followers': artist_info['followers']['total'],
                    'discogs_genres': discogs_genres,
                    'discogs_styles': discogs_styles,
                    'all_genres': list(set(artist_info.get('genres', []) + discogs_genres))
                }
                
                tracks_data.append(track_data)
                
            except Exception as e:
                print(f"\nError processing track {track['name']}: {str(e)}")
            
            # Rate limiting
            time.sleep(1.0)
        
        print("\n\nAnalysis complete! Generating report...")
        
        # Convert to DataFrame
        df = pd.DataFrame(tracks_data)
        
        # Generate insights
        print("\n=== Playlist Analysis Report ===")
        print(f"\nTotal Tracks: {len(df)}")
        print(f"Unique Artists: {df['artist_name'].nunique()}")
        print(f"Unique Albums: {df['album_name'].nunique()}")
        
        print("\nTop 10 Artists by Number of Tracks:")
        print(df['artist_name'].value_counts().head(10))
        
        print("\nRelease Year Distribution:")
        print(df['release_year'].value_counts().sort_index())
        
        print("\nMost Common Genres:")
        all_genres = [g for genres in df['all_genres'] for g in genres]
        for genre, count in Counter(all_genres).most_common(15):
            print(f"{genre}: {count} tracks")
        
        print("\nAverage Track Popularity:", df['popularity'].mean())
        
        # Save detailed analysis to CSV
        output_file = "playlist_analysis.csv"
        df.to_csv(output_file, index=False)
        print(f"\nDetailed analysis saved to {output_file}")
        
        return df
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")

if __name__ == "__main__":
    print("Welcome to the Spotify Playlist Analyzer!")
    print("This tool will analyze a playlist and provide detailed insights about its content.")
    analyze_playlist()