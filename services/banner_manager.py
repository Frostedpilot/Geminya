"""Server-side BannerManager for handling banners and their waifu pools."""

from typing import List, Dict, Optional, Union

class BannerManager:
    def __init__(self):
        # Example waifu pools for each series_id (in production, load from config or update as needed)
        self.series_waifu_pools = {
            101: [301, 302, 303, 304],  # waifu_ids for series_id 101
            102: [401, 402, 403],       # waifu_ids for series_id 102
        }
        self.banners = {
            1: {
                "id": 1,
                "type": "series",
                "name": "Attack on Titan Series Banner",
                "series_id": 101,
                "waifu_ids": self.series_waifu_pools[101],
                "description": "Summon waifus from Attack on Titan!",
                "image_url": None,
            },
            2: {
                "id": 2,
                "type": "character-list",
                "name": "Limited Summer Banner",
                "waifu_ids": [201, 202, 203],
                "description": "Limited summer waifus only!",
                "image_url": None,
            },
        }

    def get_all_banners(self) -> List[Dict]:
        return list(self.banners.values())

    def get_banner_by_id(self, banner_id: int) -> Optional[Dict]:
        return self.banners.get(banner_id)

    def get_waifu_ids_for_banner(self, banner: Dict) -> List[int]:
        return banner.get("waifu_ids", [])
