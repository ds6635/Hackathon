import sys
from analyze_playlist import get_playlist_id, split_artists
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

    _prev_len = 0
    def print_progress(msg: str):
        nonlocal _prev_len
        sys.stdout.write('\r' + msg + ' ' * max(0, _prev_len - len(msg)))
        sys.stdout.flush()
        _prev_len = len(msg)

    for idx, item in enumerate(results['items'], 1):
        if not item['track']:
            continue
        track = item['track']
        print_progress(f"Processing {idx}/{total_tracks}: {track.get('name')}")

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

        # Try Discogs first, then fall back to other sources
        album_name = track.get('album', {}).get('name') if track.get('album') else None
        discogs_genres = []
        discogs_styles = []
        try:
            from discogs_search import search_discogs_release
            discogs_genres, discogs_styles = search_discogs_release(
                client=discogs,
                track_name=track.get('name', ''),
                artist_name=artist_names[0] if artist_names else '',
                album_name=album_name,
                threshold=0.8
            )
            
            # If Discogs search failed, try additional sources
            if not discogs_genres and not discogs_styles:
                from metadata_sources import get_metadata_from_sources
                extra_genres, extra_styles = get_metadata_from_sources(
                    track_name=track.get('name', ''),
                    artist_name=artist_names[0] if artist_names else '',
                    album_name=album_name
                )
                discogs_genres.extend(extra_genres)
                discogs_styles.extend(extra_styles)
                # Deduplicate
                discogs_genres = list(dict.fromkeys(discogs_genres))
                discogs_styles = list(dict.fromkeys(discogs_styles))
                
        except Exception as e:
            print(f"\nMetadata search error: {str(e)}")
            discogs_genres = []
            discogs_styles = []

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
