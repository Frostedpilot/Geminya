import json
import random
import os

# Path to the expeditions JSON file
EXPEDITIONS_PATH = os.path.join('data', 'expeditions', 'base_expeditions.json')
# Output file for selected expedition IDs
OUTPUT_PATH = os.path.join('data', 'expeditions', 'selected_expedition_ids.json')

SIZE = 1000

def main():
    # Read expeditions
    with open(EXPEDITIONS_PATH, 'r', encoding='utf-8') as f:
        expeditions = json.load(f)


    # Bin expeditions by difficulty (bin size 200, from 1 to 2000)
    bins = [(start, start + 199) for start in range(1, 2000, 200)]
    selected_ids = []
    for bin_start, bin_end in bins:
        # Expeditions in this bin
        bin_exps = [e for e in expeditions if 'difficulty' in e and bin_start <= e['difficulty'] <= bin_end]
        # Randomly select up to 2 from this bin
        chosen = random.sample(bin_exps, min(SIZE, len(bin_exps)))
        selected_ids.extend(e['expedition_id'] for e in chosen if 'expedition_id' in e)

    # Write selected IDs to output file
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(selected_ids, f, indent=2)
    print(f"Selected expedition IDs written to {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
