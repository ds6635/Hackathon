"""Interactive CLI for the Enhanced Music Analyzer."""
from enhanced_analyzer import EnhancedMusicAnalyzer
import argparse
from typing import List, Dict, Any
import sys
import textwrap

def print_search_results(results: Dict[str, List[Dict]]):
    """Print formatted search results."""
    if results['tracks']:
        print("\nTracks:")
        for i, track in enumerate(results['tracks'], 1):
            artists = ", ".join(artist['name'] for artist in track['artists'])
            print(f"{i}. {track['name']} by {artists}")
    
    if results['artists']:
        print("\nArtists:")
        for i, artist in enumerate(results['artists'], 1):
            genres = ", ".join(artist.get('genres', [])[:3])
            print(f"{i}. {artist['name']} ({genres})")
    
    if results['playlists']:
        print("\nPlaylists:")
        for i, playlist in enumerate(results['playlists'], 1):
            print(f"{i}. {playlist['name']} by {playlist['owner']['display_name']}")

def print_recommendations(recommendations: List[Dict]):
    """Print formatted recommendations."""
    print("\nRecommended Tracks:")
    for i, track in enumerate(recommendations, 1):
        artists = ", ".join(artist['name'] for artist in track['artists'])
        print(f"{i}. {track['name']} by {artists}")

def print_artist_history(history: Dict[str, Any]):
    """Print artist history information."""
    if history.get('previous_bands'):
        print("\nPrevious Bands/Groups:")
        for band in history['previous_bands']:
            print(f"- {band}")
    
    if history.get('related_artists'):
        print("\nRelated Artists:")
        for artist in history['related_artists'][:5]:
            print(f"- {artist}")
    
    if history.get('source'):
        print(f"\nSource: {history['source']}")

def select_items(items: List[Dict], prompt: str) -> List[str]:
    """Let user select items from a list."""
    if not items:
        return []
        
    print("\nAvailable items:")
    for i, item in enumerate(items, 1):
        name = item.get('name', 'Unknown')
        artists = ", ".join(a['name'] for a in item.get('artists', []))
        print(f"{i}. {name}" + (f" by {artists}" if artists else ""))
    
    selections = input(f"\n{prompt} (comma-separated numbers, or 'all'): ").strip()
    
    if selections.lower() == 'all':
        return [item['uri'] for item in items]
    
    try:
        indices = [int(i.strip()) - 1 for i in selections.split(',')]
        return [items[i]['uri'] for i in indices if 0 <= i < len(items)]
    except (ValueError, IndexError):
        print("Invalid selection.")
        return []

def handle_error(func):
    """Decorator to handle errors in CLI functions."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"\nError: {str(e)}")
            print("Please try again or choose a different option.")
            return None
    return wrapper

def main():
    print("\nInitializing Spotify connection...")
    analyzer = EnhancedMusicAnalyzer()
    print("Connected successfully!")
    
    while True:
        print("\n=== Music Discovery and Playlist Management ===")
        print("1. Search and get recommendations")
        print("2. Create a new playlist")
        print("3. Add songs to existing playlist")
        print("4. Merge playlists")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == '1':
            query = input("\nEnter a search term (song, artist, or playlist name): ").strip()
            print("\nSearch type:")
            print("1. Track-based recommendations")
            print("2. Artist-based recommendations")
            print("3. Playlist-based recommendations")
            
            search_type = input("Enter your choice (1-3): ").strip()
            type_map = {'1': 'track', '2': 'artist', '3': 'playlist'}
            
            if search_type in type_map:
                results = analyzer.analyze_and_recommend(query, type_map[search_type])
                
                print("\n=== Search Results ===")
                print_search_results(results['found_items'])
                
                if results['artist_history']:
                    print("\n=== Artist History ===")
                    print_artist_history(results['artist_history'])
                
                if results['recommendations']:
                    print("\n=== Recommendations ===")
                    print_recommendations(results['recommendations'])
                    
                    if results['suggested_playlist_names']:
                        print("\nSuggested playlist names:")
                        for i, name in enumerate(results['suggested_playlist_names'], 1):
                            print(f"{i}. {name}")
                    
                    # Ask if user wants to save recommendations
                    save = input("\nWould you like to save these recommendations? (y/n): ").strip().lower()
                    if save == 'y':
                        name = input("Enter playlist name (or press Enter for suggested): ").strip()
                        if not name and results['suggested_playlist_names']:
                            name = results['suggested_playlist_names'][0]
                        
                        playlist_id = analyzer.create_playlist(name)
                        if playlist_id:
                            track_uris = [track['uri'] for track in results['recommendations']]
                            if analyzer.add_tracks_to_playlist(playlist_id, track_uris):
                                print(f"\nCreated playlist '{name}' with recommendations!")
                
        elif choice == '2':
            name = input("\nEnter playlist name: ").strip()
            desc = input("Enter playlist description (optional): ").strip()
            
            playlist_id = analyzer.create_playlist(name, desc)
            if playlist_id:
                print(f"\nCreated playlist '{name}'!")
                
                add_songs = input("Would you like to add songs now? (y/n): ").strip().lower()
                if add_songs == 'y':
                    while True:
                        query = input("\nEnter song or artist to search (or 'done' to finish): ").strip()
                        if query.lower() == 'done':
                            break
                            
                        results = analyzer.search_music(query)
                        if results['tracks']:
                            track_uris = select_items(
                                results['tracks'],
                                "Select tracks to add"
                            )
                            if track_uris and analyzer.add_tracks_to_playlist(playlist_id, track_uris):
                                print("Added selected tracks!")
                
        elif choice == '3':
            print("\nFirst, let's find your playlist...")
            query = input("Enter playlist name to search: ").strip()
            results = analyzer.search_music(query)
            
            if results['playlists']:
                playlist_uris = select_items(
                    results['playlists'],
                    "Select playlist to add songs to"
                )
                if playlist_uris:
                    playlist_id = playlist_uris[0].split(':')[-1]
                    
                    while True:
                        query = input("\nEnter song or artist to search (or 'done' to finish): ").strip()
                        if query.lower() == 'done':
                            break
                            
                        results = analyzer.search_music(query)
                        if results['tracks']:
                            track_uris = select_items(
                                results['tracks'],
                                "Select tracks to add"
                            )
                            if track_uris and analyzer.add_tracks_to_playlist(playlist_id, track_uris):
                                print("Added selected tracks!")
                
        elif choice == '4':
            print("\nLet's find the playlists to merge...")
            source_ids = []
            
            while True:
                query = input("\nEnter playlist name to search (or 'done' to finish): ").strip()
                if query.lower() == 'done':
                    break
                    
                results = analyzer.search_music(query)
                if results['playlists']:
                    playlist_uris = select_items(
                        results['playlists'],
                        "Select playlist"
                    )
                    if playlist_uris:
                        source_ids.append(playlist_uris[0].split(':')[-1])
            
            if len(source_ids) > 1:
                print("\nNow select or create the target playlist...")
                choice = input("1. Create new playlist\n2. Select existing playlist\nChoice: ").strip()
                
                target_id = None
                if choice == '1':
                    name = input("\nEnter new playlist name: ").strip()
                    target_id = analyzer.create_playlist(name)
                elif choice == '2':
                    query = input("\nEnter target playlist name to search: ").strip()
                    results = analyzer.search_music(query)
                    if results['playlists']:
                        playlist_uris = select_items(
                            results['playlists'],
                            "Select target playlist"
                        )
                        if playlist_uris:
                            target_id = playlist_uris[0].split(':')[-1]
                
                if target_id and analyzer.merge_playlists(source_ids, target_id):
                    print("\nSuccessfully merged playlists!")
        
        elif choice == '5':
            print("\nGoodbye!")
            break
        
        else:
            print("\nInvalid choice. Please try again.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")