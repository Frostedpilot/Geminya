"""
Select expedition rotation and save to database.
Usage: python initialize_expeditions.py
"""

import asyncio
import json
import os
import random
from config.config import Config
from services.database import DatabaseService

# Path to the expeditions JSON file
EXPEDITIONS_PATH = os.path.join('data', 'expeditions', 'base_expeditions.json')

SIZE = 6
HISTORY_LIMIT = 5  # Number of past selections to exclude


async def main():
    config = Config.create()
    db = DatabaseService(config)
    await db.initialize()

    # Load expedition history from DB
    history = await db.get_expedition_selection_history(HISTORY_LIMIT)
    excluded_ids = set()
    for entry in history:
        selected = entry.get('selected_ids', [])
        if isinstance(selected, str):
            selected = json.loads(selected)
        excluded_ids.update(str(eid) for eid in selected)
    print(f"Excluding {len(excluded_ids)} expeditions from past {len(history)} selections")

    # Read expedition templates from file
    with open(EXPEDITIONS_PATH, 'r', encoding='utf-8') as f:
        expeditions = json.load(f)

    # Bin expeditions by difficulty (bin size 400, from 1 to 2000)
    bins = [(start, start + 399) for start in range(1, 2000, 400)]
    selected_ids = []

    for bin_start, bin_end in bins:
        bin_exps = [e for e in expeditions if 'difficulty' in e and bin_start <= e['difficulty'] <= bin_end]

        # Filter out recently selected expeditions
        available_exps = [e for e in bin_exps if str(e.get('expedition_id')) not in excluded_ids]

        # Fallback if not enough available
        if len(available_exps) < SIZE:
            print(f"Warning: Only {len(available_exps)} available in range {bin_start}-{bin_end}, using all")
            available_exps = bin_exps

        num_to_select = min(SIZE, len(available_exps))
        chosen = random.sample(available_exps, num_to_select)
        selected_ids.extend(str(e['expedition_id']) for e in chosen if 'expedition_id' in e)

    # Save to database
    await db.set_selected_expedition_ids(selected_ids)
    await db.add_expedition_selection_history(selected_ids, HISTORY_LIMIT)

    print(f"Selected {len(selected_ids)} expedition IDs saved to database")
    print(f"Selected expeditions: {selected_ids}")

    await db.close()


if __name__ == '__main__':
    asyncio.run(main())
