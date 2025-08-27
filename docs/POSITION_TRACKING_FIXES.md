# Position Tracking Fixes for Queue Loop Mode

## Issues Identified and Fixed

### 1. **Skip-to Position Handling in Queue Loop Mode**

**Problem**: The `skip_to` method only worked with the regular queue and didn't understand how to map user-visible positions to the actual queue/snapshot structure in loop queue mode.

**Solution**: Enhanced `skip_to` method with intelligent position mapping:

```python
async def skip_to(self, guild_id: int, position: int) -> bool:
    mode = self._queue_modes[guild_id]

    if mode == QueueMode.LOOP_QUEUE:
        # Build combined queue view (what user sees)
        regular_queue = list(queue)
        snapshot = self._queue_snapshots.get(guild_id, [])
        snapshot_position = self._snapshot_positions.get(guild_id, 0)

        if regular_queue:
            combined_queue = regular_queue + snapshot[snapshot_position:]
        else:
            combined_queue = snapshot[snapshot_position:] + snapshot[:snapshot_position]

        # Map user position to actual queue/snapshot structure
        if index < len(regular_queue):
            # Skip within regular queue
        else:
            # Skip into snapshot with proper position calculation
            new_position = (snapshot_position + snapshot_index) % len(snapshot)
```

### 2. **Resume After Disconnection Position Sync**

**Problem**: When the bot disconnects and reconnects, the current track and snapshot position might become out of sync.

**Solution**: Enhanced resume logic to maintain position consistency:

```python
async def _try_resume_playback_after_reconnect(self, guild_id: int):
    # In loop queue mode, verify current track matches snapshot position
    if mode == QueueMode.LOOP_QUEUE and current_track and not queue:
        snapshot = self._queue_snapshots.get(guild_id, [])
        position = self._snapshot_positions.get(guild_id, 0)

        # Sync position if current track doesn't match expected snapshot position
        if not (position < len(snapshot) and
                snapshot[position].track.display_name == current_track.track.display_name):
            # Find and sync to correct position
            for i, item in enumerate(snapshot):
                if item.track.display_name == current_track.track.display_name:
                    self._snapshot_positions[guild_id] = i
                    break
```

### 3. **Position Management Methods**

**Added**: New utility method for better position control:

```python
def set_snapshot_position(self, guild_id: int, position: int):
    """Set the current position in the snapshot queue with bounds checking."""
    if guild_id in self._queue_snapshots:
        snapshot_len = len(self._queue_snapshots[guild_id])
        if snapshot_len > 0:
            self._snapshot_positions[guild_id] = max(0, min(position, snapshot_len - 1))
```

## Position Mapping Logic

### Display Queue vs Internal Structure

**What User Sees (Display Queue)**:

```
1. New Song A        <- Regular queue item 0
2. New Song B        <- Regular queue item 1
3. Snapshot Song C   <- Snapshot position 2
4. Snapshot Song D   <- Snapshot position 3
5. Snapshot Song A   <- Snapshot position 0 (wrapped)
6. Snapshot Song B   <- Snapshot position 1 (wrapped)
```

**Internal Structure**:

- Regular Queue: `[New Song A, New Song B]`
- Snapshot: `[Snapshot Song A, Snapshot Song B, Snapshot Song C, Snapshot Song D]`
- Snapshot Position: `2` (currently at Snapshot Song C)

### Skip-to Position Mapping

When user runs `/spotify_skip_to position:4`:

1. **Convert to 0-indexed**: `position = 4 - 1 = 3`
2. **Check if in regular queue**: `3 >= 2` (not in regular queue)
3. **Calculate snapshot index**: `snapshot_index = 3 - 2 = 1`
4. **Calculate new snapshot position**: `new_position = 2 + 1 = 3`
5. **Result**: Skip to Snapshot Song D (position 3 in snapshot)

### Circular Handling (No Regular Queue)

When there are no regular queue items:

**Display**: `[Snapshot C, Snapshot D, Snapshot A, Snapshot B]` (from position 2)

Skip to position 3 (Snapshot A):

1. **Snapshot index**: `3 - 1 = 2` (since no regular queue)
2. **New position**: `(2 + 2) % 4 = 0` (circular wrap)
3. **Result**: Skip to Snapshot Song A (position 0 in snapshot)

## Testing Scenarios

### ✅ **Tested and Working**:

1. **Regular queue + snapshot skip**: ✓
2. **Pure snapshot circular skip**: ✓
3. **Resume after disconnect**: ✓
4. **Position bounds checking**: ✓
5. **Normal mode compatibility**: ✓

### 🔍 **Edge Cases Handled**:

- Empty queues and snapshots
- Out-of-bounds position requests
- Snapshot position sync after reconnection
- Mixed regular queue and snapshot skipping
- Circular position wrapping

## Benefits

1. **Accurate Position Tracking**: Skip-to now works correctly in all queue modes
2. **Consistent State**: Position remains accurate after disconnections
3. **User-Friendly**: Skip positions match what users see in queue display
4. **Robust**: Handles edge cases and maintains state integrity

The position tracking system now properly handles all scenarios including skip operations, disconnection/resume, and maintains consistency between the displayed queue order and internal state management.
