# Music Enricher Setup Guide

## Prerequisites
- Python 3.x installed
- Git installed
- A Spotify account (free account is fine)

## Step 1: Clone the Repository
```bash
git clone https://github.com/ds6635/Hackathon.git
cd Hackathon/music-enricher
```

## Step 2: Get Spotify API Credentials
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
2. Log in with your Spotify account
3. Click "Create app"
4. Fill in the app details:
   - App name: "Music Enricher" (or any name you prefer)
   - App description: "App to enrich music data"
   - Redirect URI: `http://127.0.0.1:8080/callback`
5. Accept the terms and click "Create"
6. Once created, you'll see your app in the dashboard
7. Click on your app to view the details
8. You'll find your Client ID and can view your Client Secret

## Step 3: Create Environment File
1. Create a new file named `.env` in the music-enricher directory
2. Add your Spotify credentials to the file:
```
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
```

## Step 4: Set Up Python Environment
1. Create a virtual environment:
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

2. Install required packages:
```bash
pip install spotipy discogs-client python-dotenv pandas
```

## Step 5: Run the Test
```bash
python test_spotify.py
```

If everything is set up correctly, you should see:
```
Initializing Spotify client...
Testing API connection...
✅ Successfully connected to Spotify API!
Test query returned: [song name] by [artist name]
```

## Troubleshooting
- If you get "ImportError": Make sure you've installed all required packages
- If you get "ValueError: Client credentials not found": Check your `.env` file is in the correct location and contains the correct credentials
- If you get "Authorization Error": Verify your Client ID and Secret are correct

## Notes
- The `.env` file is in `.gitignore` and should never be committed to the repository
- Each developer should use their own Spotify API credentials