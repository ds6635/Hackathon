import utils
import pandas as pd
from datetime import datetime
import time
from collections import Counter

def analyze_specific_playlist():
    try:
        # Initialize clients
        sp = utils.init_spotify_client(scope='playlist-read-private playlist-read-collaborative user-library-read')
        discogs = utils.init_discogs_client()
        
        # Papi playlist ID
        playlist_id = "2UowQCCzkcp29WvwnptAiM"
        
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
    analyze_specific_playlist()