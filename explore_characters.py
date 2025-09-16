"""Test script to explore the real character data."""

from src.game.core.content_loader import ContentLoader
from src.game.core.registries import CharacterDataRegistry
from src.game.core.character_factory import CharacterFactory

def explore_character_data():
    """Explore the loaded character data from CSV."""
    print("Exploring Real Character Data...")
    
    # Load content
    content_loader = ContentLoader()
    content = content_loader.load_all_content()
    
    # Set up registry and factory
    char_registry = CharacterDataRegistry()
    char_registry.load_from_list(content['characters'])
    char_factory = CharacterFactory(char_registry)
    
    print(f"\nTotal characters loaded: {len(char_registry.get_all())}")
    
    # Show some sample characters
    characters = list(char_registry.get_all().values())
    print("\nSample characters:")
    for i, char_data in enumerate(characters[:10]):  # Show first 10
        print(f"{i+1}. {char_data['name']} from {char_data['series']}")
        print(f"   ID: {char_data['id']}, Rarity: {char_data['rarity']}, Archetype: {char_data['archetype']}")
        stats = char_data['base_stats']
        print(f"   Stats: HP={stats['hp']}, ATK={stats['atk']}, MAG={stats['mag']}, SPD={stats['spd']}")
        print()
    
    # Test creating a few different characters
    print("Creating sample characters:")
    for i, char_id in enumerate(list(char_registry.get_all().keys())[:3]):
        character = char_factory.create_character(char_id, team=1, position=i)
        print(f"- {character.name}: HP={character.components['state'].current_hp}, ATK={character.components['stats'].get_stat('atk')}")
    
    # Show archetype distribution
    archetypes = {}
    for char_data in characters:
        archetype = char_data.get('archetype', 'Unknown')
        archetypes[archetype] = archetypes.get(archetype, 0) + 1
    
    print(f"\nArchetype distribution:")
    for archetype, count in sorted(archetypes.items()):
        print(f"  {archetype}: {count} characters")
    
    # Show series distribution (top 10)
    series_count = {}
    for char_data in characters:
        series = char_data.get('series', 'Unknown')
        series_count[series] = series_count.get(series, 0) + 1
    
    print(f"\nTop 10 series by character count:")
    for series, count in sorted(series_count.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {series}: {count} characters")

if __name__ == "__main__":
    explore_character_data()