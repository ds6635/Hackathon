from music_analyzer import MusicAnalyzer

def test_playlist_access():
    analyzer = MusicAnalyzer()
    
    # List of playlists to try
    playlists = [
        "https://open.spotify.com/playlist/37i9dQZF1DX80RcWXnI2CZ?si=f33fb1a4b5ea4c6e",  # Original URL
        "spotify:playlist:37i9dQZF1DX80RcWXnI2CZ",  # Spotify URI format
        "37i9dQZF1DX80RcWXnI2CZ"  # Just the ID
    ]
    
    print("Testing playlist access...")
    for playlist_url in playlists:
        print(f"\nTrying playlist URL: {playlist_url}")
        analyzer.verify_playlist_access(playlist_url)
    
    print("\nListing your playlists...")
    try:
        results = analyzer.sp.current_user_playlists()
        print("\nYour available playlists:")
        for idx, playlist in enumerate(results['items'], 1):
            print(f"\n{idx}. {playlist['name']}")
            print(f"   Tracks: {playlist['tracks']['total']}")
            print(f"   URL: {playlist['external_urls']['spotify']}")
            print(f"   ID: {playlist['id']}")
    except Exception as e:
        print(f"Error listing playlists: {str(e)}")

if __name__ == "__main__":
    test_playlist_access()