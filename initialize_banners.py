"""
Script to clear all data from banner-related tables and reinitialize them with new data from banners.json.
Usage: python initialize_banners.py
"""


import asyncio
import json
import csv
from collections import defaultdict
from services.database import DatabaseService
from config import Config
import json as _json


BANNER_JSON = 'banners.json'
CHARACTER_CSV = 'data/character_final.csv'

def load_waifu_data():
    waifus = []
    waifu_by_id = {}
    waifus_by_series = defaultdict(list)
    one_star_waifus = set()
    with open(CHARACTER_CSV, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            waifu_id = int(row['waifu_id'])
            series_id = int(row['series_id']) if row['series_id'] else None
            rarity = int(row['rarity']) if row['rarity'] else None
            waifu = {
                'waifu_id': waifu_id,
                'series_id': series_id,
                'rarity': rarity
            }
            waifus.append(waifu)
            waifu_by_id[waifu_id] = waifu
            if series_id is not None:
                waifus_by_series[series_id].append(waifu_id)
            if rarity == 1:
                one_star_waifus.add(waifu_id)
    return waifus, waifu_by_id, waifus_by_series, one_star_waifus

async def main():
    config = Config.create()
    db = DatabaseService(config)
    await db.initialize()

    # Clear all banner-related tables
    async with db.connection_pool.acquire() as conn:
        await conn.execute("DELETE FROM banner_items;")
        await conn.execute("DELETE FROM banners;")
        #reset id start from 1 again
        await conn.execute("ALTER SEQUENCE banners_id_seq RESTART WITH 1;")
        print("Cleared all data from banner_items and banners tables.")

    # Load waifu data from CSV
    waifus, waifu_by_id, waifus_by_series, one_star_waifus = load_waifu_data()

    # Load new banner data
    with open(BANNER_JSON, 'r', encoding='utf-8') as f:
        banners = json.load(f)


    for banner in banners:
        # Compose waifu pool for this banner
        waifu_ids = set(banner.get('waifu_ids', []))
        series_waifu_ids = set()
        # Add waifus from series_ids
        if 'series_ids' in banner and banner['series_ids']:
            for sid in banner['series_ids']:
                series_waifu_ids.update(waifus_by_series.get(int(sid), []))
            waifu_ids.update(series_waifu_ids)

        # For limited banners, do NOT insert 1* waifus into banner_items (handled in summon logic)
        if banner['type'] == 'limited':
            waifu_ids = set(int(wid) for wid in waifu_ids if wid not in one_star_waifus)
        else:
            waifu_ids = set(int(wid) for wid in waifu_ids)

        # For rate-up banners, all waifus from waifu_ids and series_ids are rate-up
        rate_up_waifus = set()
        if banner['type'] == 'rate-up':
            rate_up_waifus = set(banner.get('waifu_ids', []))
            if 'series_ids' in banner and banner['series_ids']:
                for sid in banner['series_ids']:
                    rate_up_waifus.update(waifus_by_series.get(int(sid), []))
            rate_up_waifus = set(int(wid) for wid in rate_up_waifus)

        from datetime import datetime
        # Parse start_time and end_time to datetime objects
        dt_format = "%Y-%m-%d %H:%M:%S"
        start_time = banner['start_time']
        end_time = banner['end_time']
        if isinstance(start_time, str):
            start_time = datetime.strptime(start_time, dt_format)
        if isinstance(end_time, str):
            end_time = datetime.strptime(end_time, dt_format)
        # Store series_ids as a JSON string for DB compatibility
        banner_data = {
            'name': banner['name'],
            'type': banner['type'],
            'start_time': start_time,
            'end_time': end_time,
            'description': banner.get('description', ''),
            'is_active': banner.get('is_active', True),
            'series_ids': _json.dumps(banner.get('series_ids', []))
        }
        banner_id = await db.create_banner(banner_data)
        print(f"Inserted banner: {banner['name']} (ID: {banner_id})")

        # Insert banner items
        for wid in waifu_ids:
            rate_up = False
            if banner['type'] == 'rate-up' and wid in rate_up_waifus:
                rate_up = True
            await db.add_banner_item(banner_id, wid, rate_up=rate_up)

    # --- Add special banners ---
    import random
    from datetime import datetime, timedelta
    dt_format = "%Y-%m-%d %H:%M:%S"
    now = datetime.now()
    future = now + timedelta(days=30)

    # 1. Random Series Rate-Up Banner
    all_series_ids = list(waifus_by_series.keys())
    random_series_ids = random.sample(all_series_ids, min(5, len(all_series_ids)))
    series_waifu_ids = set()
    for sid in random_series_ids:
        series_waifu_ids.update(waifus_by_series[sid])
    banner_data = {
        'name': 'Random Series Rate-Up Banner',
        'type': 'rate-up',
        'start_time': now,
        'end_time': future,
        'description': f'Rate-up for 5 random anime series: {random_series_ids}',
        'is_active': True,
    }
    banner_id = await db.create_banner(banner_data)
    print(f"Inserted special banner: Random Series Rate-Up Banner (ID: {banner_id})")
    for wid in series_waifu_ids:
        await db.add_banner_item(banner_id, wid, rate_up=True)

    # 2. Random Character Rate-Up Banner (10 random 3★ and 10 random 2★)
    waifus_3star = [w['waifu_id'] for w in waifus if w['rarity'] == 3]
    waifus_2star = [w['waifu_id'] for w in waifus if w['rarity'] == 2]
    random_3star = random.sample(waifus_3star, min(10, len(waifus_3star)))
    random_2star = random.sample(waifus_2star, min(10, len(waifus_2star)))
    rate_up_waifus = set(random_3star + random_2star)
    all_waifu_ids = set(w['waifu_id'] for w in waifus)
    banner_data = {
        'name': 'Random Character Rate-Up Banner',
        'type': 'rate-up',
        'start_time': now,
        'end_time': future,
        'description': f'Rate-up for 10 random 3★ and 10 random 2★ characters.',
        'is_active': True,
        'series_ids': "[]",
    }
    banner_id = await db.create_banner(banner_data)
    print(f"Inserted special banner: Random Character Rate-Up Banner (ID: {banner_id})")
    for wid in rate_up_waifus:
        await db.add_banner_item(banner_id, wid, rate_up=True)
    await db.close()
    print("Banner tables reinitialized from banners.json.")

if __name__ == "__main__":
    asyncio.run(main())
