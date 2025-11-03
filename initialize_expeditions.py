import json
import random
import os
from datetime import datetime

# Path to the expeditions JSON file
EXPEDITIONS_PATH = os.path.join('data', 'expeditions', 'base_expeditions.json')
# Output file for selected expedition IDs
OUTPUT_PATH = os.path.join('data', 'expeditions', 'selected_expedition_ids.json')
# History file for tracking past selections
HISTORY_PATH = os.path.join('data', 'expeditions', 'expedition_history.json')

SIZE = 6
HISTORY_LIMIT = 5  # Number of past selections to exclude

def load_expedition_history():
    """Load the expedition selection history."""
    if not os.path.exists(HISTORY_PATH):
        return []
    
    try:
        with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
            history = json.load(f)
        return history
    except (json.JSONDecodeError, IOError):
        print(f"Warning: Could not load history from {HISTORY_PATH}, starting fresh")
        return []

def save_expedition_history(history, new_selection):
    """Save the updated expedition history with the new selection."""
    # Add the new selection with timestamp
    new_entry = {
        "timestamp": datetime.now().isoformat(),
        "selected_ids": new_selection
    }
    
    # Add to history and keep only the last HISTORY_LIMIT entries
    history.append(new_entry)
    if len(history) > HISTORY_LIMIT:
        history = history[-HISTORY_LIMIT:]
    
    # Save to file
    try:
        os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
        with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
        print(f"History saved to {HISTORY_PATH}")
    except IOError as e:
        print(f"Warning: Could not save history to {HISTORY_PATH}: {e}")
    
    return history

def get_excluded_expedition_ids(history):
    """Get a set of expedition IDs to exclude from the past HISTORY_LIMIT selections."""
    excluded_ids = set()
    
    for entry in history[-HISTORY_LIMIT:]:
        if 'selected_ids' in entry:
            excluded_ids.update(entry['selected_ids'])
    
    return excluded_ids

def main():
    # Load expedition history
    history = load_expedition_history()
    excluded_ids = get_excluded_expedition_ids(history)
    print(f"Excluding {len(excluded_ids)} expeditions from past {min(len(history), HISTORY_LIMIT)} selections")
    
    # Read expeditions
    with open(EXPEDITIONS_PATH, 'r', encoding='utf-8') as f:
        expeditions = json.load(f)

    # Bin expeditions by difficulty (bin size 200, from 1 to 2000)
    bins = [(start, start + 399) for start in range(1, 2000, 400)]
    selected_ids = []
    
    for bin_start, bin_end in bins:
        # Expeditions in this bin
        bin_exps = [e for e in expeditions if 'difficulty' in e and bin_start <= e['difficulty'] and e['difficulty'] <= bin_end]
        
        # Filter out expeditions that were selected in the past HISTORY_LIMIT selections
        available_exps = [e for e in bin_exps if e.get('expedition_id') not in excluded_ids]
        
        # If we don't have enough available expeditions, use all expeditions in the bin
        if len(available_exps) < SIZE:
            print(f"Warning: Only {len(available_exps)} available expeditions in difficulty range {bin_start}-{bin_end}, using all expeditions in bin")
            available_exps = bin_exps
        
        # Select expeditions
        num_to_select = min(SIZE, len(available_exps))
        chosen = random.sample(available_exps, num_to_select)
        selected_ids.extend(e['expedition_id'] for e in chosen if 'expedition_id' in e)

    # Save the current selection to history
    history = save_expedition_history(history, selected_ids)
    
    # Write selected IDs to output file
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(selected_ids, f, indent=2)
    print(f"Selected {len(selected_ids)} expedition IDs written to {OUTPUT_PATH}")
    print(f"Selected expeditions: {selected_ids}")


if __name__ == '__main__':
    main()
