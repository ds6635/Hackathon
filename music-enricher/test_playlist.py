import utils

def test_playlist_access():
    try:
        sp = utils.init_spotify_client()
        playlist_id = "37i9dQZF1DX80RcWXnI2CZ"
        
        print("Attempting to access playlist...")
        playlist = sp.playlist(playlist_id)
        print(f"\nSuccessfully accessed playlist:")
        print(f"Name: {playlist['name']}")
        print(f"Owner: {playlist['owner']['display_name']}")
        print(f"Total tracks: {playlist['tracks']['total']}")
        
    except Exception as e:
        print(f"Error accessing playlist: {str(e)}")

if __name__ == "__main__":
    test_playlist_access()