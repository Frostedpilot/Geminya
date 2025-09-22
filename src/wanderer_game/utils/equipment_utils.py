import os
import pandas as pd
import json as _json
# --- Affinity Value Pool Loader ---
def load_affinity_pools():
    """
    Loads and caches all unique values for series_id, archetype, elemental, and genre from data files.
    Returns a dict: { 'series_id': set, 'archetype': set, 'elemental': set, 'genre': set }
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../data'))
    pools = {'series_id': set(), 'archetype': set(), 'elemental': set(), 'genre': set()}
    anime_df = pd.read_csv(os.path.join(base_dir, 'anime_final.csv'))
    for _, row in anime_df.iterrows():
        series_id = row.get('series_id')
        if pd.notna(series_id):
            pools['series_id'].add(series_id)
        genre = row.get('genres')
        if pd.notna(genre):
            genres = genre.split("|")
            for g in genres:
                g = g.strip()
                if g:
                    pools['genre'].add(g)
    # --- archetypes.json: archetype names ---
    arch_json = os.path.join(base_dir, 'archetypes.json')
    try:
        with open(arch_json, encoding='utf-8') as f:
            data = _json.load(f)
            for a in data.get('archetypes', []):
                name = a.get('name')
                if name:
                    pools['archetype'].add(name)
    except Exception as e:
        pass
    # --- characters_with_stats.csv: elemental_type ---
    chars_pd = pd.read_csv(os.path.join(base_dir, 'character_final.csv'))
    for _, row in chars_pd.iterrows():
        elem = row.get('elemental_type')
        elems = _json.loads(elem)
        for e in elems:
            pools['elemental'].add(e)
    return {k: sorted(list(v)) for k, v in pools.items()}
_AFFINITY_POOLS =  load_affinity_pools()
def format_equipment_compact(equipment) -> str:
    """
    Return a compact, single-line summary of the equipment for use in lists.
    Accepts a dict (from DB), not an Equipment object.
    """
    import json
    # Main stat (short)
    main = equipment.get('main_effect')
    if isinstance(main, str):
        try:
            main = json.loads(main)
        except (ValueError, TypeError, json.JSONDecodeError):
            main = None
    if main:
        main_type = main.get('type')
        if main_type == 'affinity_add':
            main_str = f"{main.get('category', '')} ({main.get('value', '')})"
        elif main_type == 'loot_pool_bonus':
            main_str = f"Loot+{main.get('value', '')}"
        elif main_type == 'final_roll_bonus':
            main_str = f"Roll+{main.get('value', '')}"
        elif main_type == 'encounter_count_add':
            main_str = f"Enc+{main.get('value', '')}"
        else:
            main_str = str(main_type)
    else:
        main_str = "None"

    # Sub stats (short)
    sub_slots = equipment.get('sub_slots', [])
    substat_strs = []
    stat_names = ["atk", "def", "spd", "int", "luk", "vit", "mag"]
    for slot in sub_slots:
        if slot.get('is_unlocked', False):
            effect = slot.get('effect')
            if isinstance(effect, str):
                try:
                    effect = json.loads(effect)
                except (ValueError, TypeError, json.JSONDecodeError):
                    effect = None
            if effect:
                t = effect.get('type')
                value = effect.get('value', '')
                stat = effect.get('stat', '')
                if t == 'stat_check_bonus':
                    substat_strs.append(f"{stat}+{value}")
                elif t == 'final_stat_check_bonus':
                    substat_strs.append(f"{stat}+{value}f")
                else:
                    substat_strs.append(str(t))
        else:
            substat_strs.append("🔒")
    substat_summary = ", ".join(substat_strs) if substat_strs else "-"

    eq_id = equipment.get('id', None)
    id_str = f"#{eq_id} " if eq_id is not None else ""
    #truncate to 100 letters
    if len(main_str) > 100:
        main_str = main_str[:97] + "..."
    return f"{id_str}[{main_str}] | Subs: {substat_summary}"

def format_equipment_full(equipment) -> str:
    """
    Return a formatted string describing the entire equipment, including main effect and all substats.
    Accepts a dict (from DB), not an Equipment object.
    """
    import json
    lines = []
    # Main effect
    main = equipment.get('main_effect')
    if isinstance(main, str):
        try:
            main = json.loads(main)
        except (ValueError, TypeError, json.JSONDecodeError):
            main = None
    lines.append("**Main Stat:**")
    lines.append(f"- {format_equipment_effect_detail(main)}")
    # Sub stats
    sub_slots = equipment.get('sub_slots', [])
    if sub_slots:
        lines.append("**Sub Stats:**")
        for idx, slot in enumerate(sub_slots, 1):
            if slot.get('is_unlocked', False):
                effect = slot.get('effect')
                if isinstance(effect, str):
                    try:
                        effect = json.loads(effect)
                    except (ValueError, TypeError, json.JSONDecodeError):
                        effect = None
                lines.append(f"  {idx}. {format_equipment_effect_detail(effect)}")
            else:
                lines.append(f"  {idx}. (Locked)")
    else:
        lines.append("**Sub Stats:** None")
    return "\n".join(lines)
def get_main_stat_names():
    """
    Return a list of human-readable names for all possible main stat effects.
    """
    return [
        "Affinity Add (Favored Element)",
        "Loot Pool Bonus",
        "Final Roll Bonus",
        "Encounter Count Add"
    ]

def get_sub_stat_names():
    """
    Return a list of human-readable names for all possible sub stat effects.
    """
    return [
        "Stat Check Bonus",
        "Final Stat Check Bonus"
    ]

def format_equipment_effect_detail(effect) -> str:
    """
    Return a detailed string for a given EncounterModifier effect.
    Accepts a dict (from DB), not an EncounterModifier object.
    """
    if not effect:
        return "None"
    # If effect is a string, try to parse as JSON
    import json
    if isinstance(effect, str):
        try:
            effect = json.loads(effect)
        except (ValueError, TypeError, json.JSONDecodeError):
            return str(effect)
    t = effect.get('type')
    if t == 'affinity_add':
        return f"Affinity Add: Favored {effect.get('category', '')} ({effect.get('value', '')})"
    elif t == 'loot_pool_bonus':
        return f"Loot Pool Bonus: +{effect.get('value', '')} loot"
    elif t == 'final_roll_bonus':
        return f"Final Roll Bonus: +{effect.get('value', '')}"
    elif t == 'encounter_count_add':
        return f"Encounter Count Add: +{effect.get('value', '')} encounter(s)"
    elif t == 'stat_check_bonus' or t == 'final_stat_check_bonus':
        value = effect.get('value', '')
        stat = effect.get('stat', '')
        is_final = (t == 'final_stat_check_bonus')
        label = "Final Stat Check Bonus" if is_final else "Stat Check Bonus"
        if stat == 'all':
            return f"{label}: +{value} to all" + (" (final)" if is_final else "")
        else:
            return f"{label}: +{value} to {stat}" + (" (final)" if is_final else "")
    else:
        return str(effect)
import random
from src.wanderer_game.models.encounter import EncounterModifier, ModifierType


def random_main_stat_modifier():
    """
    Generate a random EncounterModifier suitable for a main stat.
    Only ModifierTypes allowed for main stat are included here.
    (Use from models.equipment for random_equipment_no_subslots)
    """
    main_effect_types = [
        ModifierType.AFFINITY_ADD,
        ModifierType.LOOT_POOL_BONUS,
        ModifierType.ENCOUNTER_COUNT_ADD
    ]
    weights = [90,5,5]
    mod_type = random.choices(main_effect_types, weights=weights)[0]
    affinity = None
    category = None
    value = None
    stat = None
    if mod_type == ModifierType.AFFINITY_ADD:
        affinity = random.choice(["favored"])
        category = random.choice(list(_AFFINITY_POOLS.keys()))
        value = random.choice(_AFFINITY_POOLS[category])
    elif mod_type == ModifierType.LOOT_POOL_BONUS:
        value = random.randint(10, 20)
    elif mod_type == ModifierType.ENCOUNTER_COUNT_ADD:
        value = random.randint(1, 3)
    return EncounterModifier(
        type=mod_type,
        affinity=affinity,
        category=category,
        value=value,
        stat=stat
    )

def random_sub_stat_modifier():
    """
    Generate a random EncounterModifier suitable for a sub stat.
    Only ModifierTypes allowed for sub stat are included here.
    (Use from models.equipment for random_equipment_no_subslots)
    """
    sub_effect_types = [
        ModifierType.STAT_CHECK_BONUS,
        ModifierType.FINAL_STAT_CHECK_BONUS
    ]
    mod_type = random.choice(sub_effect_types)
    affinity = None
    category = None
    value = None
    stat = None
    if mod_type == ModifierType.STAT_CHECK_BONUS:
        stat = random.choice(["atk", "spr", "spd", "int", "lck", "vit", "mag", "all"])
        value = random.randint(5, 20)
        if stat == "all":
            value = value//2
    elif mod_type == ModifierType.FINAL_STAT_CHECK_BONUS:
        stat = random.choice(["atk", "spr", "spd", "int", "lck", "vit", "mag", "all"])
        value = random.randint(12, 48)
        if stat == "all":
            value = value//2
    return EncounterModifier(
        type=mod_type,
        affinity=affinity,
        category=category,
        value=value,
        stat=stat
    )