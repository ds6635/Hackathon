import utils
import pandas as pd
import time

def extract_spotify_data(playlist_url, sp):
    """
    Extracts core track and album data from a Spotify playlist.
    Returns a list of dictionaries.
    """
    track_data = []
    
    # Example: Parse the playlist ID from the URL
    playlist_id = playlist_url.split('/')[-1].split('?')[0]
    results = sp.playlist_items(playlist_id)

    for item in results['items']:
        track = item['track']
        
        # We need artist, album, and track name for Discogs lookup
        if track and track['album'] and track['artists']:
            data = {
                'spotify_id': track['id'],
                'track_name': track['name'],
                'artist_name': track['artists'][0]['name'],
                'album_name': track['album']['name'],
                'release_year': track['album']['release_date'][:4],
                'spotify_genre_hint': sp.artist(track['artists'][0]['id']).get('genres', [])
            }
            track_data.append(data)
            
    return track_data

def enrich_with_discogs(track_list, d):
    """
    Iterates through track list and queries Discogs for detailed genre/style.
    """
    enriched_data = []

    for i, track in enumerate(track_list):
        print(f"[{i+1}/{len(track_list)}] Looking up: {track['artist_name']} - {track['track_name']}...")
        
        # 1. Search for the release (Album or Single)
        search_results = d.search(
            track['album_name'], 
            artist=track['artist_name'], 
            type='release'
        )
        
        discogs_genres = []
        discogs_styles = []

        if search_results and search_results.page(1):
            # Take the most relevant (first) result
            release = search_results.page(1)[0]
            
            # 2. Get the full release details
            # We fetch the full object to ensure we get all data keys
            full_release = d.release(release.id) 
            
            # Discogs API returns lists for genres and styles
            discogs_genres = full_release.genres if full_release.genres else []
            discogs_styles = full_release.styles if full_release.styles else []

        # Merge the new fields into the track dictionary
        track['discogs_genres'] = discogs_genres
        track['discogs_styles'] = discogs_styles
        enriched_data.append(track)
        
        # Respect the Discogs rate limit (60 requests/minute -> 1 request/second minimum)
        time.sleep(1.0) 
        
    return enriched_data

if __name__ == "__main__":
    try:
        # --- Initialization ---
        sp = utils.init_spotify_client()
        d = utils.init_discogs_client()
        
        # Replace this URL with a Spotify playlist you want to analyze
        TARGET_PLAYLIST_URL = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M" # Example: A Popular Playlist

        print("--- Starting Spotify Data Extraction ---")
        track_list = extract_spotify_data(TARGET_PLAYLIST_URL, sp)
        print(f"Extracted {len(track_list)} tracks from Spotify.")
        
        print("\n--- Starting Discogs Data Enrichment ---")
        enriched_data = enrich_with_discogs(track_list, d)
        
        # --- Transformation (Creating a DataFrame) ---
        df = pd.DataFrame(enriched_data)
        
        # --- Load (Saving to CSV) ---
        output_file = "enriched_music_data.csv"
        df.to_csv(output_file, index=False)
        print(f"\n✅ Success! Data saved to {output_file}")
        
        # Displaying the first few rows for confirmation
        print("\nFirst 5 enriched tracks:")
        print(df[['track_name', 'artist_name', 'spotify_genre_hint', 'discogs_genres', 'discogs_styles']].head())

    except Exception as e:
        print(f"\n❌ A critical error occurred: {e}")