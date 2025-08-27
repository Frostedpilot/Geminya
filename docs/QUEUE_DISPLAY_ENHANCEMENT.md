# Queue Display Enhancement Summary

## Problem Solved

The Spotify queue display command (`/spotify_queue`) now properly shows the snapshot queue in queue loop mode, with correct positioning relative to the currently playing song.

## Key Enhancements

### 1. Enhanced Music Service Methods

- **`get_snapshot_position(guild_id)`**: Returns the current position in the snapshot queue
- **Enhanced queue retrieval logic**: The queue display now intelligently combines regular queue + snapshot queue based on current mode

### 2. Smart Queue Display Logic

#### Normal Mode

- Shows the regular queue as before

#### Queue Loop Mode

- **Shows snapshot queue with proper positioning**
- **Combines new songs + remaining snapshot**:
  - New songs (regular queue) are shown first
  - Followed by remaining snapshot tracks from current position
  - If no new songs, shows full loop: remaining snapshot + already played tracks

#### Example Queue Loop Display:

```
Queue: [New Song 1, New Song 2, Snapshot Song 3, Snapshot Song 4, Snapshot Song 1, Snapshot Song 2]
         ^-- New songs play first    ^-- Remaining from current position  ^-- Loop back
```

### 3. Enhanced Queue Information Display

#### Regular Mode:

```
⚙️ Settings
Mode: Normal 🔀
Volume: 50%
```

#### Queue Loop Mode:

```
⚙️ Settings
Mode: Loop Queue 🔀
Volume: 50%
Snapshot: 4 tracks
New songs: 2
Snapshot pos: 3/4
```

### 4. Real-time Updates

- **Refresh button** now properly updates the display based on current mode
- **Accurate positioning** maintained as songs play through the snapshot
- **Dynamic queue composition** that reflects the actual playback order

## Technical Implementation

### Queue Retrieval Logic:

```python
if mode == QueueMode.LOOP_QUEUE:
    snapshot = get_queue_snapshot(guild_id)
    regular_queue = get_queue(guild_id)
    position = get_snapshot_position(guild_id)

    if regular_queue:
        # New songs + remaining snapshot
        display_queue = regular_queue + snapshot[position:]
    else:
        # Full loop: remaining + already played
        display_queue = snapshot[position:] + snapshot[:position]
```

### Visual Indicators:

- **"Queue (Loop Mode)"** title for clarity
- **Shuffle indicator (🔀)** when queue is shuffled
- **Detailed status info** showing snapshot size, new songs count, and current position

## Benefits

1. **Accurate Queue Representation**: Users see exactly what will play next
2. **Loop Mode Clarity**: Clear indication of snapshot vs new songs
3. **Position Awareness**: Shows current progress through the snapshot
4. **Consistent Experience**: Works seamlessly with shuffle and mode changes
5. **Real-time Updates**: Refresh button keeps display current

## Usage

Users can now:

- See the actual playback order in queue loop mode
- Understand where they are in the snapshot progression
- Distinguish between new songs and looped songs
- Track their position in the loop cycle

The queue display now provides a complete and accurate view of what will play next, regardless of the active playback mode!
