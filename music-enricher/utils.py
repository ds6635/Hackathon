import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import discogs_client as dc

# Load environment variables
load_dotenv()

# --- Configuration ---
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
DISCOGS_USER_TOKEN = os.getenv("DISCOGS_USER_TOKEN")
USER_AGENT = 'MusicEnricherApp/1.0' 

# --- Client Initialization Functions ---

def init_spotify_client():
    """Initializes and returns an authenticated Spotipy client."""
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        raise ValueError("Spotify credentials not found in .env")
    
    # Using Client Credentials Flow - no user authentication needed
    auth_manager = SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET
    )
    
    # Create client with automatic token handling
    sp = spotipy.Spotify(auth_manager=auth_manager)
    return sp

def init_discogs_client():
    """Initializes and returns an authenticated Discogs client."""
    if not DISCOGS_USER_TOKEN:
        raise ValueError("Discogs token not found in .env")
        
    d = dc.Client(USER_AGENT, user_token=DISCOGS_USER_TOKEN)
    return d