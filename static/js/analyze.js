let board = null;
let game = new Chess();
let gameData = null;
let currentGameId = null; // Track currently loaded game
let navigator = null; // Move navigator instance

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    const gameSection = document.querySelector('.game-section');
    const gameId = gameSection.getAttribute('data-game-id');

    initBoard();
    loadBoardTheme();
    setupAnalyzerEventListeners();
    setupBottomTabs();

    if (gameId) {
        loadSavedGame(gameId);
    }
});

function initBoard() {
    const config = {
        draggable: false,
        position: 'start',
        pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png'
    };

    board = Chessboard('board', config);
}

function setupAnalyzerEventListeners() {
    // Navigation controls - will be connected when navigator is created
    const prevMoveBtn = document.getElementById('prevMoveBtn');
    const nextMoveBtn = document.getElementById('nextMoveBtn');

    if (prevMoveBtn) prevMoveBtn.addEventListener('click', () => navigator && navigator.goPrevious());
    if (nextMoveBtn) nextMoveBtn.addEventListener('click', () => navigator && navigator.goNext());
}

function handleKeyboard(e) {
    if (!gameData) return;

    switch(e.key) {
        case 'ArrowLeft':
            e.preventDefault();
            goPreviousMove();
            break;
        case 'ArrowRight':
            e.preventDefault();
            goNextMove();
            break;
        case 'Home':
            e.preventDefault();
            goToFirstMove();
            break;
        case 'End':
            e.preventDefault();
            goToLastMove();
            break;
    }
}


function displayGame() {
    if (!gameData) return;

    // Display metadata
    displayMetadata();

    // Reset board and game
    game = new Chess();
    board.position(game.fen());

    // Create navigator instance
    navigator = createMoveNavigator({
        board: board,
        game: game,
        moves: gameData.moves,
        onMoveChange: (moveIndex, _fen, moveData) => {
            // Display commentary if available
            if (moveData && gameData.move_analysis) {
                // Search for the matching analysis entry instead of relying on array position
                const expectedPlayer = (moveIndex % 2 === 0) ? 'White' : 'Black';
                const expectedMoveNumber = Math.floor(moveIndex / 2) + 1;

                const analysis = gameData.move_analysis.find(a =>
                    a.player === expectedPlayer && a.move_number === expectedMoveNumber
                );

                if (analysis) {
                    displayCommentary(analysis);
                } else {
                    hideCommentary();
                }
            } else {
                hideCommentary();
            }
        },
        onHistoryUpdate: () => {
            displayMoveList();
            updateMoveCounter();
        }
    });

    // Setup keyboard shortcuts
    setupNavigationKeyboard(navigator, () => gameData !== null);

    // Display move list
    displayMoveList();

    // Update move counter
    updateMoveCounter();

    // Show game section and controls
    showGameSection();
}

function showGameSection() {
    const gameSection = document.getElementById('gameSection');

    // Show game section
    gameSection.style.display = 'grid';
    setTimeout(() => gameSection.classList.add('visible'), 10);
}

function displayMetadata() {
    const metadata = document.getElementById('gameMetadata');
    const headers = gameData.headers;

    let html = '';

    if (headers.White || headers.Black) {
        html += `<div class="metadata-row">
            <span class="metadata-label">Players</span>
            <span class="metadata-value">${headers.White || '?'} vs ${headers.Black || '?'}</span>
        </div>`;
    }

    if (headers.WhiteElo || headers.BlackElo) {
        html += `<div class="metadata-row">
            <span class="metadata-label">Rating</span>
            <span class="metadata-value">${headers.WhiteElo || '?'} - ${headers.BlackElo || '?'}</span>
        </div>`;
    }

    if (headers.Result) {
        html += `<div class="metadata-row">
            <span class="metadata-label">Result</span>
            <span class="metadata-value">${headers.Result}</span>
        </div>`;
    }

    if (headers.Event) {
        html += `<div class="metadata-row">
            <span class="metadata-label">Event</span>
            <span class="metadata-value">${headers.Event}</span>
        </div>`;
    }

    if (headers.Date) {
        html += `<div class="metadata-row">
            <span class="metadata-label">Date</span>
            <span class="metadata-value">${headers.Date}</span>
        </div>`;
    }

    if (headers.ECO || headers.Opening) {
        html += `<div class="metadata-row">
            <span class="metadata-label">Opening</span>
            <span class="metadata-value">${headers.ECO ? headers.ECO + ' ' : ''}${headers.Opening || ''}</span>
        </div>`;
    }

    if (headers.TimeControl) {
        html += `<div class="metadata-row">
            <span class="metadata-label">Time</span>
            <span class="metadata-value">${headers.TimeControl}</span>
        </div>`;
    }

    if (headers.Site) {
        html += `<div class="metadata-row">
            <span class="metadata-label">Site</span>
            <span class="metadata-value">${headers.Site}</span>
        </div>`;
    }

    // Update metadata
    if (metadata) metadata.innerHTML = html;
}

function displayMoveList() {
    const movesList = document.getElementById('movesList');

    // Use compact rendering to show only current move row
    if (movesList && navigator) {
        const currentIndex = navigator.getCurrentIndex();
        renderCurrentMoveOnly(gameData.moves, movesList, currentIndex, (index) => navigator.goToMove(index));
    }
}

function updateMoveCounter() {
    const counter = document.getElementById('moveCounter');
    const total = gameData ? gameData.moves.length : 0;
    const current = navigator ? navigator.getCurrentIndex() + 1 : 0;
    const text = `Move ${current} / ${total}`;

    if (counter) counter.textContent = text;
}

// Board theme functions moved to chess-utils.js
// Use: loadBoardTheme() and applyBoardTheme(theme)

async function loadSavedGame(gameId) {
    try {
        const response = await fetch(`/api/game/${gameId}/data`);
        const data = await response.json();

        if (data.success) {
            const loadedGame = data.game;

            // Load the game data
            gameData = {
                headers: loadedGame.headers,
                moves: loadedGame.moves,
                move_count: loadedGame.moves.length,
                pgn_text: loadedGame.pgn_text,
                move_analysis: loadedGame.move_analysis || null
            };

            currentGameId = gameId;
            displayGame();

            // Show game
            const gameSection = document.getElementById('gameSection');
            gameSection.style.display = 'grid';
            setTimeout(() => gameSection.classList.add('visible'), 10);
        } else {
            alert('Error loading game: ' + data.error);
        }
    } catch (error) {
        alert('Error loading game: ' + error.message);
    }
}

// Commentary Display Functions

function displayCommentary(analysis) {
    const panel = document.getElementById('commentaryPanel');
    const commentaryText = document.getElementById('commentaryText');
    const evaluationText = document.getElementById('evaluationText');

    if (!analysis) {
        hideCommentary();
        return;
    }

    // Display commentary
    commentaryText.textContent = analysis.commentary || 'No commentary available';

    // Display evaluation data using shared utility
    const eval_data = analysis.evaluation;
    if (eval_data) {
        renderMoveEvaluation(eval_data, evaluationText, { showPosition: true });
    } else {
        evaluationText.innerHTML = '';
    }

    // Show the panel
    panel.style.display = 'block';
}

function hideCommentary() {
    const panel = document.getElementById('commentaryPanel');
    panel.style.display = 'none';
}

// Bottom Tabs for Mobile (Analyze Mode)
function setupBottomTabs() {
    const bottomTabs = document.querySelector('.mobile-bottom-tabs');
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');

    if (!bottomTabs) return;

    const isMobile = window.innerWidth <= 767;

    if (isMobile) {
        // Move right panel (analysis-panel) into the history tab
        const historyTab = document.getElementById('historyTab');
        const rightPanel = document.querySelector('.right-panel .analysis-panel');

        if (historyTab && rightPanel) {
            historyTab.appendChild(rightPanel);
        }
    }

    // Tab switching and collapse/expand
    tabButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const targetTab = this.getAttribute('data-tab');
            const wasActive = this.classList.contains('active');
            const isExpanded = bottomTabs.classList.contains('expanded');

            // If clicking on active tab and panel is expanded, collapse it
            if (wasActive && isExpanded) {
                bottomTabs.classList.remove('expanded');
                return;
            }

            // Expand panel if collapsed
            if (!isExpanded) {
                bottomTabs.classList.add('expanded');
            }

            // Remove active class from all buttons and panels
            tabButtons.forEach(b => b.classList.remove('active'));
            tabPanels.forEach(panel => panel.classList.remove('active'));

            // Add active class to clicked button and corresponding panel
            this.classList.add('active');
            const targetPanel = document.getElementById(targetTab + 'Tab');
            if (targetPanel) {
                targetPanel.classList.add('active');
            }
        });
    });

    // Handle window resize
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            if ((window.innerWidth <= 767) !== isMobile) {
                location.reload();
            }
        }, 250);
    });
}
