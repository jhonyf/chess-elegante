/**
 * Chess Elegante - Unified Game State Management
 *
 * New architecture with:
 * - Single source of truth (server state)
 * - Unified polling for both Lichess and Stockfish
 * - No race conditions
 * - Mobile-friendly
 */

// ==================== STATE MANAGER ====================

class GameStateManager {
    constructor() {
        this.state = {
            version: 0,
            gameId: null,
            engineType: null,
            status: 'not_started',
            playerColor: 'white',
            currentTurn: 'white',
            isPlayerTurn: false,
            fen: 'start',
            moves: [],
            moveAnalysis: {},
            lastMove: null,
            aiLevel: 1,
            timestamp: null
        };

        this.pollInterval = null;
        this.listeners = [];
        this.isPolling = false;
    }

    /**
     * Update state from server data
     * Only updates if server version is newer
     */
    updateState(serverData) {
        if (!serverData.success) {
            console.error('Server returned error:', serverData.error);
            return false;
        }

        // Check version to prevent stale updates (but allow first update when both are 0)
        const isFirstUpdate = this.state.version === 0 && this.state.gameId === null;
        if (!isFirstUpdate && serverData.version !== undefined && serverData.version <= this.state.version) {
            console.log(`Ignoring stale update (server: ${serverData.version}, local: ${this.state.version})`);
            return false;
        }

        console.log(`Updating state from version ${this.state.version} to ${serverData.version}`);

        // Update state
        this.state = {
            version: serverData.version || 0,
            gameId: serverData.game_id || this.state.gameId,
            engineType: serverData.engine_type || this.state.engineType,
            status: serverData.status || this.state.status,
            playerColor: serverData.player_color || this.state.playerColor,
            currentTurn: serverData.current_turn || this.state.currentTurn,
            isPlayerTurn: serverData.is_player_turn !== undefined ? serverData.is_player_turn : this.state.isPlayerTurn,
            fen: serverData.fen || this.state.fen,
            moves: serverData.moves || this.state.moves,
            moveAnalysis: serverData.move_analysis || this.state.moveAnalysis,
            lastMove: serverData.last_move || this.state.lastMove,
            aiLevel: serverData.ai_level || this.state.aiLevel,
            timestamp: serverData.timestamp || this.state.timestamp
        };

        // Notify all listeners
        this.notifyListeners();
        return true;
    }

    /**
     * Start polling for game state updates
     */
    startPolling(intervalMs = 2000) {
        if (this.isPolling) {
            console.log('Polling already active');
            return;
        }

        console.log(`Starting state polling every ${intervalMs}ms`);
        this.isPolling = true;
        this.baseInterval = intervalMs;

        // Poll immediately
        this.poll();

        // Then poll on interval
        this.pollInterval = setInterval(() => this.poll(), intervalMs);
    }

    /**
     * Stop polling
     */
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        this.isPolling = false;
        console.log('Stopped state polling');
    }

    /**
     * Adjust polling speed based on game state
     */
    adjustPollingSpeed() {
        if (this.state.status !== 'started') {
            // Game finished - stop polling completely
            console.log('Game finished, stopping polling');
            this.stopPolling();
            return;
        }

        if (this.state.isPlayerTurn) {
            // Player's turn - STOP polling completely
            // No need to poll - state only changes when player makes a move
            console.log('Player turn - stopping polling (will resume after move)');
            this.stopPolling();
        } else if (!this.isPolling) {
            // AI's turn and not polling - START polling fast
            console.log('AI turn - starting fast polling (1000ms)');
            this.startPolling(1000);
        }
    }

    /**
     * Poll server for current game state
     */
    async poll() {
        try {
            const response = await fetch('/api/game-state');
            const data = await response.json();

            if (data.success) {
                const updated = this.updateState(data);

                // Adjust polling speed based on new state
                if (updated) {
                    this.adjustPollingSpeed();
                }
            } else {
                // No active game
                this.stopPolling();
            }
        } catch (error) {
            console.error('Poll error:', error);
        }
    }

    /**
     * Subscribe to state changes
     */
    subscribe(callback) {
        this.listeners.push(callback);
        // Immediately call with current state
        callback(this.state);
    }

    /**
     * Notify all listeners of state change
     */
    notifyListeners() {
        this.listeners.forEach(callback => {
            try {
                callback(this.state);
            } catch (error) {
                console.error('Listener error:', error);
            }
        });
    }

    /**
     * Reset state
     */
    reset() {
        this.stopPolling();
        this.state = {
            version: 0,
            gameId: null,
            engineType: null,
            status: 'not_started',
            playerColor: 'white',
            currentTurn: 'white',
            isPlayerTurn: false,
            fen: 'start',
            moves: [],
            moveAnalysis: {},
            lastMove: null,
            aiLevel: 1,
            timestamp: null
        };
        this.notifyListeners();
    }
}

// ==================== UI CONTROLLER ====================

class UIController {
    constructor(stateManager) {
        this.stateManager = stateManager;
        this.board = null;
        this.chessGame = new Chess();
        this.selectedSquare = null;
        this.isProcessingMove = false;
        this.navigator = null;
        this.isReviewingHistory = false;
        this.movesHistory = []; // Store moves history as instance variable

        // Initialize board FIRST
        this.initBoard();
        this.setupEventListeners();

        // Subscribe to state changes AFTER board is ready
        stateManager.subscribe((state) => this.render(state));
    }

    /**
     * Initialize chessboard
     */
    initBoard() {
        const config = {
            draggable: false,
            position: 'start',
            pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png'
        };

        this.board = ChessBoard('board', config);
        this.addClickHandlers();
    }

    /**
     * Add click handlers for move input
     */
    addClickHandlers() {
        const boardEl = document.getElementById('board');

        boardEl.addEventListener('click', (e) => {
            let element = e.target;
            let squareEl = null;

            // Find square element
            while (element && element !== boardEl) {
                const classes = Array.from(element.classList || []);
                const squareClass = classes.find(c => c.match(/^square-[a-h][1-8]$/));
                if (squareClass) {
                    squareEl = element;
                    break;
                }
                element = element.parentElement;
            }

            if (!squareEl) return;

            const square = Array.from(squareEl.classList)
                .find(c => c.match(/^square-[a-h][1-8]$/))
                .replace('square-', '');

            this.handleSquareClick(square);
        });
    }

    /**
     * Handle square click
     */
    async handleSquareClick(square) {
        const state = this.stateManager.state;

        // Debug logging
        console.log('Square clicked:', square);
        console.log('State:', {
            isPlayerTurn: state.isPlayerTurn,
            status: state.status,
            isProcessingMove: this.isProcessingMove,
            playerColor: state.playerColor,
            currentTurn: state.currentTurn
        });

        // Ignore if not player's turn or game not active
        if (!state.isPlayerTurn || state.status !== 'started' || this.isProcessingMove) {
            console.log('Click ignored - not player turn or game not started');
            return;
        }

        const piece = this.chessGame.get(square);

        // First click - select piece
        if (!this.selectedSquare) {
            if (piece && piece.color === this.chessGame.turn()) {
                this.selectedSquare = square;
                this.highlightSquare(square);
                this.showPossibleMoves(square);
            }
            return;
        }

        // Clicking on same square - deselect
        if (square === this.selectedSquare) {
            this.clearSelection();
            return;
        }

        // Clicking on another piece of same color - change selection
        if (piece && piece.color === this.chessGame.turn()) {
            this.clearSelection();
            this.selectedSquare = square;
            this.highlightSquare(square);
            this.showPossibleMoves(square);
            return;
        }

        // Second click - try to make move
        const from = this.selectedSquare;
        const to = square;

        // Clear selection
        this.clearSelection();

        // Try to make the move
        await this.makeMove(from, to);
    }

    /**
     * Make a move
     */
    async makeMove(from, to) {
        // Lock moves
        this.isProcessingMove = true;
        this.setStatus('Your Turn', 'info');

        try {
            // Store FEN before the move for evaluation
            const fenBefore = this.chessGame.fen();

            // Validate move locally first
            const move = this.chessGame.move({ from, to });

            if (!move) {
                this.setStatus('Illegal move', 'error');
                this.isProcessingMove = false;
                return;
            }

            // Store move UCI and current move count
            const moveUci = move.from + move.to;
            const moveCountBeforeAI = this.stateManager.state.moves.length + 1; // +1 for our move

            // Optimistically update board
            this.board.position(this.chessGame.fen());

            // Send to server
            const response = await fetch('/api/make-move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ move: moveUci })
            });

            const data = await response.json();

            if (!data.success) {
                // Revert move
                this.chessGame.undo();
                this.board.position(this.chessGame.fen());
                this.setStatus('Error: ' + data.error, 'error');
                this.isProcessingMove = false;
                return;
            }

            // Success! Move sent to server
            this.setStatus('Computer Turn', 'info');

            // Evaluate the player's move using the FEN we captured before
            this.evaluatePlayerMove(fenBefore, moveUci);

            // Resume polling to detect AI's response
            console.log('Move sent, resuming polling for AI response');
            this.stateManager.startPolling(1000);

            // Set up a listener to unlock when AI move is detected
            const unlockListener = (state) => {
                if (state.moves.length > moveCountBeforeAI) {
                    console.log('AI move detected, unlocking board');
                    this.isProcessingMove = false;
                    // Remove this listener
                    const index = this.stateManager.listeners.indexOf(unlockListener);
                    if (index > -1) {
                        this.stateManager.listeners.splice(index, 1);
                    }
                }
            };
            this.stateManager.subscribe(unlockListener);

        } catch (error) {
            console.error('Move error:', error);
            this.chessGame.undo();
            this.board.position(this.chessGame.fen());
            this.setStatus('Error: ' + error.message, 'error');
            this.isProcessingMove = false;
        }
    }

    /**
     * Render UI based on current state
     */
    render(state) {
        console.log('Rendering UI for state:', state);

        // Guard: board not initialized yet
        if (!this.board) {
            console.log('Board not ready, skipping render');
            return;
        }

        // Update chess game and board
        if (state.moves.length > 0) {
            this.chessGame = new Chess();
            for (let move of state.moves) {
                const moveUci = typeof move === 'string' ? move : move.uci;
                try {
                    this.chessGame.move(moveUci, { sloppy: true });
                } catch (e) {
                    console.error('Failed to apply move:', moveUci, e);
                }
            }
        } else {
            this.chessGame = new Chess();
        }

        this.board.position(this.chessGame.fen());

        // Update move history
        this.updateMoveHistory(state.moves);

        // Update status based on game state
        if (state.status === 'started') {
            if (state.isPlayerTurn) {
                this.setStatus('Your Turn', 'success');
            } else {
                this.setStatus('Computer Turn', 'info');
            }
        } else if (state.status === 'mate') {
            const winner = state.currentTurn === 'white' ? 'Black' : 'White';
            this.setStatus(`Checkmate! ${winner} wins`, 'success');
        } else if (state.status === 'draw') {
            this.setStatus('Draw', 'info');
        } else if (state.status === 'resigned') {
            this.setStatus('Game resigned', 'info');
        } else if (state.status === 'not_started') {
            this.setStatus('Ready to start a new game', 'info');
        }

        // Show/hide game action buttons (all buttons in the container)
        const gameActionButtons = document.querySelector('.game-action-buttons');
        if (gameActionButtons) {
            gameActionButtons.style.display = state.status === 'started' ? 'flex' : 'none';
        }
    }

    /**
     * Update move history display
     */
    updateMoveHistory(moves) {
        const moveListEl = document.getElementById('movesList');
        if (!moveListEl) return;

        // If no moves, clear and return
        if (!moves || moves.length === 0) {
            moveListEl.innerHTML = '';
            this.navigator = null;
            this.movesHistory = [];
            return;
        }

        // Build movesHistory with analysis data from state
        const newMovesHistory = moves.map((move) => {
            const moveData = typeof move === 'string' ? { uci: move, san: move } : move;
            const state = this.stateManager.state;

            // moveAnalysis is an array, find the matching entry
            const moveUci = moveData.uci || moveData.san;
            const analysis = Array.isArray(state.moveAnalysis)
                ? state.moveAnalysis.find(a => a.move_uci === moveUci)
                : null;

            return {
                san: moveData.san || moveData.uci,
                uci: moveUci,
                evaluation: analysis?.evaluation || null,
                commentary: analysis?.commentary || null
            };
        });

        // Check if moves array has changed (length or content)
        const movesChanged = newMovesHistory.length !== this.movesHistory.length;

        // Update instance variable
        this.movesHistory = newMovesHistory;

        // If moves changed, recreate navigator
        if (movesChanged || !this.navigator) {
            console.log('Moves changed or no navigator, reinitializing. Old count:', this.navigator ? 'exists' : 'none', 'New count:', this.movesHistory.length);
            this.initializeNavigator();
        } else {
            // Just re-render at current position
            this.renderMoveList(this.movesHistory, this.navigator.getCurrentIndex());
        }
    }

    /**
     * Initialize move navigator
     */
    initializeNavigator() {
        // Store current position if navigator exists
        const wasReviewing = this.isReviewingHistory;
        const currentIndex = this.navigator ? this.navigator.getCurrentIndex() : -1;

        this.navigator = createMoveNavigator({
            board: this.board,
            game: this.chessGame,
            moves: this.movesHistory,
            onMoveChange: (moveIndex, _fen, moveData) => {
                this.isReviewingHistory = !this.navigator.isAtEnd();

                // Update commentary panel when reviewing
                if (this.isReviewingHistory && moveData && moveData.evaluation) {
                    // Include commentary in the evaluation object
                    const evaluationWithCommentary = {
                        ...moveData.evaluation,
                        commentary: moveData.commentary
                    };
                    this.displayEvaluation(evaluationWithCommentary);
                } else if (!this.isReviewingHistory) {
                    // At current position - show most recent player move evaluation
                    const lastPlayerMove = this.findLastPlayerMoveWithEvaluation(this.movesHistory);
                    if (lastPlayerMove && lastPlayerMove.evaluation) {
                        const evaluationWithCommentary = {
                            ...lastPlayerMove.evaluation,
                            commentary: lastPlayerMove.commentary
                        };
                        this.displayEvaluation(evaluationWithCommentary);
                    }
                }

                // Update move list display
                this.renderMoveList(this.movesHistory, moveIndex);
            },
            onHistoryUpdate: () => {
                this.renderMoveList(this.movesHistory, this.navigator.getCurrentIndex());
            }
        });

        // Setup keyboard shortcuts (only once)
        if (!this.keyboardSetup) {
            setupNavigationKeyboard(this.navigator, () => {
                return this.stateManager.state.status !== 'not_started';
            });
            this.keyboardSetup = true;
        }

        // Decide where to navigate
        if (this.movesHistory.length > 0) {
            if (wasReviewing && currentIndex >= 0 && currentIndex < this.movesHistory.length) {
                // Restore previous position if reviewing
                this.navigator.goToMove(currentIndex);
            } else {
                // Go to latest move if not reviewing or for new navigator
                this.navigator.goToMove(this.movesHistory.length - 1);
            }
        }
    }

    /**
     * Render move list with current move highlighted
     */
    renderMoveList(movesHistory, currentIndex) {
        const moveListEl = document.getElementById('movesList');
        if (!moveListEl) return;

        renderCurrentMoveOnly(movesHistory, moveListEl, currentIndex, (index) => {
            if (this.navigator) {
                this.navigator.goToMove(index);
            }
        });
    }

    /**
     * Find last player (White) move with evaluation
     */
    findLastPlayerMoveWithEvaluation(movesHistory) {
        // White moves are at even indices (0, 2, 4, etc.)
        for (let i = movesHistory.length - 1; i >= 0; i--) {
            if (i % 2 === 0 && movesHistory[i] && movesHistory[i].evaluation) {
                return movesHistory[i];
            }
        }
        return null;
    }

    /**
     * Set status message
     */
    setStatus(message, type = 'info') {
        const statusEl = document.getElementById('status');
        if (statusEl) {
            statusEl.textContent = message;
            statusEl.className = `status status-${type}`;
        }

        // Also update mobile status text
        const statusTextEl = document.getElementById('statusText');
        if (statusTextEl) {
            statusTextEl.textContent = message;
        }
    }

    /**
     * Highlight a square
     */
    highlightSquare(square) {
        const squareEl = document.querySelector(`.square-${square}`);
        if (squareEl) {
            squareEl.classList.add('selected-square');
        }
    }

    /**
     * Show possible moves for selected piece
     */
    showPossibleMoves(square) {
        const moves = this.chessGame.moves({ square: square, verbose: true });

        moves.forEach(move => {
            const squareEl = document.querySelector(`.square-${move.to}`);
            if (squareEl) {
                // Create move hint dot
                const dot = document.createElement('div');
                dot.className = 'move-hint';

                // Different style for capture moves
                if (move.captured) {
                    dot.classList.add('capture-hint');
                }

                squareEl.appendChild(dot);
            }
        });
    }

    /**
     * Clear selection
     */
    clearSelection() {
        this.selectedSquare = null;

        // Remove square highlights
        document.querySelectorAll('.selected-square').forEach(el => {
            el.classList.remove('selected-square');
        });

        // Remove move hints
        document.querySelectorAll('.move-hint').forEach(el => {
            el.remove();
        });
    }

    /**
     * Evaluate a player's move
     */
    async evaluatePlayerMove(fenBeforeMove, moveUci) {
        try {
            // Show loading state
            this.displayEvaluationLoading();

            const response = await fetch('/api/evaluate-move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    fen: fenBeforeMove,
                    move: moveUci
                })
            });

            const data = await response.json();

            if (data.success && data.evaluation) {
                const evaluation = data.evaluation;
                console.log('Move evaluation:', evaluation);

                // Display evaluation in commentary panel
                this.displayEvaluation(evaluation);
            }
        } catch (error) {
            console.error('Failed to evaluate move:', error);
            // Clear loading state on error
            const evalTextEl = document.getElementById('playEvaluationText');
            if (evalTextEl) {
                evalTextEl.innerHTML = '<span style="color: var(--error-color);">Failed to evaluate move</span>';
            }
        }
    }

    /**
     * Display loading state while evaluating move
     */
    displayEvaluationLoading() {
        const panelEl = document.getElementById('playCommentaryPanel');
        const evalTextEl = document.getElementById('playEvaluationText');
        const commentaryTextEl = document.getElementById('playCommentaryText');

        if (!panelEl || !evalTextEl) return;

        // Show panel
        panelEl.style.display = 'block';

        // Display loading state
        evalTextEl.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <div class="spinner"></div>
                <span>Evaluating move...</span>
            </div>
        `;

        // Hide commentary while loading
        if (commentaryTextEl) {
            commentaryTextEl.style.display = 'none';
        }
    }

    /**
     * Display move evaluation
     */
    displayEvaluation(evaluation) {
        const panelEl = document.getElementById('playCommentaryPanel');
        const evalTextEl = document.getElementById('playEvaluationText');
        const commentaryTextEl = document.getElementById('playCommentaryText');

        if (!panelEl || !evalTextEl) return;

        // Use the shared utility function for consistent styling
        renderMoveEvaluation(evaluation, evalTextEl, { showPosition: true });

        // Display commentary if available
        if (evaluation.commentary && commentaryTextEl) {
            commentaryTextEl.textContent = evaluation.commentary;
            commentaryTextEl.style.display = 'block';
        } else if (commentaryTextEl) {
            commentaryTextEl.style.display = 'none';
        }

        // Show the panel
        panelEl.style.display = 'block';
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Note: newGameBtn listener is now set up in showResumeGameModal()
        // to avoid conflicts with the modal flow

        // Resign button
        const resignBtn = document.getElementById('resignBtn');
        if (resignBtn) {
            resignBtn.addEventListener('click', () => this.resignGame());
        }

        // Settings button
        const settingsBtn = document.getElementById('settingsBtn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => this.openSettingsModal());
        }

        // Navigation buttons
        const prevMoveBtn = document.getElementById('prevMoveBtn');
        const nextMoveBtn = document.getElementById('nextMoveBtn');

        if (prevMoveBtn) {
            prevMoveBtn.addEventListener('click', () => {
                if (this.navigator) {
                    this.navigator.goPrevious();
                }
            });
        }

        if (nextMoveBtn) {
            nextMoveBtn.addEventListener('click', () => {
                if (this.navigator) {
                    this.navigator.goNext();
                }
            });
        }

        // Best move button
        const getBestMoveBtn = document.getElementById('getBestMoveBtn');
        if (getBestMoveBtn) {
            getBestMoveBtn.addEventListener('click', () => this.getBestMove());
        }

        // Best move modal close button
        const closeBestMoveBtn = document.querySelector('.close-best-move-modal');
        if (closeBestMoveBtn) {
            closeBestMoveBtn.addEventListener('click', () => this.closeBestMoveModal());
        }

        const bestMoveModal = document.getElementById('bestMoveModal');
        if (bestMoveModal) {
            bestMoveModal.addEventListener('click', (e) => {
                if (e.target === bestMoveModal) {
                    this.closeBestMoveModal();
                }
            });
        }

        // Settings modal listeners
        const saveSettingsBtn = document.getElementById('saveSettingsBtn');
        if (saveSettingsBtn) {
            saveSettingsBtn.addEventListener('click', () => this.saveSettings());
        }

        const closeModalBtn = document.querySelector('.close-modal');
        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', () => this.closeSettingsModal());
        }

        const settingsModal = document.getElementById('settingsModal');
        if (settingsModal) {
            settingsModal.addEventListener('click', (e) => {
                if (e.target === settingsModal) {
                    this.closeSettingsModal();
                }
            });
        }
    }

    /**
     * Resign current game
     */
    async resignGame() {
        if (!confirm('Are you sure you want to resign?')) {
            return;
        }

        try {
            const response = await fetch('/api/resign', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });

            const data = await response.json();

            if (data.success) {
                this.setStatus('Game resigned', 'info');
                this.stateManager.stopPolling();
            } else {
                alert('Failed to resign: ' + data.error);
            }
        } catch (error) {
            alert('Error resigning: ' + error.message);
        }
    }

    /**
     * Get best move for current position
     */
    async getBestMove() {
        const btn = document.getElementById('getBestMoveBtn');
        const isMobile = window.innerWidth <= 768;

        // Check if reviewing history
        if (this.isReviewingHistory) {
            const messageHtml = '<div style="text-align: center; padding: 20px; color: #666;">Navigate to current position to see best move.</div>';
            if (isMobile) {
                this.openBestMoveModal();
                document.getElementById('bestMoveModalContent').innerHTML = messageHtml;
            } else {
                document.getElementById('bestMovePanel').style.display = 'block';
                document.getElementById('bestMoveResult').innerHTML = messageHtml;
            }
            return;
        }

        // Show loading state
        if (btn) btn.disabled = true;
        if (isMobile) {
            this.openBestMoveModal();
            document.getElementById('bestMoveModalContent').innerHTML = '<div style="text-align: center; padding: 20px;">Loading...</div>';
        } else {
            const panel = document.getElementById('bestMovePanel');
            const resultEl = document.getElementById('bestMoveResult');
            panel.style.display = 'block';
            resultEl.innerHTML = '<div style="text-align: center; padding: 20px;">Loading...</div>';
        }

        try {
            const moveHistory = this.chessGame.history();
            const moveNumber = Math.floor(moveHistory.length / 2) + 1;

            const response = await fetch('/api/analyze-best-move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    fen: this.chessGame.fen(),
                    context: { move_number: moveNumber }
                })
            });

            const data = await response.json();

            if (data.success) {
                this.displayBestMoveResult(data, isMobile);
                if (btn) btn.disabled = false;
            } else {
                const errorHtml = `<div class="error">Error: ${data.error || 'No analysis available.'}</div>`;
                if (isMobile) {
                    document.getElementById('bestMoveModalContent').innerHTML = errorHtml;
                } else {
                    document.getElementById('bestMoveResult').innerHTML = errorHtml;
                }
                if (btn) btn.disabled = false;
            }
        } catch (error) {
            const errorHtml = `<div class="error">Error: ${error.message}</div>`;
            if (isMobile) {
                document.getElementById('bestMoveModalContent').innerHTML = errorHtml;
            } else {
                document.getElementById('bestMoveResult').innerHTML = errorHtml;
            }
            if (btn) btn.disabled = false;
        }
    }

    /**
     * Display best move result
     */
    displayBestMoveResult(data, isMobile) {
        let html = `<div class="move-display">${data.best_move}</div>`;
        html += `<div class="eval-display">${data.evaluation_text}</div>`;

        if (data.pv_line && data.pv_line.length > 1) {
            html += `<div class="pv-line"><div class="pv-label">Best continuation</div>${data.pv_line.join(' ')}</div>`;
        }

        if (data.commentary) {
            html += `<div class="commentary">${data.commentary}</div>`;
        }

        if (isMobile) {
            document.getElementById('bestMoveModalContent').innerHTML = html;
        } else {
            document.getElementById('bestMoveResult').innerHTML = html;
        }
    }

    /**
     * Open best move modal (mobile)
     */
    openBestMoveModal() {
        const modal = document.getElementById('bestMoveModal');
        if (modal) {
            modal.style.display = 'flex';
        }
    }

    /**
     * Close best move modal (mobile)
     */
    closeBestMoveModal() {
        const modal = document.getElementById('bestMoveModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    /**
     * Open settings modal
     */
    openSettingsModal() {
        const modal = document.getElementById('settingsModal');
        if (modal) {
            modal.style.display = 'flex';
        }
    }

    /**
     * Close settings modal
     */
    closeSettingsModal() {
        const modal = document.getElementById('settingsModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    /**
     * Save settings
     */
    saveSettings() {
        const selectedTheme = document.getElementById('boardTheme')?.value;
        if (selectedTheme) {
            localStorage.setItem('boardTheme', selectedTheme);
            applyBoardTheme(selectedTheme);
        }
        this.closeSettingsModal();
    }
}

// ==================== APPLICATION ====================

class ChessApp {
    constructor() {
        this.stateManager = new GameStateManager();
        this.uiController = new UIController(this.stateManager);
    }

    /**
     * Initialize application
     */
    async init() {
        console.log('Initializing Chess Elegante...');

        // Load board theme
        this.loadBoardTheme();

        // Setup mobile interactions
        this.setupMobileInteractions();

        // Setup bottom tabs
        this.setupBottomTabs();

        // Check for active game
        await this.checkForActiveGame();
    }

    /**
     * Check for active game and show resume modal if exists
     */
    async checkForActiveGame() {
        try {
            const response = await fetch('/api/game-state');
            const data = await response.json();

            if (data.success && data.game_id && data.status === 'started') {
                // Show resume game modal only if game is in progress
                this.showResumeGameModal(data);
            } else {
                // No active game or game is finished, show settings modal to start new game
                this.showSettingsModal();
            }
        } catch (error) {
            // Show settings modal to start new game
            this.showSettingsModal();
        }
    }

    /**
     * Resume the active game
     */
    resumeActiveGame(gameData) {
        console.log('Resuming active game:', gameData.game_id);
        this.stateManager.updateState(gameData);

        // Only start polling if it's AI's turn
        if (!gameData.is_player_turn && gameData.status === 'started') {
            console.log('AI turn - starting polling');
            this.stateManager.startPolling(1000);
        } else {
            console.log('Player turn - no polling needed');
        }
    }

    /**
     * Start a new game
     */
    async startNewGame(level, playerColor = 'white', engineType = 'stockfish') {
        try {
            const response = await fetch('/api/new-game', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    level,
                    player_color: playerColor,
                    engine_type: engineType
                })
            });

            const data = await response.json();

            if (data.success) {
                // Fetch initial game state
                const stateResponse = await fetch('/api/game-state');
                const stateData = await stateResponse.json();

                if (stateData.success) {
                    this.stateManager.updateState(stateData);
                    this.stateManager.startPolling();
                }
            } else {
                alert('Failed to start game: ' + data.error);
            }
        } catch (error) {
            alert('Error starting game: ' + error.message);
        }
    }

    /**
     * Show resume game modal
     */
    showResumeGameModal(gameData) {
        const modal = document.getElementById('resumeGameModal');
        const gameInfo = document.getElementById('activeGameInfo');

        if (!modal) {
            console.error('Resume game modal not found!');
            return;
        }

        // Display game info
        const moveCount = gameData.moves?.length || 0;
        const engineName = gameData.engine_type === 'lichess' ? 'Lichess' : 'Stockfish';

        gameInfo.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: 8px;">
                <div><strong>Engine:</strong> ${engineName}</div>
                <div><strong>Your Color:</strong> ${gameData.player_color}</div>
                <div><strong>AI Level:</strong> ${gameData.ai_level}</div>
                <div><strong>Moves Played:</strong> ${moveCount}</div>
                <div><strong>Status:</strong> ${gameData.status}</div>
            </div>
        `;

        modal.style.display = 'flex';

        // Store game data temporarily
        this.pendingGameData = gameData;

        // Setup event listeners (only once)
        if (!this.resumeListenersSetup) {
            document.getElementById('resumeGameBtn').addEventListener('click', () => {
                modal.style.display = 'none';
                this.resumeActiveGame(this.pendingGameData);
            });

            document.getElementById('newGameBtn').addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                modal.style.display = 'none';
                this.showSettingsModal();
            });

            this.resumeListenersSetup = true;
        }
    }

    /**
     * Show settings modal for new game
     */
    showSettingsModal() {
        const modal = document.getElementById('gameSettingsModal');
        if (!modal) {
            console.error('Game settings modal not found!');
            return;
        }
        modal.style.display = 'flex';

        // Setup event listeners (only once)
        if (!this.settingsListenersSetup) {
            // Close button
            const closeBtn = modal.querySelector('.close-modal');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    modal.style.display = 'none';
                });
            }

            // Click outside to close
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.style.display = 'none';
                }
            });

            // Engine type change listener
            document.getElementById('engineType').addEventListener('change', (e) => {
                const aiLevelSelect = document.getElementById('aiLevel');
                const engineType = e.target.value;

                if (engineType === 'stockfish') {
                    aiLevelSelect.innerHTML = `
                        <option value="1">Level 1 - ~1320 Elo</option>
                        <option value="2">Level 2 - ~1400 Elo</option>
                        <option value="3" selected>Level 3 - ~1500 Elo</option>
                        <option value="4">Level 4 - ~1700 Elo</option>
                        <option value="5">Level 5 - ~1900 Elo</option>
                    `;
                } else {
                    aiLevelSelect.innerHTML = `
                        <option value="1">Level 1 - Beginner</option>
                        <option value="2">Level 2 - Casual</option>
                        <option value="3">Level 3 - Intermediate</option>
                        <option value="4">Level 4 - Advanced</option>
                        <option value="5" selected>Level 5 - Strong</option>
                        <option value="6">Level 6 - Very Strong</option>
                        <option value="7">Level 7 - Expert</option>
                        <option value="8">Level 8 - Master</option>
                    `;
                }
            });

            // Start game button
            document.getElementById('startGameBtn').addEventListener('click', async () => {
                const level = parseInt(document.getElementById('aiLevel').value);
                const playerColor = document.getElementById('playerColor').value;
                const engineType = document.getElementById('engineType').value;

                modal.style.display = 'none';
                await this.startNewGame(level, playerColor, engineType);
            });

            this.settingsListenersSetup = true;
        }
    }

    /**
     * Load board theme
     */
    loadBoardTheme() {
        const theme = localStorage.getItem('boardTheme') || 'minimal';
        const boardEl = document.getElementById('board');
        if (boardEl) {
            boardEl.className = `board-theme-${theme}`;
        }
    }

    /**
     * Setup mobile interactions
     */
    setupMobileInteractions() {
        // Prevent zoom on double-tap
        let lastTouchEnd = 0;
        document.addEventListener('touchend', (e) => {
            const now = Date.now();
            if (now - lastTouchEnd <= 300) {
                e.preventDefault();
            }
            lastTouchEnd = now;
        }, false);
    }

    /**
     * Setup bottom tabs (mobile)
     */
    setupBottomTabs() {
        const bottomTabs = document.querySelector('.mobile-bottom-tabs');
        if (!bottomTabs) return;

        // Check if we're on mobile (bottom tabs visible)
        const isMobile = window.innerWidth <= 767;

        if (isMobile) {
            // Move analysis panel (with move history + commentary) into history tab
            const historyTab = document.getElementById('historyTab');
            const rightPanel = document.querySelector('.right-panel .analysis-panel');

            if (historyTab && rightPanel) {
                historyTab.appendChild(rightPanel);
            }
        }
    }
}

// ==================== INITIALIZATION ====================

let app;

document.addEventListener('DOMContentLoaded', () => {
    app = new ChessApp();
    app.init();
});

// Export for global access
window.ChessApp = ChessApp;
window.app = app;
