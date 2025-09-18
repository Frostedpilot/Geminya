"""
Content Loader for the Wanderer Game

Loads expedition templates and encounters from JSON files.
"""

import json
from typing import List, Dict, Any
from pathlib import Path

from ..models import ExpeditionTemplate, Encounter


class ContentLoader:
    """
    Loads game content from JSON files
    
    Handles loading expedition templates and encounters from the data directory.
    """
    
    def __init__(self, data_directory: str = "data/expeditions"):
        self.data_directory = Path(data_directory)
    
    def load_expedition_templates(self, filename: str = "base_expeditions.json") -> List[ExpeditionTemplate]:
        """
        Load expedition templates from JSON file
        
        Args:
            filename: Name of the JSON file containing expedition templates
            
        Returns:
            List of ExpeditionTemplate objects
        """
        file_path = self.data_directory / filename
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                templates_data = json.load(f)
            
            templates = []
            for template_data in templates_data:
                template = ExpeditionTemplate.from_dict(template_data)
                templates.append(template)
            
            return templates
            
        except FileNotFoundError:
            print(f"Warning: Could not find expedition templates file: {file_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing expedition templates JSON: {e}")
            return []
        except Exception as e:
            print(f"Error loading expedition templates: {e}")
            return []
    
    def load_encounters(self, filename: str = "encounters.json") -> List[Encounter]:
        """
        Load encounters from JSON file
        
        Args:
            filename: Name of the JSON file containing encounters
            
        Returns:
            List of Encounter objects
        """
        file_path = self.data_directory / filename
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                encounters_data = json.load(f)
            
            encounters = []
            for encounter_data in encounters_data:
                encounter = Encounter.from_dict(encounter_data)
                encounters.append(encounter)
            
            return encounters
            
        except FileNotFoundError:
            print(f"Warning: Could not find encounters file: {file_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing encounters JSON: {e}")
            return []
        except Exception as e:
            print(f"Error loading encounters: {e}")
            return []
    
    def load_raw_json(self, filename: str) -> List[Dict[str, Any]]:
        """
        Load raw JSON data from a file
        
        Args:
            filename: Name of the JSON file to load
            
        Returns:
            List of dictionaries from the JSON file
        """
        file_path = self.data_directory / filename
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Could not find file: {file_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON file {filename}: {e}")
            return []
        except Exception as e:
            print(f"Error loading file {filename}: {e}")
            return []