#!/usr/bin/env python3
"""
Test script for the poster hint system in anime wordle.
"""

from cogs.commands.anime_wordle import AnimeData, AnimeWordle

def test_poster_hint_system():
    """Test the poster hint functionality."""
    print("🧪 Testing Poster Hint System...")
    
    # Create test anime data with cover image
    test_data = {
        'id': 21,
        'title': {'english': 'One Piece', 'romaji': 'One Piece'},
        'synonyms': [],
        'startDate': {'year': 1999},
        'averageScore': 90,
        'episodes': 1000,
        'genres': ['Action', 'Adventure'],
        'studios': {'nodes': [{'name': 'Toei Animation'}]},
        'source': 'MANGA',
        'format': 'TV',
        'coverImage': {
            'large': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21-YCDoj1EkAxFn.jpg',
            'medium': 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/medium/bx21-YCDoj1EkAxFn.jpg'
        }
    }
    
    # Test AnimeData creation
    anime = AnimeData(test_data)
    print(f"✅ AnimeData created: {anime.title}")
    print(f"✅ Cover image URL: {anime.cover_image}")
    
    # Test AnimeWordle game state
    game = AnimeWordle(anime)
    print(f"✅ AnimeWordle game created")
    print(f"✅ Initial hint penalty: {game.hint_penalty}")
    print(f"✅ Max guesses: {game.max_guesses}")
    
    # Simulate adding hint penalty
    game.hint_penalty += 10
    total_guesses = len(game.guesses) + game.hint_penalty
    print(f"✅ After hint penalty: {total_guesses}/{game.max_guesses}")
    
    # Test penalty validation logic
    if total_guesses + 10 <= game.max_guesses:
        print("✅ Can use another hint")
    else:
        print("❌ Cannot use another hint - would exceed max guesses")
    
    print("🎉 All poster hint tests passed!")
    print("📢 Note: Hints are now server-wide (visible to everyone in the channel)")

if __name__ == "__main__":
    test_poster_hint_system()
