import utils

def test_discogs_connection():
    try:
        # Initialize the Discogs client
        print("Initializing Discogs client...")
        d = utils.init_discogs_client()
        
        # Try to search for a release to test the connection
        print("Testing API connection...")
        search_results = d.search('Test', type='release')
        
        if search_results and search_results.page(1):
            # Get the first result
            release = search_results.page(1)[0]
            print("\n✅ Successfully connected to Discogs API!")
            print(f"Test query returned: {release.title} ({release.year if hasattr(release, 'year') else 'Year N/A'})")
            
            # Show some additional info about genres and styles if available
            if hasattr(release, 'genres'):
                print(f"Genres: {', '.join(release.genres)}")
            if hasattr(release, 'styles'):
                print(f"Styles: {', '.join(release.styles)}")
        else:
            print("❌ Connection successful but received no results")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_discogs_connection()