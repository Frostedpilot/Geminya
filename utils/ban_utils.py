import json
import os

BANNED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'banned.json')

def is_user_banned(user_id: int) -> bool:
    """
    Check if a Discord user ID is banned by looking in banned.json.
    Args:
        user_id (int): Discord user ID to check.
    Returns:
        bool: True if banned, False otherwise.
    """
    try:
        with open(BANNED_FILE, 'r', encoding='utf-8') as f:
            banned_ids = json.load(f)
        return str(user_id) in banned_ids or user_id in banned_ids
    except Exception:
        return False
