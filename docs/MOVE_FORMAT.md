# Unified Move Format

## Overview

All chess moves in the application are stored in a consistent format regardless of source (live games or imported PGNs).

## Standard Format

```json
[
  {"san": "e4", "uci": "e2e4"},
  {"san": "d5", "uci": "d7d5"},
  {"san": "exd5", "uci": "e4d5"}
]
```

Each move is an object with:
- `san`: Standard Algebraic Notation (human-readable, e.g., "e4", "Nf3", "O-O")
- `uci`: Universal Chess Interface format (machine-readable, e.g., "e2e4", "g1f3")

## Why Both Formats?

- **SAN**: For display to users (readable, standard notation)
- **UCI**: For communication with engines, Lichess API, and programmatic move validation

## Using move_utils.py

The `move_utils` module provides utilities to work with moves consistently:

### Normalizing Moves

Convert any format to the standard format:

```python
from core.move_utils import normalize_moves

# From UCI strings (live games from Lichess)
moves = ["e2e4", "d7d5", "e4d5"]
normalized = normalize_moves(moves)
# Result: [{"san": "e4", "uci": "e2e4"}, {"san": "d5", "uci": "d7d5"}, ...]

# Already in correct format (imported PGNs)
moves = [{"san": "e4", "uci": "e2e4"}]
normalized = normalize_moves(moves)
# Result: Same as input
```

### Extracting UCI/SAN

```python
from core.move_utils import to_uci_list, to_san_list

moves = [{"san": "e4", "uci": "e2e4"}, {"san": "d5", "uci": "d7d5"}]

# Get UCI strings for engine communication
uci_moves = to_uci_list(moves)
# Result: ["e2e4", "d7d5"]

# Get SAN strings for display
san_moves = to_san_list(moves)
# Result: ["e4", "d5"]
```

### Parsing from Different Sources

```python
from core.move_utils import MoveFormat
import chess.pgn
import io

# From space-separated UCI string (Lichess API)
lichess_moves = "e2e4 d7d5 e4d5"
moves = MoveFormat.parse_uci_string(lichess_moves)

# From PGN file
pgn_text = "[Event \"Game\"]\n\n1. e4 d5 2. exd5"
pgn = chess.pgn.read_game(io.StringIO(pgn_text))
moves = MoveFormat.parse_pgn_moves(pgn)
```

### Replaying Moves

```python
from core.move_utils import MoveFormat

moves = [{"san": "e4", "uci": "e2e4"}, {"san": "d5", "uci": "d7d5"}]

# Get final position after all moves
board = MoveFormat.replay_moves(moves)
print(board.fen())

# Get position after specific move
fen = MoveFormat.get_position_at_move(moves, move_index=0)
# Position after first move (e4)
```

## Integration Points

### Database Storage

The `GameStorage.save_game()` method automatically normalizes moves:

```python
# Any format works - it will be normalized
storage.save_game(game_id, {
    'moves': ["e2e4", "d7d5"],  # UCI strings from Lichess
    'game_type': 'live'
})

# Stored in database as:
# [{"san": "e4", "uci": "e2e4"}, {"san": "d5", "uci": "d7d5"}]
```

### API Endpoints

**Live Games** (`/api/game-state`):
- Receives UCI strings from Lichess: `"e2e4 d7d5"`
- Saves to database (automatically normalized)
- Returns both formats to frontend

**Imported PGNs** (`/api/parse-pgn`):
- Parses PGN using `MoveFormat.parse_pgn_moves()`
- Already in standard format
- Saves to database
- Returns to frontend

### Frontend

Frontend receives moves in standard format and can choose which to display:

```javascript
// From API response
const moves = [
  {san: "e4", uci: "e2e4"},
  {san: "d5", uci: "d7d5"}
];

// Display SAN to user
moves.forEach(move => console.log(move.san));  // "e4", "d5"

// Use UCI for chess.js
game.move(move.uci);
```

## Benefits

1. **Consistency**: Same format regardless of source (live game vs imported PGN)
2. **Flexibility**: Easy to extract either format when needed
3. **Type Safety**: Always know the structure of moves
4. **Analysis**: Both formats available for engine communication and user display
5. **Debugging**: Can see both notations side-by-side

## Migration

Old data with inconsistent formats is automatically normalized when accessed:
- UCI string arrays → converted to standard format
- Already in standard format → no change needed

The `core.move_utils.normalize_moves()` function handles all legacy formats transparently.
