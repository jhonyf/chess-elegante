# Curated Classical Chess Games

This directory contains curated classical chess games with **static UUIDs** for SEO optimization.

## Files

- `curated_games.yaml` - Master list of all curated games with static UUIDs

## Structure

The YAML file contains 36 curated classical games (3 per opening type):

- Italian Game (3 games)
- Ruy Lopez (3 games)
- Sicilian Defense (3 games)
- French Defense (3 games)
- Queen's Gambit (3 games)
- King's Indian Defense (3 games)
- London System (3 games)
- Caro-Kann Defense (3 games)
- English Opening (3 games)
- Scandinavian Defense (3 games)
- Nimzo-Indian Defense (3 games)
- Catalan Opening (3 games)

## UUID Format

All UUIDs follow the pattern: `a0000000-0000-4000-8000-0000000000XX`

- UUIDs are sequential (01-24 in hex)
- UUIDs are **permanent** and should never change
- These UUIDs are hardcoded in HTML templates for SEO

## Seeding the Database

To seed the curated games into your database:

\`\`\`bash
python seed_curated_games.py
\`\`\`

To list all curated games in the database:

\`\`\`bash
python seed_curated_games.py --list
\`\`\`

## Adding New Games

To add a new curated game:

1. Add the game to `curated_games.yaml` with a new sequential UUID
2. If the game should appear on the home page, update `templates/home.html`
3. If the game should appear on an opening page, manually add it to `templates/openings.html`
4. Run `python seed_curated_games.py` to seed the new game

## SEO Benefits

- **Static UUIDs**: URLs never change, even if database is reset
- **Static HTML**: Games are in HTML (not loaded via JavaScript), so search engines can crawl them
- **Schema.org markup**: Games include structured data for better search results
- **Stable URLs**: `/analyze/{uuid}` URLs are permanent and can be indexed

## Important Notes

- Never change existing UUIDs - they are referenced in multiple templates
- Always use sequential UUIDs for new games
- Keep game metadata (white, black, event, date) consistent with PGN content
- PGN strings should be properly formatted (one line, space-separated moves)
