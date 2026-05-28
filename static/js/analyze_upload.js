// Chess Elegante - Games Page (Unified)

let gameToDelete = null; // Track game to delete
let lastUploadedGameId = null; // Track most recently uploaded game

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    loadCuratedGames();

    // Only load user games if user is authenticated (savedTab exists)
    if (document.getElementById('savedTab')) {
        loadMyGames();
    }
});

function setupEventListeners() {
    // Upload modal controls (only if user is authenticated)
    const uploadBtn = document.getElementById('openUploadModalBtn');
    if (uploadBtn) {
        uploadBtn.addEventListener('click', () => openModal('uploadModal'));
    }

    const loadBtn = document.getElementById('loadPgnBtn');
    if (loadBtn) {
        loadBtn.addEventListener('click', loadPgn);
    }

    const clearBtn = document.getElementById('clearPgnBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearPgn);
    }

    // Tab switching
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            switchTab(tabName);
        });
    });

    // Modal controls (only if user is authenticated)
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', confirmDeleteGame);
    }

    const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
    if (cancelDeleteBtn) {
        cancelDeleteBtn.addEventListener('click', () => closeModal('deletePgnModal'));
    }

    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', function() {
            const modalId = this.getAttribute('data-modal');
            closeModal(modalId);
        });
    });

    // Close modal when clicking outside
    const deleteModal = document.getElementById('deletePgnModal');
    if (deleteModal) {
        deleteModal.addEventListener('click', function(e) {
            if (e.target === this) closeModal('deletePgnModal');
        });
    }

    const uploadModal = document.getElementById('uploadModal');
    if (uploadModal) {
        uploadModal.addEventListener('click', function(e) {
            if (e.target === this) closeModal('uploadModal');
        });
    }
}

function openModal(modalId) {
    document.getElementById(modalId).style.display = 'flex';
}

function switchTab(tabName) {
    // Remove active class from all tab buttons and tab contents
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    // Add active class to selected tab button and content
    document.querySelector(`.tab-button[data-tab="${tabName}"]`).classList.add('active');

    if (tabName === 'curated') {
        document.getElementById('curatedTab').classList.add('active');
    } else if (tabName === 'saved') {
        document.getElementById('savedTab').classList.add('active');
    }
}

async function loadPgn() {
    const pgnText = document.getElementById('pgnInput').value.trim();

    if (!pgnText) {
        setStatus('Please enter or upload a PGN', 'error');
        return;
    }

    setStatus('Parsing PGN...', 'info');

    try {
        const response = await fetch('/api/parse-pgn', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ pgn: pgnText })
        });

        const data = await response.json();

        if (data.success) {
            // Auto-save the PGN
            await autoSaveGame(pgnText, data);
        } else {
            setStatus('Error: ' + data.error, 'error');
        }
    } catch (error) {
        setStatus('Error parsing PGN: ' + error.message, 'error');
    }
}

async function autoSaveGame(pgnText, parsedData) {
    const headers = parsedData.headers;
    const suggestedName = `${headers.White || 'Player'} vs ${headers.Black || 'Player'}`;

    try {
        const response = await fetch('/api/save-pgn', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                pgn_text: pgnText,
                headers: parsedData.headers,
                moves: parsedData.moves,
                name: suggestedName
            })
        });

        const data = await response.json();

        if (data.success) {
            setStatus(`Game saved: ${suggestedName}`, 'success');
            lastUploadedGameId = data.game_id;

            // Close modal
            closeModal('uploadModal');

            // Clear input
            document.getElementById('pgnInput').value = '';

            // Switch to My Games tab
            switchTab('saved');

            // Reload My Games and highlight the new one
            await loadMyGames();

            // Scroll to the new game and highlight it
            setTimeout(() => {
                const newGameElement = document.querySelector(`[data-game-id="${data.game_id}"]`);
                if (newGameElement) {
                    newGameElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    newGameElement.classList.add('highlight-new');
                    setTimeout(() => newGameElement.classList.remove('highlight-new'), 2000);
                }
            }, 100);
        } else {
            setStatus(`Failed to save game: ${data.error}`, 'error');
        }
    } catch (error) {
        setStatus(`Failed to save game: ${error.message}`, 'error');
    }
}

function clearPgn() {
    document.getElementById('pgnInput').value = '';
    setStatus('', '');
}

function setStatus(message, type = 'info') {
    const statusEl = document.getElementById('uploadStatus');
    statusEl.textContent = message;
    statusEl.className = 'status-message ' + type;
}

// My Games Functions (all user games - live and imported)

async function loadMyGames() {
    try {
        const response = await fetch('/api/games');
        const data = await response.json();

        if (data.success) {
            displayMyGames(data.user_games);
        }
    } catch (error) {
        console.error('Error loading games:', error);
    }
}

function displayMyGames(games) {
    const container = document.getElementById('savedPgnsList');

    if (!games || games.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No games yet. Upload a game or play one!</p>
            </div>
        `;
        return;
    }

    let html = '';
    games.forEach(game => {
        const gameId = game.id;
        const gameType = game.game_type || 'imported';
        const moveCount = game.move_count || 0;
        const isCurated = game.is_curated || false;

        // Skip curated games in My Games tab
        if (isCurated) return;

        html += createGameCard(game, gameId, gameType, moveCount);
    });

    container.innerHTML = html || '<div class="empty-state"><p>No games yet. Upload a game or play one!</p></div>';
}

function createGameCard(game, gameId, gameType, moveCount) {
    const isLiveGame = gameType === 'live';

    if (isLiveGame) {
        // Live game card (from games.js)
        const status = game.status || 'unknown';
        const engineType = game.engine_type === 'lichess' ? 'Lichess' : 'Stockfish';
        const playerColor = game.player_color || 'white';
        const aiLevel = game.ai_level || 1;
        const updatedAt = formatDate(game.updated_at);
        const hasCommentary = game.commentary_status === 'completed';
        const isProcessing = game.commentary_status === 'processing';

        return `
            <div class="pgn-item game-card-live" data-game-id="${gameId}" onclick="viewGame('${gameId}', '${gameType}')">
                <div class="pgn-item-header">
                    <div class="pgn-info">
                        <div class="pgn-name">${escapeHtml(game.name || `Game ${gameId.substring(0, 8)}`)}</div>
                        <div class="pgn-date">${updatedAt}</div>
                    </div>
                    <div class="pgn-result"><span class="game-type-badge">Live Game</span></div>
                </div>
                <div class="pgn-details" onclick="event.stopPropagation()">
                    <div class="pgn-detail-row">
                        <span class="pgn-detail-label">Status</span>
                        <span class="pgn-detail-value">${status}</span>
                    </div>
                    <div class="pgn-detail-row">
                        <span class="pgn-detail-label">Engine</span>
                        <span class="pgn-detail-value">${engineType}</span>
                    </div>
                    <div class="pgn-detail-row">
                        <span class="pgn-detail-label">Color</span>
                        <span class="pgn-detail-value">${playerColor}</span>
                    </div>
                    <div class="pgn-detail-row">
                        <span class="pgn-detail-label">AI Level</span>
                        <span class="pgn-detail-value">Level ${aiLevel}</span>
                    </div>
                    <div class="pgn-detail-row">
                        <span class="pgn-detail-label">Moves</span>
                        <span class="pgn-detail-value">${moveCount}</span>
                    </div>
                </div>
                <div class="pgn-actions" onclick="event.stopPropagation()">
                    <button class="pgn-action-btn" onclick="viewGame('${gameId}', '${gameType}')">
                        ${status === 'started' ? 'Resume Game' : 'View Game'}
                    </button>
                    ${status !== 'started' && !hasCommentary ? `
                        <button class="pgn-action-btn commentary-btn" onclick="generateCommentary('${gameId}')" ${isProcessing ? 'disabled' : ''}>
                            ${isProcessing ? 'Processing...' : 'Generate Commentary'}
                        </button>
                    ` : ''}
                    ${hasCommentary ? '<button class="pgn-action-btn commentary-btn has-commentary" disabled>✓ Has Commentary</button>' : ''}
                    <button class="pgn-action-btn delete-btn" onclick="openDeleteGameModal('${gameId}')">
                        Delete
                    </button>
                </div>
            </div>
        `;
    } else {
        // Imported game card (from analyze_upload.js)
        const white = escapeHtml(game.white_player || '?');
        const black = escapeHtml(game.black_player || '?');
        const event = escapeHtml(game.event || 'Unknown');
        const gameDate = escapeHtml(game.game_date || 'Unknown');
        const result = escapeHtml(game.result || '*');
        const createdAt = formatDate(game.created_at);
        const hasCommentary = game.has_analysis || false;

        return `
            <div class="pgn-item" data-game-id="${gameId}" onclick="viewGame('${gameId}', '${gameType}')">
                <div class="pgn-item-header">
                    <div class="pgn-info">
                        <div class="pgn-name">${escapeHtml(game.name)}</div>
                        <div class="pgn-date">${createdAt}</div>
                    </div>
                    <div class="pgn-result">${result}</div>
                </div>
                <div class="pgn-details" onclick="event.stopPropagation()">
                    <div class="pgn-detail-row">
                        <span class="pgn-detail-label">White</span>
                        <span class="pgn-detail-value">${white}</span>
                    </div>
                    <div class="pgn-detail-row">
                        <span class="pgn-detail-label">Black</span>
                        <span class="pgn-detail-value">${black}</span>
                    </div>
                    <div class="pgn-detail-row">
                        <span class="pgn-detail-label">Event</span>
                        <span class="pgn-detail-value">${event}</span>
                    </div>
                    <div class="pgn-detail-row">
                        <span class="pgn-detail-label">Date</span>
                        <span class="pgn-detail-value">${gameDate}</span>
                    </div>
                    <div class="pgn-detail-row">
                        <span class="pgn-detail-label">Moves</span>
                        <span class="pgn-detail-value">${moveCount}</span>
                    </div>
                </div>
                <div class="pgn-actions" onclick="event.stopPropagation()">
                    <button class="pgn-action-btn" onclick="viewGame('${gameId}', '${gameType}')">
                        Load & Analyze
                    </button>
                    ${hasCommentary ?
                        '<button class="pgn-action-btn commentary-btn has-commentary" disabled>✓ Has Commentary</button>' :
                        `<button class="pgn-action-btn commentary-btn" onclick="generateCommentary('${gameId}')">Generate Commentary</button>`}
                    <button class="pgn-action-btn delete-btn" onclick="openDeleteGameModal('${gameId}')">
                        Delete
                    </button>
                </div>
            </div>
        `;
    }
}

function viewGame(gameId, gameType) {
    if (gameType === 'live') {
        // Check game status first
        fetch(`/api/game/${gameId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const game = data.game;
                    const status = game.live_state?.status || 'started';

                    if (status === 'started') {
                        // Resume active game in play mode
                        return fetch(`/api/resume-game/${gameId}`, { method: 'POST' })
                            .then(response => response.json())
                            .then(resumeData => {
                                if (resumeData.success) {
                                    window.location.href = '/play';
                                } else {
                                    alert('Failed to resume game: ' + resumeData.error);
                                }
                            });
                    } else {
                        // View completed game in analyze mode
                        window.location.href = '/analyze/' + gameId;
                    }
                } else {
                    alert('Failed to load game: ' + data.error);
                }
            })
            .catch(error => alert('Error loading game: ' + error.message));
    } else {
        // View imported game in analyze mode
        window.location.href = '/analyze/' + gameId;
    }
}

async function generateCommentary(gameId) {
    if (!confirm('Generate AI commentary for this game? This may take a few minutes.')) {
        return;
    }

    // Find the button and update its text
    const button = event.target;
    const originalText = button.textContent;
    button.textContent = 'Generating...';
    button.disabled = true;

    try {
        const response = await fetch(`/api/generate-commentary/${gameId}`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            alert('Commentary generated successfully!');
            loadMyGames(); // Refresh the list
        } else {
            alert('Failed to generate commentary: ' + data.error);
            button.textContent = originalText;
            button.disabled = false;
        }
    } catch (error) {
        alert('Error generating commentary: ' + error.message);
        button.textContent = originalText;
        button.disabled = false;
    }
}

function openDeleteGameModal(gameId) {
    gameToDelete = gameId;
    document.getElementById('deletePgnStatus').textContent = '';
    document.getElementById('deletePgnModal').style.display = 'flex';
}

async function confirmDeleteGame() {
    if (!gameToDelete) return;

    const statusEl = document.getElementById('deletePgnStatus');

    try {
        const response = await fetch(`/api/delete-game/${gameToDelete}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            statusEl.textContent = 'Game deleted successfully!';
            statusEl.className = 'status-message success';

            // Refresh the list
            loadMyGames();

            setTimeout(() => {
                closeModal('deletePgnModal');
                gameToDelete = null;
            }, 1000);
        } else {
            statusEl.textContent = 'Error: ' + data.error;
            statusEl.className = 'status-message error';
        }
    } catch (error) {
        statusEl.textContent = 'Error deleting game: ' + error.message;
        statusEl.className = 'status-message error';
    }
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Curated Games Functions

async function loadCuratedGames() {
    try {
        const response = await fetch('/api/curated-games');
        const data = await response.json();

        if (data.success) {
            displayCuratedGames(data.games);
        }
    } catch (error) {
        console.error('Error loading curated games:', error);
    }
}

function displayCuratedGames(games) {
    const container = document.getElementById('curatedPgnsList');

    if (!games || games.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No curated games available yet.</p>
            </div>
        `;
        return;
    }

    let html = '';
    games.forEach(game => {
        const gameId = game.game_id;
        const moveCount = game.move_count || 0;
        const white = escapeHtml(game.white || '?');
        const black = escapeHtml(game.black || '?');
        const event = escapeHtml(game.event || 'Unknown');
        const gameDate = escapeHtml(game.date || 'Unknown');
        const result = escapeHtml(game.result || '*');
        const opening = escapeHtml(game.opening || 'Unknown Opening');

        html += `
            <div class="pgn-item curated-item" onclick="viewGame('${gameId}', 'imported')">
                <div class="pgn-item-header">
                    <div class="pgn-info">
                        <div class="pgn-name">${escapeHtml(game.name)}</div>
                        <div class="pgn-date">${gameDate}</div>
                    </div>
                    <div class="pgn-result">${result}</div>
                </div>
                <div class="pgn-details" onclick="event.stopPropagation()">
                    <div class="pgn-detail-row">
                        <span class="pgn-detail-label">White</span>
                        <span class="pgn-detail-value">${white}</span>
                    </div>
                    <div class="pgn-detail-row">
                        <span class="pgn-detail-label">Black</span>
                        <span class="pgn-detail-value">${black}</span>
                    </div>
                    <div class="pgn-detail-row">
                        <span class="pgn-detail-label">Event</span>
                        <span class="pgn-detail-value">${event}</span>
                    </div>
                    <div class="pgn-detail-row">
                        <span class="pgn-detail-label">Opening</span>
                        <span class="pgn-detail-value">${opening}</span>
                    </div>
                    <div class="pgn-detail-row">
                        <span class="pgn-detail-label">Moves</span>
                        <span class="pgn-detail-value">${moveCount}</span>
                    </div>
                </div>
                <div class="pgn-actions" onclick="event.stopPropagation()">
                    <button class="pgn-action-btn" onclick="viewGame('${gameId}', 'imported')">
                        Load & Analyze
                    </button>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// Utility Functions

function formatDate(dateStr) {
    if (!dateStr) return 'Unknown';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
