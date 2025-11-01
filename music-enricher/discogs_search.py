"""Helper module for improved Discogs search with fallback strategies."""
from difflib import SequenceMatcher
import re
from typing import List, Dict, Any, Optional, Tuple

def clean_text(text: str) -> str:
    """Remove special characters and normalize whitespace."""
    if not text:
        return ""
    # Remove special characters but keep spaces
    cleaned = re.sub(r'[^\w\s]', '', text)
    # Normalize whitespace
    return ' '.join(cleaned.split()).lower()

def is_similar(str1: str, str2: str, threshold: float = 0.8) -> bool:
    """Check if two strings are similar using sequence matcher."""
    if not str1 or not str2:
        return False
    # Clean both strings first
    clean1 = clean_text(str1)
    clean2 = clean_text(str2)
    # Use sequence matcher to get similarity ratio
    return SequenceMatcher(None, clean1, clean2).ratio() >= threshold

def extract_artist_parts(artist_name: str) -> List[str]:
    """Extract meaningful parts from an artist name for fallback search.
    
    Examples:
        "Yasunori Mitsuda, ACE (TOMOri Kudo, CHiCO)" -> ["Yasunori Mitsuda", "ACE", "TOMOri Kudo", "CHiCO"]
        "System of a Down" -> ["System of a Down", "System"]
    """
    parts = []
    
    # First add the full name
    if artist_name:
        parts.append(artist_name)
    
    # Split on common separators and add individual names
    separators = [',', '&', 'feat.', 'ft.', 'featuring']
    name = artist_name
    for sep in separators:
        if sep in name.lower():
            parts.extend([p.strip() for p in name.split(sep) if p.strip()])
    
    # Handle parenthetical parts
    paren_match = re.findall(r'\((.*?)\)', name)
    for match in paren_match:
        # Remove the parenthetical part from original name and add both parts
        main_part = name.replace(f'({match})', '').strip()
        if main_part:
            parts.append(main_part)
        if match:
            parts.extend([p.strip() for p in match.split(',') if p.strip()])
    
    # For band names, try the first word if it's meaningful (exclude common words)
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'nor', 'for', 'yet'}
    words = name.split()
    if len(words) > 1 and words[0].lower() not in common_words:
        parts.append(words[0])
    
    # Remove duplicates while preserving order
    seen = set()
    return [x for x in parts if x and not (x in seen or seen.add(x))]

def search_discogs_release(client: Any,
                         track_name: str,
                         artist_name: str,
                         album_name: Optional[str] = None,
                         threshold: float = 0.8) -> Tuple[List[str], List[str]]:
    """Search Discogs with multiple fallback strategies.
    
    Args:
        client: Discogs client instance
        track_name: Name of the track
        artist_name: Name of the artist/band
        album_name: Optional album name
        threshold: Similarity threshold for fuzzy matching (0.0 to 1.0)
        
    Returns:
        Tuple of (genres list, styles list)
    """
    try:
        # Strategy 1: Try exact album search first
        if album_name:
            for artist_part in extract_artist_parts(artist_name):
                try:
                    results = client.search(album_name, artist=artist_part, type='release')
                    if results and results.page(1):
                        rel = results.page(1)[0]
                        # Verify we got a good match
                        if (is_similar(rel.title, album_name, threshold) or
                            any(is_similar(a.name, artist_part, threshold) 
                                for a in rel.artists)):
                            return (rel.genres if hasattr(rel, 'genres') else [],
                                    rel.styles if hasattr(rel, 'styles') else [])
                except Exception:
                    continue

        # Strategy 2: Try track name search with each artist part
        for artist_part in extract_artist_parts(artist_name):
            try:
                # Search by track name
                results = client.search(track_name, artist=artist_part, type='release')
                if results and results.page(1):
                    rel = results.page(1)[0]
                    # Verify the match
                    if any(is_similar(a.name, artist_part, threshold) 
                          for a in rel.artists):
                        return (rel.genres if hasattr(rel, 'genres') else [],
                                rel.styles if hasattr(rel, 'styles') else [])
            except Exception:
                continue
                
        # Strategy 3: Try artist-only search as last resort
        for artist_part in extract_artist_parts(artist_name):
            try:
                # First try artist search to find their main genre
                results = client.search(artist_part, type='artist')
                if results and results.page(1):
                    artist = results.page(1)[0]
                    if is_similar(artist.name, artist_part, threshold):
                        # Then get their most relevant release
                        releases = client.search('', artist=artist.name, type='release')
                        if releases and releases.page(1):
                            rel = releases.page(1)[0]
                            return (rel.genres if hasattr(rel, 'genres') else [],
                                    rel.styles if hasattr(rel, 'styles') else [])
            except Exception:
                continue
                    
    except Exception as e:
        print(f"Error in Discogs search: {str(e)}")
    
    # If all strategies fail, return empty lists
    return [], []