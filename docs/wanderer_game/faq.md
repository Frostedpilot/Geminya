# FAQ, Extension Points, and Troubleshooting

## Frequently Asked Questions

**Q: How do I add new expeditions or encounters?**
- Add new entries to `data/expeditions/base_expeditions.json` (for templates) or `data/expeditions/encounters.json` (for encounters). Use the existing format as a guide.

**Q: How do I add new characters?**
- Add rows to `data/character_final.csv` with the required fields. See the Character model for details.

**Q: How are affinity buffs/nerfs calculated?**
- The system uses a multiplicative model: each favored match multiplies by 1.2, each disfavored by 0.6 (clamped).

**Q: Can I change the number of expedition slots?**
- Yes, set the `max_expedition_slots` parameter when initializing `ExpeditionManager`.

**Q: How do I customize loot probabilities or add new items?**
- Edit the item configs in `LootGenerator` or extend the loot table logic.

## Extension Points
- **New Encounter Types**: Extend the `EncounterType` enum and update `ExpeditionResolver` logic.
- **New Modifiers**: Add to `ModifierType` and handle in `_apply_modifier`.
- **Custom Stat/Outcome Logic**: Override or extend calculation utilities in `utils/calculations.py`.
- **UI Integration**: The backend is designed for Discord UI, but can be adapted for other frontends.

## Troubleshooting
- **Data Not Loading**: Check file paths and formats. Use `DataManager.load_all_data()` and review console output for errors.
- **Character Not Found**: Ensure waifu_id and series_id are unique and present in the CSV.
- **Unexpected Results**: Review affinity and stat calculations, and check for recent changes in calculation logic.

---


For more details, see the other documentation files in this folder.

**See also:** [Discord Cog & Service Integration Guide](integration.md) for details on how the Discord bot and backend service interact, and how to extend or debug the integration layer.
