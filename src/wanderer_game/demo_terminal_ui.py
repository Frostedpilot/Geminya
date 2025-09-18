#!/usr/bin/env python3
"""
Wanderer Game Terminal UI Demo

Interactive terminal interface to showcase the Wanderer Game system.
Allows users to create teams, select expeditions, and watch them resolve in real-time.
"""

import sys
import os
import time
import random
from typing import List, Optional, Dict, Any
from dataclasses import asdict

# Add the parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.wanderer_game.registries.data_manager import DataManager
from src.wanderer_game.systems.expedition_resolver import ExpeditionResolver
from src.wanderer_game.models.character import Character, Team
from src.wanderer_game.models.expedition import ExpeditionTemplate, Expedition, ActiveExpedition, ExpeditionStatus
from src.wanderer_game.models.encounter import EncounterType, EncounterOutcome


class Colors:
    """ANSI color codes for terminal output"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'


class WandererGameUI:
    """Terminal UI for the Wanderer Game demo"""
    
    def __init__(self):
        self.data_manager = None
        self.expedition_resolver = None
        self.current_team = None
        self.available_characters = []
        
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title: str):
        """Print a styled header"""
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}{title.center(60)}{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    def print_section(self, title: str):
        """Print a section header"""
        print(f"\n{Colors.YELLOW}{Colors.BOLD}=== {title} ==={Colors.RESET}")
    
    def print_character(self, char: Character, index: Optional[int] = None):
        """Print character information in a formatted way"""        
        prefix = f"{index:2d}. " if index is not None else "    "
        
        print(f"{prefix}{Colors.WHITE}{char.name}{Colors.RESET} "
              f"({Colors.CYAN}{char.series}{Colors.RESET}) "
              f"- {Colors.GREEN}{char.archetype}{Colors.RESET}")
        
        # Show stats
        stats = char.base_stats
        print(f"      Stats: HP:{stats.hp} ATK:{stats.atk} MAG:{stats.mag} "
              f"VIT:{stats.vit} SPR:{stats.spr} INT:{stats.intel} "
              f"SPD:{stats.spd} LCK:{stats.lck}")
        
        # Show elements
        if char.elemental_types:
            elements = ", ".join(char.elemental_types)
            print(f"      Elements: {Colors.BLUE}{elements}{Colors.RESET}")
    
    def print_expedition_template(self, template: ExpeditionTemplate, index: int):
        """Print expedition template information"""
        difficulty_color = Colors.GREEN if template.difficulty <= 200 else Colors.YELLOW if template.difficulty <= 400 else Colors.RED
        
        print(f"{index:2d}. {Colors.BOLD}{template.name}{Colors.RESET}")
        print(f"    Duration: {Colors.CYAN}{template.duration_hours}h{Colors.RESET} | "
              f"Difficulty: {difficulty_color}{template.difficulty}{Colors.RESET}")
        print(f"    Favored: {template.num_favored_affinities} | "
              f"Disfavored: {template.num_disfavored_affinities}")
        
        # Show encounter tags
        if template.encounter_pool_tags:
            tags = ", ".join(template.encounter_pool_tags[:5])  # Show first 5 tags
            if len(template.encounter_pool_tags) > 5:
                tags += f" (+{len(template.encounter_pool_tags) - 5} more)"
            print(f"    Tags: {Colors.GRAY}{tags}{Colors.RESET}")
    
    def initialize_system(self):
        """Initialize the game data and systems"""
        print(f"{Colors.YELLOW}Loading Wanderer Game data...{Colors.RESET}")
        
        try:
            self.data_manager = DataManager()
            success = self.data_manager.load_all_data()
            
            if not success:
                print(f"{Colors.RED}❌ Failed to load game data!{Colors.RESET}")
                return False
            
            self.expedition_resolver = ExpeditionResolver(
                self.data_manager.get_encounters_as_dict(), 
                self.data_manager.get_loot_generator()
            )
            
            # Get some interesting characters for selection
            all_characters = self.data_manager.get_character_registry().get_all_characters()
            
            # Filter for diverse and interesting characters
            self.available_characters = self._select_diverse_characters(all_characters, 30)
            
            summary = self.data_manager.get_data_summary()
            print(f"{Colors.GREEN}✓ Loaded {summary['characters']} characters, "
                  f"{summary['expedition_templates']} expeditions, "
                  f"{summary['encounters']} encounters{Colors.RESET}")
            
            return True
            
        except Exception as e:
            print(f"{Colors.RED}❌ Error initializing system: {e}{Colors.RESET}")
            return False
    
    def _select_diverse_characters(self, all_characters: List[Character], count: int) -> List[Character]:
        """Select a diverse set of characters for the demo"""
        if not all_characters:
            return []
        
        # If we have fewer characters than requested, return all
        if len(all_characters) <= count:
            return all_characters
        
        # Group by series to ensure diversity
        by_series = {}
        for char in all_characters:
            if char.series_id not in by_series:
                by_series[char.series_id] = []
            by_series[char.series_id].append(char)
        
        selected = []
        
        # Try to get characters from different series
        series_list = list(by_series.keys())
        random.shuffle(series_list)
        
        for series_id in series_list:
            if len(selected) >= count:
                break
            # Pick 1-2 characters from each series
            available = by_series[series_id]
            chars_to_pick = min(2, len(available), count - len(selected))
            selected.extend(random.sample(available, chars_to_pick))
        
        # Fill remaining spots with random characters if needed
        remaining_count = count - len(selected)
        if remaining_count > 0:
            other_chars = [c for c in all_characters if c not in selected]
            if other_chars:
                selected.extend(random.sample(other_chars, min(remaining_count, len(other_chars))))
        
        return selected[:count]
    
    def team_selection_menu(self):
        """Menu for selecting team members"""
        while True:
            self.clear_screen()
            self.print_header("🎭 Team Selection")
            
            if self.current_team and self.current_team.characters:
                self.print_section("Current Team")
                for i, char in enumerate(self.current_team.characters):
                    self.print_character(char, i + 1)
                print(f"\n{Colors.GREEN}Team Size: {len(self.current_team.characters)}/3{Colors.RESET}")
            else:
                print(f"{Colors.GRAY}No team members selected yet.{Colors.RESET}")
            
            print(f"\n{Colors.YELLOW}Available Actions:{Colors.RESET}")
            print("1. Add character to team")
            print("2. Remove character from team")
            print("3. Auto-generate random team")
            print("4. Continue to expedition selection")
            print("0. Return to main menu")
            
            choice = input(f"\n{Colors.CYAN}Enter your choice: {Colors.RESET}").strip()
            
            if choice == "1":
                self._add_character_to_team()
            elif choice == "2":
                self._remove_character_from_team()
            elif choice == "3":
                self._generate_random_team()
            elif choice == "4":
                if self.current_team and self.current_team.characters:
                    return "continue"
                else:
                    print(f"{Colors.RED}❌ Please select at least one character first!{Colors.RESET}")
                    input("Press Enter to continue...")
            elif choice == "0":
                return "back"
            else:
                print(f"{Colors.RED}❌ Invalid choice. Please try again.{Colors.RESET}")
                input("Press Enter to continue...")
    
    def _add_character_to_team(self):
        """Add a character to the current team"""
        # Get current team members
        current_members = self.current_team.characters if self.current_team else []
        
        if len(current_members) >= 3:
            print(f"{Colors.RED}❌ Team is already full (3/3 characters)!{Colors.RESET}")
            input("Press Enter to continue...")
            return
        
        self.clear_screen()
        self.print_header("📋 Available Characters")
        
        # Filter out characters already in team
        current_members = self.current_team.characters if self.current_team else []
        available_chars = [char for char in self.available_characters if char not in current_members]
        
        if not available_chars:
            print(f"{Colors.RED}❌ No available characters to add!{Colors.RESET}")
            input("Press Enter to continue...")
            return
        
        for i, char in enumerate(available_chars):
            self.print_character(char, i + 1)
        
        try:
            choice = input(f"\n{Colors.CYAN}Enter character number (0 to cancel): {Colors.RESET}").strip()
            
            if choice == "0":
                return
            
            index = int(choice) - 1
            if 0 <= index < len(available_chars):
                char = available_chars[index]
                
                # Create new team or add to existing team
                if not self.current_team:
                    self.current_team = Team([char])
                else:
                    # Create new team with updated characters list
                    new_characters = self.current_team.characters + [char]
                    self.current_team = Team(new_characters)
                
                print(f"{Colors.GREEN}✓ Added {char.name} to the team!{Colors.RESET}")
            else:
                print(f"{Colors.RED}❌ Invalid character number!{Colors.RESET}")
        
        except ValueError:
            print(f"{Colors.RED}❌ Please enter a valid number!{Colors.RESET}")
        
        input("Press Enter to continue...")
    
    def _remove_character_from_team(self):
        """Remove a character from the current team"""
        if not self.current_team or not self.current_team.characters:
            print(f"{Colors.RED}❌ No characters in team to remove!{Colors.RESET}")
            input("Press Enter to continue...")
            return
        
        self.clear_screen()
        self.print_header("❌ Remove Character")
        
        for i, char in enumerate(self.current_team.characters):
            self.print_character(char, i + 1)
        
        try:
            choice = input(f"\n{Colors.CYAN}Enter character number to remove (0 to cancel): {Colors.RESET}").strip()
            
            if choice == "0":
                return
            
            index = int(choice) - 1
            if 0 <= index < len(self.current_team.characters):
                removed_char = self.current_team.characters[index]
                # Create new team without the removed character
                remaining_chars = [char for i, char in enumerate(self.current_team.characters) if i != index]
                if remaining_chars:
                    self.current_team = Team(remaining_chars)
                else:
                    self.current_team = None  # No characters left
                print(f"{Colors.GREEN}✓ Removed {removed_char.name} from the team!{Colors.RESET}")
            else:
                print(f"{Colors.RED}❌ Invalid character number!{Colors.RESET}")
        
        except ValueError:
            print(f"{Colors.RED}❌ Please enter a valid number!{Colors.RESET}")
        
        input("Press Enter to continue...")
    
    def _generate_random_team(self):
        """Generate a random team of 3 characters"""
        # If available characters list is empty, populate it
        if not self.available_characters and self.data_manager:
            all_characters = self.data_manager.get_character_registry().get_all_characters()
            self.available_characters = self._select_diverse_characters(all_characters, 30)
        
        if len(self.available_characters) < 3:
            # Fall back to using all characters if we don't have enough
            if self.data_manager:
                all_characters = self.data_manager.get_character_registry().get_all_characters()
                selected_chars = random.sample(all_characters, min(3, len(all_characters)))
            else:
                print(f"{Colors.RED}❌ No characters available!{Colors.RESET}")
                return
        else:
            selected_chars = random.sample(self.available_characters, 3)
        
        self.current_team = Team(selected_chars)
        
        print(f"{Colors.GREEN}✓ Generated random team!{Colors.RESET}")
        time.sleep(1)
    
    def _simulate_expedition_result(self, expedition: Expedition, team: Team):
        """Simulate an expedition result for demo purposes"""
        # Simple simulation based on team stats and expedition difficulty
        total_team_power = sum([
            char.base_stats.hp + char.base_stats.atk + char.base_stats.mag +
            char.base_stats.vit + char.base_stats.spr + char.base_stats.intel +
            char.base_stats.spd + char.base_stats.lck
            for char in team.characters
        ])
        
        # Calculate success rate based on team power vs expedition difficulty
        avg_team_power = total_team_power / len(team.characters)
        power_ratio = avg_team_power / expedition.difficulty
        
        # Generate encounter results
        total_encounters = expedition.encounter_count
        great_successes = 0
        successes = 0
        failures = 0
        mishaps = 0
        
        for _ in range(total_encounters):
            roll = random.random()
            if power_ratio > 1.5:  # Very strong team
                if roll < 0.3:
                    great_successes += 1
                elif roll < 0.8:
                    successes += 1
                elif roll < 0.95:
                    failures += 1
                else:
                    mishaps += 1
            elif power_ratio > 1.0:  # Adequate team
                if roll < 0.15:
                    great_successes += 1
                elif roll < 0.65:
                    successes += 1
                elif roll < 0.9:
                    failures += 1
                else:
                    mishaps += 1
            else:  # Weak team
                if roll < 0.05:
                    great_successes += 1
                elif roll < 0.35:
                    successes += 1
                elif roll < 0.8:
                    failures += 1
                else:
                    mishaps += 1
        
        # Simple loot calculation
        loot_items = max(0, great_successes * 2 + successes - mishaps)
        
        # Create a simple result object
        class SimpleExpeditionResult:
            def __init__(self):
                self.total_encounters = total_encounters
                self.great_successes = great_successes
                self.successes = successes
                self.failures = failures
                self.mishaps = mishaps
                self.final_loot_items = loot_items
        
        return SimpleExpeditionResult()
    
    def expedition_selection_menu(self):
        """Menu for selecting expeditions"""
        if not self.data_manager:
            print(f"{Colors.RED}❌ Data manager not initialized!{Colors.RESET}")
            return "back"
        
        templates = self.data_manager.get_expedition_templates()
        
        while True:
            self.clear_screen()
            self.print_header("🗺️ Expedition Selection")
            
            # Show current team summary
            if self.current_team:
                self.print_section("Your Team")
                team_names = [char.name for char in self.current_team.characters]
                print(f"    {Colors.GREEN}{', '.join(team_names)}{Colors.RESET}")
            
            self.print_section("Available Expeditions")
            
            # Show first 15 expeditions
            for i, template in enumerate(templates[:15]):
                self.print_expedition_template(template, i + 1)
            
            if len(templates) > 15:
                print(f"\n{Colors.GRAY}... and {len(templates) - 15} more expeditions{Colors.RESET}")
            
            print(f"\n{Colors.YELLOW}Available Actions:{Colors.RESET}")
            print("1-15. Select expedition by number")
            print("r. Select random expedition")
            print("s. Show more expeditions")
            print("0. Back to team selection")
            
            choice = input(f"\n{Colors.CYAN}Enter your choice: {Colors.RESET}").strip().lower()
            
            if choice == "0":
                return "back"
            elif choice == "r":
                template = random.choice(templates)
                return self._run_expedition(template)
            elif choice == "s":
                self._show_all_expeditions(templates)
            else:
                try:
                    index = int(choice) - 1
                    if 0 <= index < min(15, len(templates)):
                        template = templates[index]
                        return self._run_expedition(template)
                    else:
                        print(f"{Colors.RED}❌ Invalid expedition number!{Colors.RESET}")
                        input("Press Enter to continue...")
                except ValueError:
                    print(f"{Colors.RED}❌ Please enter a valid number or 'r' for random!{Colors.RESET}")
                    input("Press Enter to continue...")
    
    def _show_all_expeditions(self, templates: List[ExpeditionTemplate]):
        """Show all available expeditions"""
        self.clear_screen()
        self.print_header("🗺️ All Expeditions")
        
        for i, template in enumerate(templates):
            self.print_expedition_template(template, i + 1)
            
            if (i + 1) % 10 == 0:
                choice = input(f"\n{Colors.CYAN}Press Enter to continue, or 'q' to go back: {Colors.RESET}").strip().lower()
                if choice == 'q':
                    return
                self.clear_screen()
                self.print_header("🗺️ All Expeditions (continued)")
        
        input(f"\n{Colors.CYAN}Press Enter to return to expedition selection...{Colors.RESET}")
    
    def _run_expedition(self, template: ExpeditionTemplate):
        """Run an expedition and show the results"""
        if not self.current_team:
            print(f"{Colors.RED}❌ No team selected!{Colors.RESET}")
            return "back"
        
        self.clear_screen()
        self.print_header(f"🚀 Expedition: {template.name}")
        
        # Show expedition info
        print(f"{Colors.BOLD}Duration:{Colors.RESET} {template.duration_hours} hours")
        print(f"{Colors.BOLD}Difficulty:{Colors.RESET} {template.difficulty}")
        print(f"{Colors.BOLD}Team:{Colors.RESET} {', '.join([c.name for c in self.current_team.characters])}")
        
        print(f"\n{Colors.YELLOW}🎬 Starting expedition...{Colors.RESET}")
        time.sleep(2)
        
        try:
            # Generate expedition instance
            team_series_ids = [char.series_id for char in self.current_team.characters]
            expedition = template.generate_expedition(team_series_ids)
            
            print(f"\n{Colors.CYAN}📋 Expedition Details:{Colors.RESET}")
            print(f"  Expected encounters: {expedition.encounter_count}")
            print(f"  Favored affinities: {len(expedition.favored_affinities)}")
            print(f"  Disfavored affinities: {len(expedition.disfavored_affinities)}")
            
            # Show affinities
            if expedition.favored_affinities:
                favored_str = ", ".join([f"{a.type.value}:{a.value}" for a in expedition.favored_affinities])
                print(f"  {Colors.GREEN}Favored:{Colors.RESET} {favored_str}")
            
            if expedition.disfavored_affinities:
                disfavored_str = ", ".join([f"{a.type.value}:{a.value}" for a in expedition.disfavored_affinities])
                print(f"  {Colors.RED}Disfavored:{Colors.RESET} {disfavored_str}")
            
            input(f"\n{Colors.CYAN}Press Enter to begin the expedition...{Colors.RESET}")
            
            # Create a simple expedition result for demo
            result = self._simulate_expedition_result(expedition, self.current_team)
            
            self._show_expedition_results(result, expedition)
            
        except Exception as e:
            print(f"{Colors.RED}❌ Error running expedition: {e}{Colors.RESET}")
            import traceback
            traceback.print_exc()
        
        input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")
        return "continue"
    
    def _show_expedition_results(self, result, expedition: Expedition):
        """Display expedition results"""
        self.clear_screen()
        self.print_header("📊 Expedition Results")
        
        print(f"{Colors.BOLD}Expedition Status:{Colors.RESET} {Colors.GREEN}COMPLETED{Colors.RESET}")
        print(f"{Colors.BOLD}Total Encounters:{Colors.RESET} {result.total_encounters}")
        
        # Show encounter outcomes
        print(f"\n{Colors.YELLOW}Encounter Outcomes:{Colors.RESET}")
        if hasattr(result, 'great_successes'):
            print(f"  {Colors.YELLOW}⭐ Great Successes:{Colors.RESET} {result.great_successes}")
        if hasattr(result, 'successes'):
            print(f"  {Colors.GREEN}✓ Successes:{Colors.RESET} {result.successes}")
        if hasattr(result, 'failures'):
            print(f"  {Colors.RED}✗ Failures:{Colors.RESET} {result.failures}")
        if hasattr(result, 'mishaps'):
            print(f"  {Colors.RED}💥 Mishaps:{Colors.RESET} {result.mishaps}")
        
        # Show loot if available
        if hasattr(result, 'final_loot_items'):
            print(f"\n{Colors.YELLOW}Loot Obtained:{Colors.RESET}")
            if result.final_loot_items:
                print(f"  {Colors.GREEN}🎁 Items found: {result.final_loot_items}{Colors.RESET}")
            else:
                print(f"  {Colors.GRAY}No loot obtained{Colors.RESET}")
        
        # Show any special effects or modifiers
        if hasattr(expedition, 'stat_bonuses') and expedition.stat_bonuses:
            print(f"\n{Colors.YELLOW}Team Effects:{Colors.RESET}")
            for stat, bonus in expedition.stat_bonuses.items():
                bonus_str = f"+{bonus}" if bonus > 0 else str(bonus)
                print(f"  {stat.upper()}: {bonus_str}")
        
        # Calculate success rate
        total_outcomes = getattr(result, 'total_encounters', 0)
        if total_outcomes > 0:
            successes = getattr(result, 'successes', 0) + getattr(result, 'great_successes', 0)
            success_rate = (successes / total_outcomes) * 100
            
            color = Colors.GREEN if success_rate >= 70 else Colors.YELLOW if success_rate >= 40 else Colors.RED
            print(f"\n{Colors.BOLD}Success Rate:{Colors.RESET} {color}{success_rate:.1f}%{Colors.RESET}")
    
    def main_menu(self):
        """Main menu loop"""
        while True:
            self.clear_screen()
            self.print_header("🎮 Wanderer Game Demo")
            
            print(f"{Colors.BOLD}Welcome to the Wanderer Game Terminal Demo!{Colors.RESET}")
            print("Experience the expedition system with real game data.\n")
            
            if not self.data_manager:
                print(f"{Colors.YELLOW}System not initialized.{Colors.RESET}")
                print("1. Initialize Game System")
                print("0. Exit")
            else:
                summary = self.data_manager.get_data_summary()
                print(f"{Colors.GREEN}✓ System Ready{Colors.RESET}")
                print(f"  Characters: {summary['characters']}")
                print(f"  Expeditions: {summary['expedition_templates']}")
                print(f"  Encounters: {summary['encounters']}")
                
                print(f"\n{Colors.YELLOW}Available Actions:{Colors.RESET}")
                print("1. Create/Edit Team")
                print("2. Quick Start (Random Team + Expedition)")
                print("3. System Status")
                print("0. Exit")
            
            choice = input(f"\n{Colors.CYAN}Enter your choice: {Colors.RESET}").strip()
            
            if choice == "1":
                if not self.data_manager:
                    if self.initialize_system():
                        print(f"{Colors.GREEN}✓ System initialized successfully!{Colors.RESET}")
                        input("Press Enter to continue...")
                else:
                    result = self.team_selection_menu()
                    if result == "continue":
                        self.expedition_selection_menu()
            
            elif choice == "2" and self.data_manager:
                self._quick_start()
            
            elif choice == "3" and self.data_manager:
                self._show_system_status()
            
            elif choice == "0":
                print(f"{Colors.YELLOW}Thanks for playing the Wanderer Game Demo!{Colors.RESET}")
                break
            
            else:
                print(f"{Colors.RED}❌ Invalid choice. Please try again.{Colors.RESET}")
                input("Press Enter to continue...")
    
    def _quick_start(self):
        """Quick start with random team and expedition"""
        if not self.data_manager:
            print(f"{Colors.RED}❌ Data manager not initialized!{Colors.RESET}")
            return
        
        print(f"{Colors.YELLOW}🎲 Quick Start - Generating random experience...{Colors.RESET}")
        
        # Generate random team
        self._generate_random_team()
        
        # Select random expedition
        templates = self.data_manager.get_expedition_templates()
        template = random.choice(templates)
        
        print(f"{Colors.GREEN}✓ Selected expedition: {template.name}{Colors.RESET}")
        time.sleep(1)
        
        self._run_expedition(template)
    
    def _show_system_status(self):
        """Show detailed system status"""
        if not self.data_manager:
            print(f"{Colors.RED}❌ Data manager not initialized!{Colors.RESET}")
            return
        
        self.clear_screen()
        self.print_header("⚙️ System Status")
        
        summary = self.data_manager.get_data_summary()
        
        print(f"{Colors.BOLD}Data Manager:{Colors.RESET}")
        print(f"  Status: {Colors.GREEN}Loaded{Colors.RESET}")
        print(f"  Characters: {summary['characters']}")
        print(f"  Series: {summary['series']}")
        print(f"  Expedition Templates: {summary['expedition_templates']}")
        print(f"  Encounters: {summary['encounters']}")
        print(f"  Loot Tables: {summary['loot_tables']}")
        
        # Show character archetype distribution
        all_chars = self.data_manager.get_character_registry().get_all_characters()
        archetype_counts = {}
        for char in all_chars:
            archetype_counts[char.archetype] = archetype_counts.get(char.archetype, 0) + 1
        
        print(f"\n{Colors.BOLD}Character Archetype Distribution:{Colors.RESET}")
        for archetype, count in sorted(archetype_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / len(all_chars)) * 100
            print(f"  {archetype}: {count} ({percentage:.1f}%)")
        
        # Show expedition difficulty distribution
        templates = self.data_manager.get_expedition_templates()
        difficulties = [t.difficulty for t in templates]
        avg_difficulty = sum(difficulties) / len(difficulties)
        min_difficulty = min(difficulties)
        max_difficulty = max(difficulties)
        
        print(f"\n{Colors.BOLD}Expedition Difficulty Range:{Colors.RESET}")
        print(f"  Average: {avg_difficulty:.0f}")
        print(f"  Range: {min_difficulty} - {max_difficulty}")
        
        input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.RESET}")


def main():
    """Main entry point"""
    try:
        ui = WandererGameUI()
        ui.main_menu()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Demo interrupted by user. Goodbye!{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}❌ Fatal error: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()