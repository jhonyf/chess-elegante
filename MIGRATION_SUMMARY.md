# Database Model Migration Summary

## Changes Made

### Overview
Unified the separate `Game` and `PGN` models into a cleaner architecture with `ChessGame` and `LiveGameState` models.

## New Architecture

### 1. ChessGame Model (Unified)
**Table:** `chess_games`

**Purpose:** Stores all chess games (both live and imported) with move analysis

**Key Fields:**
- `id` - Primary key
- `user_id` - Foreign key to users (nullable for anonymous/shared games)
- `name` - User-defined or auto-generated game name
- `moves` - JSON array of moves in unified format: `[{"san": "e4", "uci": "e2e4"}, ...]` (required)
- `move_analysis` - JSON object with Stockfish + AI analysis
- `game_type` - 'live' or 'imported' (required, indexed)
- `result` - Game result ('1-0', '0-1', '1/2-1/2', '*')

**Unified Move Format:**
All moves are stored in a consistent format regardless of source:
```json
[
  {"san": "e4", "uci": "e2e4"},
  {"san": "d5", "uci": "d7d5"}
]
```
The `move_utils.py` module provides utilities to normalize any move format to this standard.

**Rich Metadata (Optional, available for all games):**
- `white_player`, `black_player` - Player names
- `white_elo`, `black_elo` - Player ratings
- `event`, `site`, `game_date` - Event information
- `opening`, `eco` - Opening information

**Benefits:**
- Single source of truth for all games
- No data redundancy (eliminated `pgn_text` and `headers` JSON blob)
- Unified analysis workflow
- Searchable metadata fields

### 2. LiveGameState Model (Ephemeral)
**Table:** `live_game_states`

**Purpose:** Tracks active Lichess game sessions (can be deleted after game ends)

**Key Fields:**
- `game_id` - Primary key and foreign key to chess_games
- `lichess_game_id` - Lichess game identifier
- `status` - 'started', 'finished', 'resigned', etc. (indexed)
- `player_color` - 'white' or 'black'
- `ai_level` - AI difficulty level (1-8)
- `current_fen` - Current board position

**Benefits:**
- Separates ephemeral session data from permanent game record
- Small table (only active games)
- Can be cleaned up after games finish
- Keeps core ChessGame table focused

## Data Flow

### Live Games
1. **Create:** New game creates `ChessGame` (game_type='live') + `LiveGameState`
2. **During Play:** Updates moves in `ChessGame`, updates FEN in `LiveGameState`
3. **Analysis:** Adds move_analysis to `ChessGame` as moves happen
4. **End Game:** Update `LiveGameState.status`, optionally delete `LiveGameState`
5. **Persist:** `ChessGame` persists forever with full analysis

### Imported Games
1. **Import:** Create `ChessGame` (game_type='imported') with metadata
2. **Analysis:** Optionally run analysis to populate `move_analysis`
3. **Persist:** `ChessGame` persists with all metadata

## Files Modified

1. **models.py**
   - Removed: `Game`, `PGN` models
   - Added: `ChessGame`, `LiveGameState` models
   - Updated: User relationships
   - Added: Documentation for unified move format

2. **game_storage_db.py**
   - Updated: `save_game()` to normalize moves using `move_utils.normalize_moves()`
   - Updated: `load_game()` to include live_state if present
   - Updated: `list_games()` with filtering by game_type and status
   - Added: `update_live_state()`, `delete_live_state()` methods
   - Removed: Old backward compatibility methods (not needed for new project)

3. **app.py**
   - Updated: `save_game()` calls to include `game_type='live'` and `lichess_game_id`
   - Updated: `parse_pgn()` to use `MoveFormat.parse_pgn_moves()`
   - Updated: `/api/games` to filter for live games only
   - Updated: `/api/pgns` to use `list_games(game_type='imported')` directly
   - Updated: `/api/pgn/<id>` to use `load_game()` and format response
   - Updated: `/api/save-pgn` to use `save_game()` with game_type='imported'
   - Updated: `/api/delete-pgn` to use `delete_game()` directly
   - Added: Import for `MoveFormat` from `move_utils`

4. **templates/games.html**
   - Updated: Changed `game.game_id` references to `game.id`

5. **migrate_to_db.py**
   - Updated: Table names in output messages

6. **move_utils.py** (NEW)
   - Added: Unified move format utilities
   - `normalize_moves()` - Convert any format to standard dict format
   - `to_uci_list()` - Extract UCI strings from any format
   - `to_san_list()` - Extract SAN strings from any format
   - `parse_uci_string()` - Parse space-separated UCI string
   - `parse_pgn_moves()` - Parse moves from chess.pgn.Game
   - `replay_moves()` - Replay moves on a board
   - `get_position_at_move()` - Get FEN at specific move

## Database Migration Steps

Since there's no existing data:

```bash
# 1. Drop existing tables (if any)
# Run this in psql or your database client:
DROP TABLE IF EXISTS pgns CASCADE;
DROP TABLE IF EXISTS games CASCADE;
DROP TABLE IF EXISTS users CASCADE;

# 2. Initialize Flask-Migrate and create new tables
flask db init
flask db migrate -m "Initial migration - unified chess game model"
flask db upgrade
```

For detailed migration instructions, see [Migrations Guide](docs/MIGRATIONS.md).

## Benefits of New Architecture

### 1. No Data Redundancy
- ❌ Removed `pgn_text` (can regenerate from moves + metadata)
- ❌ Removed `headers` JSON blob (normalized into structured fields)
- ✅ Single storage of moves and analysis

### 2. Clean Separation
- Core game data (ChessGame) is permanent
- Session data (LiveGameState) is ephemeral
- No NULL fields or confusing type discriminators

### 3. Flexible Queries
```python
# All games for a user
storage.list_games(user_id=user_id)

# Only live games
storage.list_games(game_type='live')

# Only imported games
storage.list_games(game_type='imported')

# Active games only
storage.list_games(status='started')
```

### 4. Better Performance
- Indexed fields: `game_type`, `status`, `user_id`
- Smaller tables (no redundant data)
- Optional joins for live state (only when needed)

### 5. Future Extensibility
- Easy to add new metadata fields
- Can export live games as importable format
- Can link live games to imported PGNs for deeper analysis
- Can add more game types (e.g., 'puzzle', 'lesson')

## Next Steps

1. Test game creation and gameplay
2. Test PGN import functionality
3. Verify backward compatibility with existing API endpoints
4. Consider adding indexes on frequently queried fields
5. Consider cleanup job to delete old LiveGameState records
