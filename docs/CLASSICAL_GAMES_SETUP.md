# Classical Games Setup Guide

This guide explains how classical chess games are integrated into the Chess Elegante learning pages.

## Overview

The openings learning page (`/openings`) now displays links to 3 classical games for each opening. These are curated master games stored in the database that demonstrate the opening's key ideas.

## Architecture

### 1. **PGN File** (`seed_data/classical_games.pgn`)
   - Contains 36 classical games (3 per opening)
   - 12 openings covered:
     * Italian Game
     * Ruy Lopez
     * Sicilian Defense
     * French Defense
     * Queen's Gambit
     * King's Indian Defense
     * London System
     * Caro-Kann Defense
     * English Opening
     * Scandinavian Defense
     * Nimzo-Indian Defense
     * Catalan Opening

### 2. **Seeding Script** (`seed_classical_games.py`)
   - Parses the PGN file using `chess.pgn`
   - Uses `MoveFormat.parse_pgn_moves()` for consistent move formatting
   - Generates **deterministic UUIDs** based on game metadata (White, Black, Event, Date)
   - Inserts games into the `chess_games` table with `is_curated=True`
   - Skips existing games on re-runs (idempotent)

**Running the seeder:**
```bash
# Make sure DATABASE_URL is set
export DATABASE_URL="postgresql://..."

# Run the seeder
python seed_classical_games.py

# View all curated games
python seed_classical_games.py --list
```

### 3. **Database Storage**
   - Games stored in `chess_games` table
   - Fields used:
     * `id`: Deterministic UUID (same game always has same ID)
     * `is_curated`: TRUE for classical games
     * `opening`: Opening name (e.g., "Italian Game")
     * `white_player`, `black_player`: Player names
     * `event`, `site`, `game_date`: Event metadata
     * `moves`: Normalized move list `[{"san": "e4", "uci": "e2e4"}, ...]`
     * `eco`: ECO code
     * `result`: Game result
     * `white_elo`, `black_elo`: Player ratings

### 4. **API Endpoint**
   - **Route**: `GET /api/curated-pgns?opening=<opening_name>`
   - **Purpose**: Fetch curated games filtered by opening
   - **Response**: List of game metadata
   - **Implementation**: `game_storage_db.py:get_curated_games()`

### 5. **Frontend Integration**

#### HTML Template (`templates/openings.html`)
Each opening card includes a "Classical Games" section:
```html
<div class="classical-games">
    <h4>Classical Games</h4>
    <p class="classical-games-intro">Study these master games to see the Italian Game in action:</p>
    <div class="classical-games-links" data-opening="Italian Game">
        <span class="loading-games">Loading games...</span>
    </div>
</div>
```

#### JavaScript (`static/js/learn.js`)
- `loadClassicalGames()` function runs on page load
- Fetches games from `/api/curated-pgns?opening=<name>`
- Renders up to 3 game links per opening
- Links point to `/analyze/<game_id>`

#### CSS (`static/css/learn.css`)
- Styled classical game links with hover effects
- Clean, modern card-based design
- Loading and error states

### 6. **Game Analysis Page** (`/analyze/<game_id>`)
   - Existing route already supports this pattern
   - Renders `game.html` with `pgn_id` parameter
   - Works with both user games and curated games
   - Curated games are read-only (no user ownership)

## Deterministic UUIDs

The seeding script generates consistent UUIDs using MD5 hashing:

```python
def generate_game_uuid(white, black, event, date):
    unique_str = f"{white}|{black}|{event}|{date}"
    hash_obj = hashlib.md5(unique_str.encode())
    hash_hex = hash_obj.hexdigest()
    return f"{hash_hex[:8]}-{hash_hex[8:12]}-{hash_hex[12:16]}-{hash_hex[16:20]}-{hash_hex[20:32]}"
```

**Benefits:**
- Same game always gets the same ID
- Can reference games directly in HTML/docs
- Re-running seeder won't create duplicates
- Enables direct linking: `/analyze/<static-uuid>`

## Adding More Classical Games

1. **Add PGN to `seed_data/classical_games.pgn`**
   - Use standard PGN format
   - Include headers: Event, Site, Date, White, Black, Result, ECO, Opening

2. **Run the seeder**
   ```bash
   python seed_classical_games.py
   ```

3. **Verify in database**
   ```bash
   python seed_classical_games.py --list
   ```

## Updating Openings Template

To add classical games section to a new opening:

1. **Edit `templates/openings.html`**

2. **Add after the "beginner-mistakes" div:**
   ```html
   <div class="classical-games">
       <h4>Classical Games</h4>
       <p class="classical-games-intro">Study these master games to see the [Opening Name] in action:</p>
       <div class="classical-games-links" data-opening="[Opening Name]">
           <span class="loading-games">Loading games...</span>
       </div>
   </div>
   ```

3. **Or use the automated script:**
   ```bash
   python add_classical_sections.py
   ```

## Game Selection Criteria

Classical games were chosen based on:
- **Historical significance** (World Championships, famous tournaments)
- **Instructive value** (demonstrates opening's key ideas)
- **Player strength** (games by world champions and top GMs)
- **Game quality** (brilliant play, interesting tactics/strategy)

## Future Enhancements

Potential improvements:
- Add AI commentary to curated games (uses existing `CuratedGameService`)
- Filter by player (show all Kasparov games)
- Add annotations to PGN (text comments explaining moves)
- Create themed collections (attacking games, endgames, etc.)
- User voting on best classical games
- "Game of the Day" feature

## File Structure

```
chess-analyzer/
├── seed_data/
│   └── classical_games.pgn          # 36 classical games
├── seed_classical_games.py          # Seeding script
├── add_classical_sections.py        # Template updater
├── update_openings_template.py      # Alternative updater
├── templates/
│   └── openings.html                # Updated with classical games sections
├── static/
│   ├── js/
│   │   └── learn.js                 # Loads and displays classical games
│   └── css/
│       └── learn.css                # Styling for classical games links
├── game_storage_db.py               # get_curated_games() method
└── app.py                           # /api/curated-pgns endpoint
```

## Database Schema

The `chess_games` table stores both live games and curated games:

```sql
-- Relevant fields for curated games
is_curated BOOLEAN NOT NULL DEFAULT FALSE
opening VARCHAR(255)
eco VARCHAR(10)
white_player VARCHAR(255)
black_player VARCHAR(255)
event VARCHAR(255)
site VARCHAR(255)
game_date VARCHAR(20)  -- Format: YYYY.MM.DD
white_elo INTEGER
black_elo INTEGER
```

Query curated games:
```sql
SELECT * FROM chess_games
WHERE is_curated = TRUE
  AND opening = 'Italian Game'
ORDER BY created_at DESC;
```
