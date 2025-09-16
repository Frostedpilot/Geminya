import json
import os
import pandas as pd

class ContentLoader:
    """Loads and manages all JSON content for the game."""
    
    def __init__(self, data_directory="data"):
        self.data_directory = data_directory
        self.loaded_content = {}
    
    def load_json_file(self, filename):
        """Load a specific JSON file."""
        filepath = os.path.join(self.data_directory, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            print(f"Warning: {filepath} not found. Returning empty list.")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing {filepath}: {e}")
            return []
    
    def load_character_csv(self, filename="character_final.csv"):
        """Load character data from CSV file and convert to expected format."""
        filepath = os.path.join(self.data_directory, filename)
        try:
            df = pd.read_csv(filepath)
            characters = []
            
            for _, row in df.iterrows():
                # Parse stats JSON string
                stats_str = row['stats']
                try:
                    stats = json.loads(stats_str) if isinstance(stats_str, str) else stats_str
                except (json.JSONDecodeError, TypeError):
                    # Default stats if parsing fails
                    stats = {"hp": 100, "atk": 20, "mag": 10, "vit": 15, "spr": 12, "int": 8, "spd": 10, "lck": 5}
                
                character = {
                    "id": str(row['waifu_id']),
                    "name": row['name'],
                    "series": row['series'],
                    "rarity": row['rarity'],
                    "archetype": row['archetype'],
                    "elemental_type": row['elemental_type'],
                    "base_stats": stats
                }
                characters.append(character)
            
            return characters
        except FileNotFoundError:
            print(f"Warning: {filepath} not found. Returning empty list.")
            return []
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return []
    
    def load_all_content(self):
        """Load all JSON content files."""
        self.loaded_content['characters'] = self.load_character_csv()
        self.loaded_content['skills'] = self.load_json_file('skill_definitions.json')
        self.loaded_content['effects'] = self.load_json_file('effect_library.json')
        self.loaded_content['synergies'] = self.load_json_file('synergy_definitions.json')
        return self.loaded_content