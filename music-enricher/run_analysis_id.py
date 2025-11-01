import sys
from analyze_playlist import get_playlist_id
import utils
import pandas as pd
import time
from collections import Counter

# This is a non-interactive runner that calls the core logic inside analyze_playlist
# but avoids the interactive prompts. It duplicates a small part of the logic for
# convenience when testing with a provided playlist id or URL.


def process_playlist(playlist_input):
    sp = utils.init_spotify_client(scope='playlist-read-private playlist-read-collaborative user-library-read')
    discogs = utils.init_discogs_client()

    playlist_id = get_playlist_id(playlist_input)
    playlist_info = sp.playlist(playlist_id)
    print(f"Analyzing playlist: {playlist_info['name']}")
    print(f"Total tracks: {playlist_info['tracks']['total']}")

    results = sp.playlist_tracks(playlist_id)
    tracks_data = []
    total_tracks = len(results['items'])

    for idx, item in enumerate(results['items'], 1):
        if not item['track']:
            continue
        track = item['track']
        print(f"\rProcessing {idx}/{total_tracks}: {track.get('name')}", end='')

        # Use code path from analyze_playlist: build minimal record and attempt to fetch genres
        is_local = track.get('is_local', False)
        raw_artist = None
        if track.get('artists'):
            raw_artist = track['artists'][0].get('name')
        # For test runner we'll just call the same helpers from analyze_playlist module
        from analyze_playlist import split_artists
        artist_names = split_artists(raw_artist) if raw_artist else []

        spotify_genres = []
        for name in artist_names:
            try:
                res = sp.search(q=f"artist:{name}", type='artist', limit=1)
                if res and 'artists' in res and res['artists']['items']:
                    fetched = res['artists']['items'][0]
                    spotify_genres.extend(fetched.get('genres', []))
            except Exception:
                continue

        # Discogs test: try album then track
        album_name = track.get('album', {}).get('name') if track.get('album') else None
        discogs_genres = []
        discogs_styles = []
        try:
            search_album = album_name or track.get('name') or ''
            found = False
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
            pass

        record = {
            'track_name': track.get('name'),
            'artist_names': artist_names,
            'spotify_genres': list(dict.fromkeys(spotify_genres)),
            'discogs_genres': discogs_genres,
            'discogs_styles': discogs_styles,
            'is_local': is_local
        }
        tracks_data.append(record)
        time.sleep(0.5)

    print('\n\nDone. Saving CSV...')
    df = pd.DataFrame(tracks_data)
    out = f"playlist_analysis_{playlist_id}.csv"
    df.to_csv(out, index=False)
    print(f"Saved to {out}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python run_analysis_id.py <playlist_url_or_id>')
        sys.exit(1)
    process_playlist(sys.argv[1])
