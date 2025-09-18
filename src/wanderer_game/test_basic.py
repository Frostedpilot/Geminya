"""
Basic integration test for the Wanderer Game system

Tests the core functionality to ensure all components work together.
"""

import time
import sys
import os

# Add the src directory to the path so we can import wanderer_game
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.wanderer_game.registries import DataManager
from src.wanderer_game.systems import ExpeditionManager, ExpeditionResolver
from src.wanderer_game.models import Team, Character, CharacterStats


def create_test_character(waifu_id: int, name: str, series_id: int = 1) -> Character:
    """Create a test character for testing purposes"""
    test_stats = CharacterStats(
        hp=100, atk=80, mag=90, vit=85, spr=95, intel=110, spd=75, lck=88
    )
    
    return Character(
        waifu_id=waifu_id,
        name=name,
        series="Test Series",
        series_id=series_id,
        genres=["Comedy", "Fantasy"],
        image_url="test.jpg",
        base_stats=test_stats,
        elemental_types=["neutral"],
        archetype="Mage",
        potency={"Mage": "A"},
        elemental_resistances={"neutral": "neutral"},
        star_level=1
    )


def test_basic_functionality():
    """Test basic wanderer game functionality"""
    print("=== Wanderer Game Basic Test ===\n")
    
    # Initialize data manager
    print("1. Initializing data manager...")
    data_manager = DataManager()
    
    # Load data
    print("2. Loading game data...")
    if data_manager.load_all_data():
        print("✓ Data loaded successfully")
    else:
        print("⚠ Some data failed to load, creating test data...")
    
    print(f"Data summary: {data_manager.get_data_summary()}\n")
    
    # Initialize expedition manager
    print("3. Initializing expedition manager...")
    expedition_manager = ExpeditionManager()
    
    # Load expedition templates
    templates = data_manager.get_expedition_templates()
    if templates:
        expedition_manager.load_expedition_templates([template.__dict__ for template in templates])
        print(f"✓ Loaded {len(templates)} expedition templates")
    else:
        print("⚠ No expedition templates loaded")
    
    # Create test team
    print("\n4. Creating test team...")
    test_characters = [
        create_test_character(1, "Alice", 1),
        create_test_character(2, "Bob", 2),
        create_test_character(3, "Carol", 1)
    ]
    test_team = Team(test_characters)
    print(f"✓ Created team with {len(test_team.characters)} characters")
    
    # Generate available expeditions
    print("\n5. Generating available expeditions...")
    current_time = time.time()
    expedition_manager.generate_available_expeditions(current_time)
    available_expeditions = expedition_manager.get_available_expeditions(current_time)
    print(f"✓ Generated {len(available_expeditions)} available expeditions")
    
    if available_expeditions:
        expedition = available_expeditions[0]
        print(f"First expedition: {expedition.name} (Difficulty: {expedition.difficulty})")
        print(f"  Duration: {expedition.duration_hours} hours")
        print(f"  Favored affinities: {len(expedition.favored_affinities)}")
        print(f"  Disfavored affinities: {len(expedition.disfavored_affinities)}")
    
    # Test expedition dispatch
    print("\n6. Testing expedition dispatch...")
    if available_expeditions:
        try:
            slot_id = expedition_manager.dispatch_expedition(
                available_expeditions[0].expedition_id,
                test_team,
                current_time
            )
            print(f"✓ Expedition dispatched to slot {slot_id}")
            
            # Get active expeditions
            active_expeditions = expedition_manager.get_active_expeditions()
            print(f"Active expeditions: {len(active_expeditions)}")
            
        except Exception as e:
            print(f"✗ Error dispatching expedition: {e}")
    
    # Test expedition resolution (simulate completion)
    print("\n7. Testing expedition resolution...")
    try:
        # Initialize resolver
        encounters = data_manager.get_encounters()
        encounter_dicts = []
        for encounter in encounters:
            # Convert encounter object to dictionary for resolver
            encounter_dict = {
                'encounter_id': encounter.encounter_id,
                'name': encounter.name,
                'type': encounter.type.value,
                'tags': encounter.tags,
                'description_success': encounter.description_success,
                'description_failure': encounter.description_failure,
                'description': encounter.description,
                'check_stat': encounter.check_stat,
                'difficulty': encounter.difficulty,
                'loot_values': encounter.loot_values
            }
            
            if encounter.condition:
                encounter_dict['condition'] = {
                    'type': encounter.condition.type.value,
                    'value': encounter.condition.value
                }
            
            if encounter.modifier:
                encounter_dict['modifier'] = {
                    'type': encounter.modifier.type.value,
                    'affinity': encounter.modifier.affinity,
                    'category': encounter.modifier.category,
                    'value': encounter.modifier.value,
                    'stat': encounter.modifier.stat
                }
            
            encounter_dicts.append(encounter_dict)
        
        resolver = ExpeditionResolver(encounter_dicts, data_manager.get_loot_generator())
        
        # Get the active expedition for resolution
        active_expeditions = expedition_manager.get_active_expeditions()
        if active_expeditions:
            slot_id = list(active_expeditions.keys())[0]
            active_expedition = expedition_manager.prepare_expedition_for_resolution(slot_id)
            
            if active_expedition:
                print(f"Resolving expedition: {active_expedition.expedition.name}")
                result = resolver.resolve(active_expedition, test_team)
                
                print(f"✓ Expedition resolved!")
                print(f"  Total encounters: {len(result.encounter_results)}")
                print(f"  Great successes: {result.great_successes}")
                print(f"  Successes: {result.successes}")
                print(f"  Failures: {result.failures}")
                print(f"  Mishaps: {result.mishaps}")
                print(f"  Final loot items: {len(result.loot_pool)}")
                print(f"  Final multiplier: {result.final_multiplier.value}")
                
                # Complete the expedition
                expedition_manager.complete_expedition(slot_id)
                print("✓ Expedition completed and slot cleared")
                
        else:
            print("⚠ No active expeditions to resolve")
            
    except Exception as e:
        print(f"✗ Error in expedition resolution: {e}")
        import traceback
        traceback.print_exc()
    
    # Final status
    print("\n8. Final status check...")
    status = expedition_manager.get_status_summary(current_time)
    print(f"Final status: {status}")
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    test_basic_functionality()