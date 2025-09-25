# Implementing 6-Star Characters: Code Update Plan

## 1. Character Data Model
- **File(s):** `base.py`, any model files in `src/wanderer_game/models/`
- **Action:**  
  - Update the character/star-level schema to support a 6th star.
  - Ensure star level is not capped at 5 in any validation or property.

## 2. Upgrade Logic
- **File(s):** `cogs/commands/waifu_academy.py` (or wherever star upgrades are handled)
- **Action:**  
  - Add logic to allow upgrading from 5★ to 6★ only via a manual/admin command or special UI.
  - Require both the rare expedition item and 300 shards for the upgrade.
  - Block normal upgrade flow from reaching 6★.

## 3. Item & Shard Handling
- **File(s):** `services/database.py`, `src/wanderer_game/systems/expedition_resolver.py`, `src/wanderer_game/utils/equipment_utils.py`
- **Action:**  
  - Add the new rare item to the item database and expedition loot tables.
  - Ensure shard deduction and item consumption are atomic and validated.

## 4. Expedition Rewards
- **File(s):** `src/wanderer_game/systems/expedition_resolver.py`, `data/expeditions/encounters.json`
- **Action:**  
  - Add the rare 6★ upgrade item as a possible (very rare) expedition reward.

## 5. UI/UX & Discord Commands
- **File(s):** `cogs/commands/waifu_academy.py`, `cogs/commands/expeditions.py`
- **Action:**  
  - Update any UI or command that displays star levels to show 6★.
  - Add admin or special command for manual 6★ upgrade.
  - Add feedback for insufficient shards or missing item.

## 6. Validation & Edge Cases
- **File(s):** All above, plus any test or validation logic.
- **Action:**  
  - Ensure no auto-upgrade to 6★ is possible.
  - Validate that only eligible characters (e.g., maxed 5★) can be upgraded.
  - Add tests for upgrade, item consumption, and error cases.

## 7. Documentation & Data
- **File(s):** `README.md`, `docs/`, `data/`
- **Action:**  
  - Document the 6★ upgrade process for admins and users.
  - Add the new item to any item lists or drop tables.

---

**Summary Table:**

| Area                | File(s) / Folder(s)                                 | What to Update                                  |
|---------------------|-----------------------------------------------------|-------------------------------------------------|
| Data Model          | `base.py`, models                                   | Allow 6★, update star cap                       |
| Upgrade Logic       | `waifu_academy.py`, upgrade handlers                | Manual 6★ upgrade, require item + shards        |
| Item Handling       | `services/database.py`, utils, loot                 | Add rare item, shard logic                      |
| Expedition Rewards  | `expedition_resolver.py`, `encounters.json`         | Add rare item to loot                           |
| UI/UX & Commands    | `waifu_academy.py`, `expeditions.py`                | Show 6★, add admin/manual upgrade               |
| Validation/Testing  | All above, tests                                    | Prevent auto 6★, test all flows                 |
| Docs & Data         | `README.md`, `docs/`, `data/`                       | Document process, update item lists             |

---

**Next Steps:**  
- Update the data model and upgrade logic first.
- Add the rare item to expeditions and item handling.
- Implement the manual/admin upgrade command.
- Update UI and documentation.
