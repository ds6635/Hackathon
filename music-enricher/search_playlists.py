import utils

def search_playlists(query):
    try:
        sp = utils.init_spotify_client()
        print(f"\nSearching for playlists matching: '{query}'...")
        
        # Search for playlists
        results = sp.search(q=query, type='playlist', limit=5)
        playlists = results['playlists']['items']
        
        if not playlists:
            print("No playlists found.")
            return
        
        print("\nFound playlists:")
        for idx, playlist in enumerate(playlists, 1):
            print(f"\n{idx}. {playlist['name']}")
            print(f"   Owner: {playlist['owner']['display_name']}")
            print(f"   Tracks: {playlist['tracks']['total']}")
            print(f"   URL: {playlist['external_urls']['spotify']}")
            print(f"   ID: {playlist['id']}")

    except Exception as e:
        print(f"Error searching for playlists: {str(e)}")

if __name__ == "__main__":
    # Try a broader search
    search_query = "Bubbly Pink"
    search_playlists(search_query)