# Spotify Playback Mode Implementation

## Overview

This implementation adds advanced playback mode functionality to the Geminya Discord bot's Spotify integration, including queue loop, song loop, and queue shuffle capabilities.

## Features Implemented

### 1. Queue Loop Mode (`QueueMode.LOOP_QUEUE`)

- **Functionality**: Creates a snapshot of the current queue and loops through it infinitely
- **Behavior**:
  - When enabled, takes a snapshot of current queue + currently playing track
  - Plays through the snapshot in order
  - When snapshot is exhausted, starts over from the beginning
  - New songs added to queue are played first, then returns to snapshot loop
  - Maintains separate shuffle state for the snapshot

### 2. Song Loop Mode (`QueueMode.LOOP_TRACK`)

- **Functionality**: Repeats the currently playing song indefinitely
- **Behavior**:
  - Loops the current track without advancing the queue
  - Queue remains intact for when loop mode is disabled

### 3. Queue Shuffle (`QueueMode.SHUFFLE`)

- **Functionality**: Randomizes the order of tracks in the queue
- **Behavior**:
  - Shuffles the current queue when entering shuffle mode
  - In queue loop mode, shuffles the snapshot queue instead
  - Maintains separate shuffle states for normal queue and snapshot queue

### 4. Advanced Queue Management

- **Smart State Handling**: Separate tracking of shuffle states for normal and snapshot queues
- **Mode Transitions**: Automatic cleanup and setup when switching between modes
- **Queue Preservation**: Adding new tracks resets shuffle in normal mode but preserves queue loop snapshot

## Command Interface

### `/spotify_playback_mode`

#### Parameters:

- `mode` (optional): Choose playback mode

  - **Normal**: Play queue in order
  - **Song Loop**: Repeat current song
  - **Queue Loop**: Loop through queue snapshot
  - **Shuffle Mode**: Randomize queue order

- `shuffle` (optional): Boolean to shuffle the current queue

#### Usage Examples:

```
/spotify_playback_mode
```

Shows current playback mode and shuffle status

```
/spotify_playback_mode mode:Queue Loop
```

Enables queue loop mode and creates a snapshot

```
/spotify_playback_mode shuffle:True
```

Shuffles the current queue (or snapshot if in queue loop mode)

```
/spotify_playback_mode mode:Normal shuffle:True
```

Sets normal mode and shuffles the queue

## Technical Implementation

### Core Components

#### Enhanced Music Service (`services/music_service.py`)

**New Fields Added:**

```python
self._queue_snapshots: Dict[int, List[QueueItem]] = {}  # guild_id -> snapshot
self._snapshot_positions: Dict[int, int] = {}  # guild_id -> position in snapshot
self._is_shuffled: Dict[int, bool] = {}  # guild_id -> shuffle state
self._snapshot_shuffled: Dict[int, bool] = {}  # guild_id -> snapshot shuffle state
```

**Key Methods:**

1. **`set_queue_mode(guild_id, mode)`**

   - Handles mode transitions
   - Creates/clears snapshots as needed
   - Resets shuffle states appropriately

2. **`_create_queue_snapshot(guild_id)`**

   - Creates snapshot from current track + queue
   - Preserves shuffle state if enabled

3. **`shuffle_queue(guild_id)`**

   - Shuffles normal queue or snapshot depending on mode
   - Updates appropriate shuffle state flags

4. **`_get_next_track(guild_id)`** (Enhanced)

   - Handles all queue modes with proper logic
   - Manages snapshot position tracking
   - Implements shuffle logic for different modes

5. **`is_queue_shuffled(guild_id)`**
   - Returns appropriate shuffle state based on current mode

#### Command Implementation (`cogs/commands/spotify.py`)

**New Command:**

- `@app_commands.command(name="spotify_playback_mode")`
- Supports both mode setting and queue shuffling
- Provides comprehensive status display
- User-friendly embed with mode descriptions

### Queue Mode Logic

#### Normal Mode (`QueueMode.NORMAL`)

```
Queue: [A, B, C, D] -> Play A -> Queue: [B, C, D] -> Play B -> ...
```

#### Song Loop Mode (`QueueMode.LOOP_TRACK`)

```
Current: A, Queue: [B, C, D] -> Play A -> Play A -> Play A -> ...
```

#### Queue Loop Mode (`QueueMode.LOOP_QUEUE`)

```
Snapshot: [A, B, C, D] -> Play A, B, C, D -> Start over: A, B, C, D -> ...
New songs: [E] + Snapshot: [A, B, C, D] -> Play E -> Resume snapshot
```

#### Shuffle Mode (`QueueMode.SHUFFLE`)

```
Queue: [A, B, C, D] -> Shuffle -> Queue: [C, A, D, B] -> Play in new order
```

### State Management

The implementation carefully manages state transitions:

1. **Mode Changes**:

   - Entering `LOOP_QUEUE` creates snapshot
   - Leaving `LOOP_QUEUE` clears snapshot
   - Shuffle states reset appropriately

2. **Adding Tracks**:

   - Normal mode: Resets shuffle state (new content should be in order)
   - Queue loop mode: Preserves snapshot, new tracks play first

3. **Queue Operations**:
   - Clear queue resets normal shuffle state
   - Snapshot shuffle state preserved for queue loop mode

## Benefits

1. **User Experience**: Intuitive command interface with clear status display
2. **Flexibility**: Multiple playback modes to suit different listening preferences
3. **Robustness**: Proper state management prevents inconsistent behavior
4. **Integration**: Seamlessly integrates with existing Spotify functionality

## Testing

The implementation includes comprehensive state management and has been tested for:

- Mode transitions
- Shuffle state handling
- Queue operations
- Edge cases (empty queues, mode changes during playback)

## Future Enhancements

Potential future improvements:

- Crossfade support between loops
- Custom loop counts (e.g., repeat 3 times)
- Queue history navigation
- Playlist-specific loop modes
