/**
 * Chess Elegante - Shared Chess Utilities
 * Common functions used across multiple pages
 */

/**
 * Convert chess notation to Unicode chess pieces
 * @param {string} san - Standard Algebraic Notation move
 * @param {boolean} isWhite - True if white piece, false if black
 * @returns {string} SAN with Unicode chess symbols
 */
function convertToUnicode(san, isWhite) {
    const whitePieces = {
        'K': '♔', // King
        'Q': '♕', // Queen
        'R': '♖', // Rook
        'B': '♗', // Bishop
        'N': '♘'  // Knight
        // Pawns don't have a letter prefix in SAN
    };

    const blackPieces = {
        'K': '♚', // King
        'Q': '♛', // Queen
        'R': '♜', // Rook
        'B': '♝', // Bishop
        'N': '♞'  // Knight
    };

    const pieces = isWhite ? whitePieces : blackPieces;

    // Replace piece letters with Unicode symbols
    let unicode = san;
    for (const [letter, symbol] of Object.entries(pieces)) {
        unicode = unicode.replace(letter, symbol);
    }

    return unicode;
}

/**
 * Render move history in a standard format
 * @param {Array} moves - Array of move objects with {san, uci} or just SAN strings
 * @param {HTMLElement} container - Container element to render moves into
 * @param {number} currentMoveIndex - Index of currently active move (-1 for none)
 * @param {Function} onMoveClick - Optional callback when a move is clicked (receives moveIndex)
 */
function renderMoveHistory(moves, container, currentMoveIndex = -1, onMoveClick = null) {
    container.innerHTML = '';

    // Group moves in pairs (white + black)
    for (let i = 0; i < moves.length; i += 2) {
        const movePairDiv = document.createElement('div');
        movePairDiv.className = 'move-pair';

        const moveNumber = Math.floor(i / 2) + 1;

        // Move number
        const numberSpan = document.createElement('span');
        numberSpan.className = 'move-number';
        numberSpan.textContent = `${moveNumber}.`;
        movePairDiv.appendChild(numberSpan);

        // White's move
        const whiteMove = document.createElement('span');
        whiteMove.className = 'move-san';
        const whiteSan = typeof moves[i] === 'string' ? moves[i] : moves[i].san;
        whiteMove.textContent = convertToUnicode(whiteSan, true);
        whiteMove.dataset.moveIndex = i;

        if (i === currentMoveIndex) {
            whiteMove.classList.add('active-move');
            // Scroll into view after render
            setTimeout(() => {
                whiteMove.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 0);
        }

        if (onMoveClick) {
            whiteMove.addEventListener('click', () => onMoveClick(i));
        }

        movePairDiv.appendChild(whiteMove);

        // Black's move (if exists)
        if (i + 1 < moves.length) {
            const blackMove = document.createElement('span');
            blackMove.className = 'move-san';
            const blackSan = typeof moves[i + 1] === 'string' ? moves[i + 1] : moves[i + 1].san;
            blackMove.textContent = convertToUnicode(blackSan, false);
            blackMove.dataset.moveIndex = i + 1;

            if (i + 1 === currentMoveIndex) {
                blackMove.classList.add('active-move');
                // Scroll into view after render
                setTimeout(() => {
                    blackMove.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }, 0);
            }

            if (onMoveClick) {
                blackMove.addEventListener('click', () => onMoveClick(i + 1));
            }

            movePairDiv.appendChild(blackMove);
        }

        container.appendChild(movePairDiv);
    }
}

/**
 * Render only the current move row (compact view for analyze page)
 * @param {Array} moves - Array of move objects with {san, uci} or just SAN strings
 * @param {HTMLElement} container - Container element to render moves into
 * @param {number} currentMoveIndex - Index of currently active move (-1 for none)
 * @param {Function} onMoveClick - Optional callback when a move is clicked (receives moveIndex)
 */
function renderCurrentMoveOnly(moves, container, currentMoveIndex = -1, onMoveClick = null) {
    container.innerHTML = '';

    // If no move is selected, show the starting position message
    if (currentMoveIndex === -1) {
        const startMsg = document.createElement('div');
        startMsg.className = 'move-pair';
        startMsg.style.justifyContent = 'center';
        startMsg.style.color = '#78716c';
        startMsg.style.fontSize = '14px';
        startMsg.textContent = '0. Start';
        container.appendChild(startMsg);
        return;
    }

    // Calculate which move pair this move belongs to
    const pairIndex = Math.floor(currentMoveIndex / 2);
    const whiteIndex = pairIndex * 2;
    const blackIndex = whiteIndex + 1;
    const moveNumber = pairIndex + 1;

    const movePairDiv = document.createElement('div');
    movePairDiv.className = 'move-pair';

    // Move number
    const numberSpan = document.createElement('span');
    numberSpan.className = 'move-number';
    numberSpan.textContent = `${moveNumber}.`;
    movePairDiv.appendChild(numberSpan);

    // White's move
    if (whiteIndex < moves.length) {
        const whiteMove = document.createElement('span');
        whiteMove.className = 'move-san';
        const whiteSan = typeof moves[whiteIndex] === 'string' ? moves[whiteIndex] : moves[whiteIndex].san;
        whiteMove.textContent = convertToUnicode(whiteSan, true);
        whiteMove.dataset.moveIndex = whiteIndex;

        if (whiteIndex === currentMoveIndex) {
            whiteMove.classList.add('active-move');
        }

        if (onMoveClick) {
            whiteMove.addEventListener('click', () => onMoveClick(whiteIndex));
        }

        movePairDiv.appendChild(whiteMove);
    }

    // Black's move (if exists)
    if (blackIndex < moves.length) {
        const blackMove = document.createElement('span');
        blackMove.className = 'move-san';
        const blackSan = typeof moves[blackIndex] === 'string' ? moves[blackIndex] : moves[blackIndex].san;
        blackMove.textContent = convertToUnicode(blackSan, false);
        blackMove.dataset.moveIndex = blackIndex;

        if (blackIndex === currentMoveIndex) {
            blackMove.classList.add('active-move');
        }

        if (onMoveClick) {
            blackMove.addEventListener('click', () => onMoveClick(blackIndex));
        }

        movePairDiv.appendChild(blackMove);
    }

    container.appendChild(movePairDiv);
}

/**
 * Render move evaluation in a consistent format
 * @param {Object} evaluation - Evaluation data object
 * @param {HTMLElement} container - Container element to render evaluation into
 * @param {Object} options - Optional configuration { showPosition: boolean }
 */
function renderMoveEvaluation(evaluation, container, options = {}) {
    const showPosition = options.showPosition !== false; // Default to true

    if (!evaluation) {
        container.innerHTML = '';
        return;
    }

    // Format evaluation values
    const eval_loss = (evaluation.eval_loss / 100).toFixed(2);
    const classification = evaluation.classification || 'unknown';
    const classificationLower = classification.toLowerCase();
    const best_move = evaluation.best_move || 'N/A';

    // Capitalize classification for display
    const classificationDisplay = classification.charAt(0).toUpperCase() + classification.slice(1).toLowerCase();

    // Build evaluation HTML in single-line format
    let leftHtml = `
        <div class="evaluation-left">
            <span class="evaluation-dot ${classificationLower}"></span>
            <span class="evaluation-classification ${classificationLower}">${classificationDisplay}</span>
        </div>
    `;

    let rightHtml = '<div class="evaluation-right">';

    // Position and eval loss
    if (evaluation.evaluation_after !== undefined) {
        const eval_after = (evaluation.evaluation_after / 100).toFixed(2);
        rightHtml += `<span>P${eval_after > 0 ? '+' : ''}${eval_after}</span>`;
    } 
    rightHtml += `<span class="evaluation-separator">|</span>`;
    if (eval_loss !== undefined) {
        rightHtml += `<span>${eval_loss}</span>`;
    }

    // Best move
    rightHtml += `<span class="evaluation-separator">|</span>`;
    if (best_move !== 'N/A') {
        rightHtml += `<span class="evaluation-best">${best_move}</span>`;
    }

    rightHtml += '</div>';

    container.innerHTML = leftHtml + rightHtml;
}

/**
 * Create a move history navigator with shared navigation logic
 * @param {Object} config - Configuration object
 * @returns {Object} Navigator instance with methods
 */
function createMoveNavigator(config) {
    const {
        board,              // Chessboard instance
        game,              // Chess.js instance
        moves,             // Array of moves
        onMoveChange,      // Callback when move changes: (moveIndex, fen, moveData) => void
        onHistoryUpdate,   // Callback to update display: (currentIndex) => void
    } = config;

    let currentMoveIndex = -1;

    return {
        getCurrentIndex() {
            return currentMoveIndex;
        },

        goToMove(moveIndex) {
            if (moveIndex < -1 || moveIndex >= moves.length) return;

            currentMoveIndex = moveIndex;

            // Reset and replay moves
            game.reset();
            for (let i = 0; i <= moveIndex; i++) {
                const move = moves[i];
                game.move(move.uci || move, { sloppy: true });
            }

            // Update board
            board.position(game.fen());

            // Notify callbacks
            const moveData = moveIndex >= 0 ? moves[moveIndex] : null;
            if (onMoveChange) onMoveChange(moveIndex, game.fen(), moveData);
            if (onHistoryUpdate) onHistoryUpdate(currentMoveIndex);

            return currentMoveIndex;
        },

        goToFirst() {
            game.reset();
            currentMoveIndex = -1;
            board.position('start');

            if (onMoveChange) onMoveChange(-1, game.fen(), null);
            if (onHistoryUpdate) onHistoryUpdate(currentMoveIndex);

            return currentMoveIndex;
        },

        goPrevious() {
            if (currentMoveIndex < 0) return currentMoveIndex;
            return this.goToMove(currentMoveIndex - 1);
        },

        goNext() {
            if (currentMoveIndex >= moves.length - 1) return currentMoveIndex;
            return this.goToMove(currentMoveIndex + 1);
        },

        goToLast() {
            if (moves.length === 0) return currentMoveIndex;
            return this.goToMove(moves.length - 1);
        },

        updateCurrentIndex(index) {
            currentMoveIndex = index;
        },

        isAtEnd() {
            return currentMoveIndex === moves.length - 1;
        },

        isAtStart() {
            return currentMoveIndex === -1;
        }
    };
}

/**
 * Setup keyboard shortcuts for move navigation
 * @param {Object} navigator - Navigator instance from createMoveNavigator
 * @param {Function} canNavigate - Optional function to check if navigation is allowed
 */
function setupNavigationKeyboard(navigator, canNavigate = () => true) {
    document.addEventListener('keydown', (e) => {
        if (!canNavigate()) return;

        switch(e.key) {
            case 'ArrowLeft':
                e.preventDefault();
                navigator.goPrevious();
                break;
            case 'ArrowRight':
                e.preventDefault();
                navigator.goNext();
                break;
            case 'Home':
                e.preventDefault();
                navigator.goToFirst();
                break;
            case 'End':
                e.preventDefault();
                navigator.goToLast();
                break;
        }
    });
}

/**
 * Load saved board theme from localStorage and apply it
 * @param {string} selectId - Optional ID of theme select element (for play mode)
 */
function loadBoardTheme(selectId = null) {
    const savedTheme = localStorage.getItem('boardTheme') || 'minimal';

    // If select element ID is provided, update its value
    if (selectId) {
        const themeSelect = document.getElementById(selectId);
        if (themeSelect) {
            themeSelect.value = savedTheme;
        }
    }

    applyBoardTheme(savedTheme);
}

/**
 * Apply a board theme to the chess board
 * @param {string} theme - Theme name (minimal, classic, gray, blue, green, purple, ice, wood)
 */
function applyBoardTheme(theme) {
    const boardElement = document.getElementById('board');
    if (!boardElement) return;

    const themeClasses = [
        'board-theme-minimal', 'board-theme-classic', 'board-theme-gray',
        'board-theme-blue', 'board-theme-green', 'board-theme-purple',
        'board-theme-ice', 'board-theme-wood'
    ];

    // Remove all existing theme classes
    themeClasses.forEach(cls => boardElement.classList.remove(cls));

    // Add the selected theme class
    boardElement.classList.add(`board-theme-${theme}`);
}

/**
 * Set status message with optional type styling
 * @param {string} message - Status message to display
 * @param {string} type - Message type: 'info', 'success', 'error', 'warning'
 */
function setStatusMessage(message, type = 'info') {
    const statusTextMobile = document.getElementById('statusText');
    if (statusTextMobile) {
        statusTextMobile.textContent = message;
    }

    // Update status dot color if it exists
    const statusDot = document.querySelector('.status-dot');
    if (statusDot) {
        statusDot.classList.remove('status-success', 'status-error', 'status-warning', 'status-info');
        statusDot.classList.add(`status-${type}`);
    }
}
