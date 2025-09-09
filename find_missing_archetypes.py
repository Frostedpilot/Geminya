import json
import re

# Read the archetypes.json file
with open('data/archetypes.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Get all archetype names from JSON
archetypes_from_json = [archetype['name'] for archetype in data['archetypes']]

# Current enum values (from ArchetypeGroup)
current_enum_values = [
    'physical_attacker', 'berserker', 'mage', 'warlock', 'sorcerer', 'healer', 
    'priest', 'defender', 'knight', 'templar', 'debuffer', 'trickster', 
    'illusionist', 'buffer', 'dancer', 'bard', 'specialist', 'ninja', 
    'assassin', 'gunslinger', 'sage', 'oracle', 'engineer'
]

# Convert JSON names to enum format (lowercase, spaces to underscores)
def to_enum_format(name):
    return re.sub(r'[^a-zA-Z0-9]', '_', name.lower()).strip('_')

json_enum_format = [to_enum_format(name) for name in archetypes_from_json]

# Find missing archetypes
missing_enum_values = []
missing_original_names = []

for i, enum_name in enumerate(json_enum_format):
    if enum_name not in current_enum_values:
        missing_enum_values.append(enum_name)
        missing_original_names.append(archetypes_from_json[i])

print(f"Total archetypes in JSON: {len(archetypes_from_json)}")
print(f"Current enum has: {len(current_enum_values)} values")
print(f"Missing: {len(missing_enum_values)} archetypes\n")

print("Missing archetypes (original names):")
for i, name in enumerate(missing_original_names, 1):
    print(f"{i:2d}. {name}")

print("\nMissing archetypes (enum format):")
for i, enum_name in enumerate(missing_enum_values, 1):
    print(f"{i:2d}. {enum_name}")

# Also show which ones we already have
print("\nArchetypes already in enum:")
existing_original_names = []
for enum_name in current_enum_values:
    for i, json_enum in enumerate(json_enum_format):
        if json_enum == enum_name:
            existing_original_names.append(archetypes_from_json[i])
            break

for i, name in enumerate(existing_original_names, 1):
    print(f"{i:2d}. {name}")
