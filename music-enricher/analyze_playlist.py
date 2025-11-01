import utils
import pandas as pd
import re
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


def split_artists(raw_name: str):
    """Split a raw artist string into a list of artist names.

    Splits on commas that are not inside parentheses, and also splits on common separators
    like ' & ' and variations of 'feat.' or 'ft.'. This handles cases like
    "Yasunori Mitsuda, ACE (TOMOri Kudo, CHiCO), Kenji Hiramatsu" without
    splitting the parenthetical comma inside ACE(...).
    """
    if not raw_name:
        return []

    parts = []
    buf = ''
    depth = 0
    for ch in raw_name:
        if ch == '(':
            depth += 1
            buf += ch
        elif ch == ')':
            depth = max(depth - 1, 0)
            buf += ch
        elif ch == ',' and depth == 0:
            parts.append(buf.strip())
            buf = ''
        else:
            buf += ch
    if buf.strip():
        parts.append(buf.strip())

    # Now further split on ' & ' and ' feat. ' patterns
    final = []
    for p in parts:
        subs = re.split(r"\s+(?:&|feat\.|ft\.|featuring)\s+", p, flags=re.I)
        for s in subs:
            s2 = s.strip()
            if s2:
                final.append(s2)
    return final

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
                # Prepare defaults
                is_local = track.get('is_local', False)
                artist_name = None
                artist_id = None
                album_name = None
                album_id = None
                discogs_genres = []
                discogs_styles = []
                spotify_genres = []
                artist_followers = 0

                # Extract basic available metadata
                artist_names = []
                artist_ids = []
                if track.get('artists'):
                    # If Spotify provides multiple artist entries, use them
                    if len(track['artists']) > 1:
                        for a in track['artists']:
                            if a.get('name'):
                                artist_names.append(a.get('name'))
                            if a.get('id'):
                                artist_ids.append(a.get('id'))
                    else:
                        # Single artist field — may contain multiple artists separated by commas
                        raw = track['artists'][0].get('name')
                        artist_names = split_artists(raw)
                        # If Spotify provided an id for the combined entry, keep it as best-effort
                        if track['artists'][0].get('id'):
                            artist_ids = [track['artists'][0].get('id')]

                if track.get('album'):
                    album_name = track['album'].get('name')
                    album_id = track['album'].get('id')

                # If this is not a local file and we have artist names/ids, fetch richer metadata
                artist_info = None
                spotify_genres = []
                artist_followers = 0
                # Try to gather metadata for each parsed artist name
                artist_infos = []
                for i, name in enumerate(artist_names):
                    fetched = None
                    aid = artist_ids[i] if i < len(artist_ids) else None
                    if not is_local and aid:
                        try:
                            fetched = sp.artist(aid)
                        except Exception:
                            fetched = None
                    if not fetched:
                        # Attempt search by artist name
                        try:
                            res = sp.search(q=f"artist:{name}", type='artist', limit=1)
                            if res and 'artists' in res and res['artists']['items']:
                                fetched = res['artists']['items'][0]
                        except Exception:
                            fetched = None
                    if fetched:
                        artist_infos.append(fetched)
                        spotify_genres.extend(fetched.get('genres', []))
                        artist_followers = max(artist_followers, fetched.get('followers', {}).get('total', 0))
                # dedupe spotify_genres
                spotify_genres = list(dict.fromkeys(spotify_genres))

                # Album info (optional)
                album_info = None
                if not is_local and album_id:
                    try:
                        album_info = sp.album(album_id)
                    except Exception:
                        album_info = None

                # Attempt Discogs search only if we have some textual metadata
                try:
                    # Try multiple artist candidates and fall back to track-level searches
                    search_album = album_name or track.get('name') or ''
                    found = False
                    # First try album-based search using each parsed artist
                    for a_name in (artist_names or []):
                        if not a_name:
                            continue
                        try:
                            results = discogs.search(search_album, artist=a_name, type='release')
                            if results and results.page(1):
                                rel = results.page(1)[0]
                                discogs_genres = rel.genres if hasattr(rel, 'genres') else []
                                discogs_styles = rel.styles if hasattr(rel, 'styles') else []
                                found = True
                                break
                        except Exception:
                            continue
                    # If no album-based result, try searching by track name + artist
                    if not found:
                        search_track = track.get('name') or ''
                        for a_name in (artist_names or []):
                            if not a_name:
                                continue
                            try:
                                results = discogs.search(search_track, artist=a_name, type='release')
                                if results and results.page(1):
                                    rel = results.page(1)[0]
                                    discogs_genres = rel.genres if hasattr(rel, 'genres') else []
                                    discogs_styles = rel.styles if hasattr(rel, 'styles') else []
                                    found = True
                                    break
                            except Exception:
                                continue
                except Exception:
                    discogs_genres = []
                    discogs_styles = []

                # Build the track record using fallbacks for local/missing metadata
                release_date = None
                if album_info and album_info.get('release_date'):
                    release_date = album_info.get('release_date')
                elif track.get('album') and track['album'].get('release_date'):
                    release_date = track['album'].get('release_date')
                else:
                    release_date = 'Unknown'

                release_year = release_date[:4] if release_date and release_date != 'Unknown' else 'Unknown'

                track_data = {
                    'track_name': track.get('name'),
                    'artist_name': artist_name or 'Unknown Artist',
                    'album_name': album_name or 'Unknown Album',
                    'release_date': release_date,
                    'release_year': release_year,
                    'popularity': track.get('popularity', 0),
                    'duration_ms': track.get('duration_ms', 0),
                    'spotify_genres': spotify_genres,
                    'artist_followers': artist_followers,
                    'discogs_genres': discogs_genres,
                    'discogs_styles': discogs_styles,
                    'all_genres': list(set(spotify_genres + discogs_genres)),
                    'is_local': is_local
                }

                tracks_data.append(track_data)

            except Exception as e:
                # Log and continue; local tracks or missing metadata should not stop analysis
                print(f"\nError processing track {track.get('name', '<unknown>')}: {str(e)}")

            # Respect rate limits; local tracks don't need external calls, so shorter sleep
            time.sleep(0.5)
        
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