"""
SIMPLE DEMONSTRATION: How the Codebase Works

This script demonstrates the core concepts by creating a character
and showing how all the components work together.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.game.data.data_manager import get_data_manager
from src.game.data.character_factory import get_character_factory

def demonstrate_system():
    print("🎮 CODEBASE DEMONSTRATION")
    print("=" * 50)
    
    # STEP 1: Data Loading
    print("\n📊 STEP 1: Loading Game Data")
    print("-" * 30)
    
    data_manager = get_data_manager()
    print(f"✅ Loaded {len(data_manager.get_all_characters())} characters from CSV")
    print(f"✅ Loaded {len(data_manager.get_all_skills())} skills from JSON")
    print(f"✅ Loaded {len(data_manager.get_all_status_effects())} status effects")
    
    # Show some data examples
    print(f"\n🔍 Example Skills by Category:")
    mage_skills = data_manager.get_skills_by_category("mage_potency")
    print(f"   - Mage Skills: {len(mage_skills)} skills")
    for skill_id in list(mage_skills.keys())[:3]:
        skill = mage_skills[skill_id]
        print(f"     • {skill['name']}: {skill['description']}")
    
    # STEP 2: Character Creation
    print(f"\n🏭 STEP 2: Creating Characters")
    print("-" * 30)
    
    character_factory = get_character_factory()
    
    # Create Megumin
    megumin = character_factory.create_character("117225")
    print(f"✅ Created {megumin.character_data['name']}")
    print(f"   📊 Series: {megumin.character_data['series']}")
    print(f"   🎭 Archetype: {megumin.character_data['archetype']}")
    print(f"   💫 Element: {megumin.character_data['element']}")
    
    # Show component details
    print(f"\n🧩 STEP 3: Component Analysis")
    print("-" * 30)
    
    # Stats Component
    print(f"📈 Stats Component:")
    print(f"   • HP: {megumin.stats.get_stat('hp')}")
    print(f"   • ATK: {megumin.stats.get_stat('atk')}")
    print(f"   • MAG: {megumin.stats.get_stat('mag')}")
    print(f"   • SPD: {megumin.stats.get_stat('spd')}")
    
    # Abilities Component
    available_skills = megumin.abilities.get_available_skills()
    print(f"\n🎯 Abilities Component:")
    print(f"   • Total Skills: {len(available_skills)}")
    
    # Handle the actual skill structure
    if isinstance(available_skills, list):
        for skill in available_skills:
            skill_name = getattr(skill, 'name', 'Unknown Skill')
            skill_cooldown = getattr(skill, 'cooldown', 0)
            print(f"     - {skill_name} (Cooldown: {skill_cooldown})")
    elif isinstance(available_skills, dict):
        for skill_id, skill in available_skills.items():
            skill_name = getattr(skill, 'name', skill_id)
            skill_cooldown = getattr(skill, 'cooldown', 0)
            print(f"     - {skill_name} (Cooldown: {skill_cooldown})")
    else:
        print(f"     - Skills structure: {type(available_skills)}")
        print(f"     - Skills content: {available_skills}")
    
    # Effects Component
    print(f"\n✨ Effects Component:")
    active_effects = megumin.effects.active_effects  # Direct access to the dictionary
    print(f"   • Active Effects: {len(active_effects)}")
    if len(active_effects) == 0:
        print(f"     - No active effects (clean state)")
    else:
        for effect_id, effect in active_effects.items():
            print(f"     - {effect_id}: {effect.name}")
    
    # State Component
    print(f"\n🎭 State Component:")
    print(f"   • Is Alive: {megumin.state.is_alive()}")
    print(f"   • Is Ready to Act: {megumin.state.is_ready_to_act()}")
    print(f"   • Current HP: {megumin.current_hp}/{megumin.stats.get_stat('hp')}")
    
    # Elemental Component  
    print(f"\n🔥 Elemental System:")
    print(f"   • Elements: {megumin.get_elements()}")
    resistances = megumin.get_elemental_resistances()
    interesting_resistances = {elem: res for elem, res in resistances.items() if res != "neutral"}
    if interesting_resistances:
        print(f"   • Resistances: {interesting_resistances}")
    else:
        print(f"   • Resistances: All neutral")
    
    # STEP 4: Skill System Demonstration
    print(f"\n⚔️ STEP 4: Skill System Demo")
    print("-" * 30)
    
    # Handle both list and dict skill structures
    skill_to_demo = None
    if isinstance(available_skills, list) and len(available_skills) > 0:
        skill_to_demo = available_skills[0]
    elif isinstance(available_skills, dict) and len(available_skills) > 0:
        skill_id = list(available_skills.keys())[0]
        skill_to_demo = available_skills[skill_id]
    
    if skill_to_demo:
        skill_name = getattr(skill_to_demo, 'name', 'Unknown Skill')
        skill_description = getattr(skill_to_demo, 'description', 'No description')
        skill_target_type = getattr(skill_to_demo, 'target_type', 'Unknown target')
        skill_cooldown = getattr(skill_to_demo, 'cooldown', 0)
        
        print(f"🎯 Demonstrating Skill: {skill_name}")
        print(f"   📝 Description: {skill_description}")
        print(f"   🎯 Target Type: {skill_target_type}")
        print(f"   ⏱️ Cooldown: {skill_cooldown} turns")
        
        # Show effects if available
        if hasattr(skill_to_demo, 'effects'):
            effects = getattr(skill_to_demo, 'effects', [])
            effect_types = [effect.get('type', 'unknown') if isinstance(effect, dict) else str(effect) for effect in effects]
            print(f"   🔥 Effect Types: {effect_types}")
        
        # Show how damage would be calculated
        if hasattr(skill_to_demo, 'scaling') or hasattr(skill_to_demo, 'floor'):
            mag_stat = megumin.stats.get_stat('mag')
            floor = getattr(skill_to_demo, 'floor', 20)
            sc1 = getattr(skill_to_demo, 'sc1', 50)
            
            estimated_damage = floor + (mag_stat * sc1 / 100)
            print(f"   💥 Estimated Damage: {floor} + ({mag_stat} * {sc1}/100) = {estimated_damage:.1f}")
    else:
        print(f"🎯 No skills available to demonstrate")
        print(f"   (Character might only have basic attack)")
        
        # Show basic attack info
        print(f"\n🔨 Basic Attack Info:")
        print(f"   • Every character has a basic attack")
        print(f"   • Basic attacks use ATK stat for physical damage")
        print(f"   • No cooldown, always available")
    
    # STEP 5: Data-Driven Nature
    print(f"\n🔧 STEP 5: Data-Driven Design")
    print("-" * 30)
    
    print(f"✅ Character data loaded from: data/character_final.csv")
    print(f"✅ Skills data loaded from: data/general_skills.json")
    print(f"✅ No hardcoding - everything configurable!")
    print(f"\n💡 To add new content:")
    print(f"   • New Character: Add row to CSV file")
    print(f"   • New Skill: Add entry to JSON file")
    print(f"   • New Effect: Add handler method")
    print(f"   • Modify Balance: Change numbers in data files")
    
    # STEP 6: Architecture Benefits
    print(f"\n🏗️ STEP 6: Architecture Benefits")
    print("-" * 30)
    
    print(f"🧩 Component-Based:")
    print(f"   • Each component has single responsibility")
    print(f"   • Easy to test and modify independently")
    print(f"   • Character = Stats + Abilities + Effects + State")
    
    print(f"\n📊 Data-Driven:")
    print(f"   • Game content in external files")
    print(f"   • No coding needed for new content")
    print(f"   • Easy for designers to modify")
    
    print(f"\n🧪 Well-Tested:")
    print(f"   • Unit tests for individual components")
    print(f"   • Integration tests for system interactions")
    print(f"   • Performance tests for scalability")
    
    print(f"\n🚀 Extensible:")
    print(f"   • New components can be added easily")
    print(f"   • New skill effects via handler methods")
    print(f"   • New game mechanics without breaking existing code")
    
    print(f"\n🎉 DEMONSTRATION COMPLETE!")
    print(f"This shows how the codebase creates characters with skills")
    print(f"from external data files using a clean, modular architecture!")

if __name__ == "__main__":
    demonstrate_system()
