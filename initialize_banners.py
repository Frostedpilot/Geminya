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
        banner_data = {
            'name': banner['name'],
            'type': banner['type'],
            'start_time': start_time,
            'end_time': end_time,
            'description': banner.get('description', ''),
            'is_active': banner.get('is_active', True)
        }
        banner_id = await db.create_banner(banner_data)
        print(f"Inserted banner: {banner['name']} (ID: {banner_id})")

        # Insert banner items
        for wid in waifu_ids:
            rate_up = False
            if banner['type'] == 'rate-up' and wid in rate_up_waifus:
                rate_up = True
            await db.add_banner_item(banner_id, wid, rate_up=rate_up)

    await db.close()
    print("Banner tables reinitialized from banners.json.")

if __name__ == "__main__":
    asyncio.run(main())
