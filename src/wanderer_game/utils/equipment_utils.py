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
            return f"{label}: +{value} to ALL" + (" (final)" if is_final else "")
        else:
            return f"{label}: +{value} to {stat.upper()}" + (" (final)" if is_final else "")
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
    mod_type = random.choice(main_effect_types)
    affinity = None
    category = None
    value = None
    stat = None
    if mod_type == ModifierType.AFFINITY_ADD:
        affinity = random.choice(["favored"])
        category = random.choice(["elemental"])
        value = random.choice(["fire", "water", "earth", "wind"])
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
    elif mod_type == ModifierType.FINAL_STAT_CHECK_BONUS:
        stat = random.choice(["atk", "spr", "spd", "int", "lck", "vit", "mag", "all"])
        value = random.randint(12, 48)
    return EncounterModifier(
        type=mod_type,
        affinity=affinity,
        category=category,
        value=value,
        stat=stat
    )