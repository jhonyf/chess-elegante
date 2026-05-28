"""
Update openings.html template to add classical games links for each opening
"""

import re

# List of openings in order they appear in the template
openings = [
    "Italian Game",
    "Ruy Lopez",
    "Sicilian Defense",
    "French Defense",
    "Queen's Gambit",
    "King's Indian Defense",
    "London System",
    "Caro-Kann Defense",
    "English Opening",
    "Scandinavian Defense",
    "Nimzo-Indian Defense",
    "Catalan Opening"
]

# Template for classical games section
classical_games_template = """
                    <div class="classical-games">
                        <h4>Classical Games</h4>
                        <p class="classical-games-intro">Study these master games to see the {opening} in action:</p>
                        <div class="classical-games-links" data-opening="{opening}">
                            <span class="loading-games">Loading games...</span>
                        </div>
                    </div>"""

def main():
    # Read the template file
    with open('templates/openings.html', 'r') as f:
        content = f.read()

    # For each opening (except Italian Game which is already done), find the beginner-mistakes div
    # and add the classical-games section after it
    for opening in openings[1:]:  # Skip Italian Game (already done)
        # Find the opening's title, then find the next beginner-mistakes closing tag
        title_pattern = f'<h3 class="lesson-title">{re.escape(opening)}'
        if opening == "Ruy Lopez":
            title_pattern = f'<h3 class="lesson-title">Ruy Lopez \\(Spanish Opening\\)'

        title_match = re.search(title_pattern, content)
        if not title_match:
            print(f"Warning: Could not find title for {opening}")
            continue

        search_start = title_match.end()
        section_pattern = (
            r'(<div class="beginner-mistakes">.*?</ul>\s*</div>)'
            r'(\s*</div>\s*<button class="view-board-btn")'
        )

        match = re.search(section_pattern, content[search_start:], re.DOTALL)
        if match:
            insert_pos = search_start + match.end(1)
            classical_section = classical_games_template.format(opening=opening)

            content = content[:insert_pos] + classical_section + content[insert_pos:]
            print(f"Added classical games section for: {opening}")
        else:
            print(f"Could not find insertion point for: {opening}")

    # Write the updated content
    with open('templates/openings.html', 'w') as f:
        f.write(content)

    print("\nTemplate updated successfully!")


if __name__ == '__main__':
    main()
