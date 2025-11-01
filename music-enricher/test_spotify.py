import utils

def test_spotify_connection():
    try:
        # Initialize the Spotify client
        print("Initializing Spotify client...")
        sp = utils.init_spotify_client()
        
        # Try to fetch a simple query to test the connection
        print("Testing API connection...")
        results = sp.search(q='test', limit=1)
        
        if results and 'tracks' in results:
            track = results['tracks']['items'][0]
            print("\n✅ Successfully connected to Spotify API!")
            print(f"Test query returned: {track['name']} by {track['artists'][0]['name']}")
        else:
            print("❌ Connection successful but received unexpected response format")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_spotify_connection()