# Banner Configuration Documentation

## New Banner Cost and Currency System

The banner system now supports custom cost and currency types for each banner.

### New Fields

#### `cost` (integer, optional)
- Cost per summon for this banner
- Default: 10 (if not specified)
- Examples: 10, 15, 50, 1

#### `currency_type` (string, optional)  
- Currency type to use for this banner
- Default: "sakura_crystals" (if not specified)
- Options:
  - `"sakura_crystals"` - Standard crystals (💎)
  - `"quartzs"` - Premium currency (💠)
  - `"daphine"` - Special awakening currency (🦋)

### Examples

```json
{
  "name": "Standard Banner",
  "cost": 10,
  "currency_type": "sakura_crystals"
}
```

```json
{
  "name": "Premium Anniversary Banner", 
  "cost": 50,
  "currency_type": "quartzs"
}
```

```json
{
  "name": "Awakening Special Banner",
  "cost": 1,
  "currency_type": "daphine"
}
```

### Backward Compatibility

- If `cost` or `currency_type` are not specified, defaults are used
- Existing banners without these fields will use: cost=10, currency_type="sakura_crystals"
- Non-banner summons (when no banner_id is specified) still use the hardcoded SUMMON_COST (10 sakura_crystals)

### Implementation Notes

- The WaifuService automatically handles currency validation and deduction
- Error messages show the correct currency type and amount
- Command responses include both the currency used and remaining amounts
- All three currency types are supported: sakura_crystals, quartzs, daphine