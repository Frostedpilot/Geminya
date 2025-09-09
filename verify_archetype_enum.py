"""
Verification script to check that all archetypes from JSON are now in the enum
"""
import sys
import os
sys.path.append('src')

import json
import re
from game.core.archetype_system import ArchetypeGroup

# Read the archetypes.json file
with open('data/archetypes.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Get all archetype names from JSON
archetypes_from_json = [archetype['name'] for archetype in data['archetypes']]

# Get all enum values
enum_values = [archetype.value for archetype in ArchetypeGroup]

# Convert JSON names to enum format
def to_enum_format(name):
    return re.sub(r'[^a-zA-Z0-9]', '_', name.lower()).strip('_')

json_enum_format = [to_enum_format(name) for name in archetypes_from_json]

print(f"Total archetypes in JSON: {len(archetypes_from_json)}")
print(f"Total archetypes in enum: {len(enum_values)}")

# Check if all JSON archetypes are now in enum
missing_from_enum = []
for i, enum_name in enumerate(json_enum_format):
    if enum_name not in enum_values:
        missing_from_enum.append((enum_name, archetypes_from_json[i]))

if missing_from_enum:
    print(f"\nStill missing {len(missing_from_enum)} archetypes:")
    for enum_name, original_name in missing_from_enum:
        print(f"  - {original_name} ({enum_name})")
else:
    print("\n✅ SUCCESS: All archetypes from JSON are now in the enum!")

# Check for extra enum values not in JSON
extra_in_enum = []
for enum_value in enum_values:
    if enum_value not in json_enum_format:
        extra_in_enum.append(enum_value)

if extra_in_enum:
    print(f"\nExtra enum values not in JSON ({len(extra_in_enum)}):")
    for enum_value in extra_in_enum:
        print(f"  - {enum_value}")

# Test the archetype system
print("\nTesting archetype system...")
from game.core.archetype_system import archetype_system

all_archetypes = archetype_system.get_all_archetypes()
print(f"archetype_system.get_all_archetypes() returns {len(all_archetypes)} archetypes")

# Test a few specific lookups
test_names = ['mage', 'vampire', 'champion_of_chaos', 'sage_of_light']
for name in test_names:
    archetype = archetype_system.get_archetype_by_name(name)
    if archetype:
        print(f"✅ Found: {name} -> {archetype}")
    else:
        print(f"❌ Not found: {name}")

print("\nArchetype system verification complete!")
