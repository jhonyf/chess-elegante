// Chess Learning Pages - Unified JavaScript
// Used by: openings.html, tactics.html, strategy.html, endgames.html
// Handles search, board interactions, and navigation

class LessonBoard {
    constructor(boardId, moves) {
        this.boardId = boardId;
        this.moves = moves;
        this.board = null;
        this.game = new Chess();
        this.currentMoveIndex = -1;
        this.isInitialized = false;
    }

    toggle() {
        const section = document.getElementById(`board-section-${this.boardId}`);
        const toggleBtn = document.querySelector(`[data-board-id="${this.boardId}"]`);
        const arrow = toggleBtn.querySelector('.toggle-arrow');

        if (section.classList.contains('expanded')) {
            section.classList.remove('expanded');
            arrow.textContent = '▼';
        } else {
            section.classList.add('expanded');
            arrow.textContent = '▲';

            if (!this.isInitialized) {
                this.initBoard();
                this.isInitialized = true;
            }
        }
    }

    initBoard() {
        const config = {
            draggable: false,
            position: 'start',
            pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png'
        };

        this.board = Chessboard(`board-${this.boardId}`, config);
        this.loadBoardTheme();
        this.updateMoveCounter();
    }

    loadBoardTheme() {
        const savedTheme = localStorage.getItem('boardTheme') || 'minimal';
        this.applyBoardTheme(savedTheme);
    }

    applyBoardTheme(theme) {
        const boardElement = document.getElementById(`board-${this.boardId}`);
        const themeClasses = ['board-theme-minimal', 'board-theme-classic', 'board-theme-gray',
                            'board-theme-blue', 'board-theme-wood', 'board-theme-green'];
        themeClasses.forEach(cls => boardElement.classList.remove(cls));
        boardElement.classList.add(`board-theme-${theme}`);
    }

    goToMove(moveIndex) {
        this.game = new Chess();
        for (let i = 0; i <= moveIndex; i++) {
            if (i < this.moves.length) {
                this.game.move(this.moves[i], { sloppy: true });
            }
        }
        this.currentMoveIndex = moveIndex;
        this.board.position(this.game.fen());
        this.updateMoveCounter();
    }

    goToFirstMove() {
        this.game = new Chess();
        this.currentMoveIndex = -1;
        this.board.position(this.game.fen());
        this.updateMoveCounter();
    }

    goPreviousMove() {
        if (this.currentMoveIndex < 0) return;
        this.currentMoveIndex--;
        if (this.currentMoveIndex < 0) {
            this.goToFirstMove();
        } else {
            this.goToMove(this.currentMoveIndex);
        }
    }

    goNextMove() {
        if (this.currentMoveIndex >= this.moves.length - 1) return;
        this.currentMoveIndex++;
        this.goToMove(this.currentMoveIndex);
    }

    goToLastMove() {
        if (this.moves.length > 0) {
            this.currentMoveIndex = this.moves.length - 1;
            this.goToMove(this.currentMoveIndex);
        }
    }

    updateMoveCounter() {
        const counter = document.getElementById(`move-counter-${this.boardId}`);
        if (!counter) return;

        if (this.currentMoveIndex === -1) {
            counter.textContent = 'Starting Position';
        } else {
            const moveNumber = Math.floor(this.currentMoveIndex / 2) + 1;
            const color = this.currentMoveIndex % 2 === 0 ? 'White' : 'Black';
            counter.textContent = `Move ${moveNumber}. ${this.moves[this.currentMoveIndex]} (${color})`;
        }
    }
}

// Move sequences for all boards across all learning pages
const boardMoves = {
    // ==================== OPENINGS PAGE ====================
    // Section A: Principles
    'center-control': ['e4', 'e5', 'Nf3', 'Nc6', 'Bc4'],
    'development': ['e4', 'e5', 'Nf3', 'Nc6', 'Bc4', 'Bc5', 'O-O'],
    'king-safety': ['e4', 'e5', 'Nf3', 'Nc6', 'Bc4', 'Bc5', 'c3', 'Nf6', 'O-O'],
    'tempo': ['e4', 'd5', 'exd5', 'Qxd5', 'Nc3', 'Qa5'],
    'queen-early': ['e4', 'e5', 'Qh5', 'Nc6', 'Bc4', 'g6', 'Qf3'],

    // Section B: Opening Families
    'open-games': ['e4', 'e5', 'Nf3', 'Nc6', 'Bc4', 'Bc5'],
    'semi-open': ['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4', 'Nxd4', 'Nf6', 'Nc3'],
    'closed-games': ['d4', 'd5', 'c4', 'e6', 'Nc3', 'Nf6', 'Bg5'],
    'indian-defenses': ['d4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6'],
    'flank-openings': ['c4', 'e5', 'Nc3', 'Nf6', 'Nf3', 'Nc6', 'g3'],

    // Section C: Popular Openings
    'italian-game': ['e4', 'e5', 'Nf3', 'Nc6', 'Bc4', 'Bc5', 'c3', 'Nf6', 'd4'],
    'ruy-lopez': ['e4', 'e5', 'Nf3', 'Nc6', 'Bb5', 'a6', 'Ba4', 'Nf6', 'O-O'],
    'sicilian-defense': ['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4', 'Nxd4', 'Nf6', 'Nc3'],
    'french-defense': ['e4', 'e6', 'd4', 'd5', 'Nc3', 'Nf6', 'Bg5'],
    'queens-gambit': ['d4', 'd5', 'c4', 'e6', 'Nc3', 'Nf6', 'Bg5', 'Be7', 'e3'],
    'kings-indian': ['d4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6', 'Nf3', 'O-O'],
    'london-system': ['d4', 'd5', 'Bf4', 'Nf6', 'e3', 'e6', 'Nf3', 'c5', 'c3'],
    'caro-kann': ['e4', 'c6', 'd4', 'd5', 'Nc3', 'dxe4', 'Nxe4', 'Bf5'],
    'english-opening': ['c4', 'e5', 'Nc3', 'Nf6', 'Nf3', 'Nc6', 'g3', 'Bb4'],
    'scandinavian': ['e4', 'd5', 'exd5', 'Qxd5', 'Nc3', 'Qa5', 'd4', 'Nf6'],
    'nimzo-indian': ['d4', 'Nf6', 'c4', 'e6', 'Nc3', 'Bb4', 'Qc2', 'O-O'],
    'catalan': ['d4', 'Nf6', 'c4', 'e6', 'g3', 'd5', 'Bg2', 'Be7', 'Nf3'],

    // ==================== TACTICS PAGE ====================
    // Section A: Tactical Motifs
    'fork': ['e4', 'e5', 'Nf3', 'Nc6', 'd4', 'exd4', 'Bc4', 'Bc5', 'O-O', 'Nf6', 'Ng5', 'd6', 'Nf7'],
    'pin': ['d4', 'Nf6', 'c4', 'e6', 'Nc3', 'd5', 'Bg5'],
    'skewer': ['e4', 'e5', 'Nf3', 'Nc6', 'Bc4', 'Bc5', 'O-O', 'd6', 'd3', 'Bg4', 'Bb5'],
    'discovered-attack': ['e4', 'e5', 'Nf3', 'Nc6', 'Bb5', 'a6', 'Ba4', 'Nf6', 'd3', 'b5', 'Bb3', 'd6', 'Bg5', 'Qd7', 'Bxf6', 'gxf6', 'Nc3', 'Bg7', 'Nd5', 'O-O', 'Ne7+'],
    'double-attack': ['e4', 'e5', 'Nf3', 'Nc6', 'Bc4', 'Nf6', 'd3', 'Be7', 'O-O', 'd6', 'Ng5', 'O-O', 'Qh5'],
    'removing-defender': ['e4', 'e5', 'Nf3', 'Nc6', 'd4', 'exd4', 'Nxd4', 'Bc5', 'Nxc6', 'Qf6', 'Qd5', 'Qxc6', 'Qxc5'],

    // Section B: Tactical Themes
    'greek-gift': ['e4', 'e6', 'd4', 'd5', 'Nc3', 'Nf6', 'Bg5', 'Be7', 'e5', 'Nfd7', 'Bxe7', 'Qxe7', 'f4', 'O-O', 'Nf3', 'c5', 'Bd3', 'Nc6', 'O-O', 'f6', 'Qe2', 'cxd4', 'Nxd4', 'Nxd4', 'Qh5', 'fxe5', 'fxe5', 'Rxf1+', 'Rxf1', 'Nf6', 'Rxf6', 'gxf6', 'Qxh7+', 'Kxh7', 'Ng5+'],
    'back-rank': ['e4', 'e5', 'Nf3', 'Nc6', 'Bc4', 'Bc5', 'O-O', 'Nf6', 'd3', 'd6', 'Bg5', 'h6', 'Bh4', 'g5', 'Bg3', 'h5', 'h3', 'h4', 'Bh2', 'Bg4', 'hxg4', 'Nxg4', 'Nbd2', 'Qf6', 'Re1', 'O-O-O', 'Nf1', 'Rde8', 'Ne3', 'Nxe3', 'Rxe3', 'Nd4', 'Nxd4', 'Bxd4', 'Rd1', 'Rd8'],
    'deflection': ['e4', 'e5', 'Nf3', 'Nc6', 'Bb5', 'a6', 'Ba4', 'Nf6', 'O-O', 'Be7', 'Re1', 'b5', 'Bb3', 'd6', 'c3', 'O-O', 'd4', 'Bg4', 'Be3', 'exd4', 'cxd4', 'Na5', 'Bc2', 'c5', 'Nbd2', 'cxd4', 'Nxd4', 'Rc8', 'N2f3', 'Qd7', 'h3', 'Bh5', 'g4', 'Bg6', 'Bxg6', 'fxg6', 'e5', 'dxe5', 'Nxe5', 'Qd8', 'Rxd8'],
    'zwischenzug': ['e4', 'e5', 'Nf3', 'Nc6', 'Bb5', 'a6', 'Ba4', 'Nf6', 'O-O', 'Nxe4', 'Qe2', 'Nc5', 'd4', 'Nxa4', 'dxe5', 'Qe7', 'Nc3', 'Nxc3', 'bxc3'],

    // Section C: Common Patterns
    'outpost': ['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4', 'Nxd4', 'Nf6', 'Nc3', 'a6', 'Be3', 'e5', 'Nb3', 'Be6', 'f3', 'Be7', 'Qd2', 'O-O', 'O-O-O', 'Nbd7', 'g4', 'b5', 'g5', 'b4', 'Ne2', 'Ne8', 'f4', 'a5', 'Nxa5', 'Rxa5', 'b3', 'Qa8', 'Kb2', 'exf4', 'Nxf4', 'Ne5', 'Nd5', 'Bxd5', 'exd5', 'Nc5', 'Qxb4', 'Nd3+'],
    'weak-back-rank': ['e4', 'e5', 'Nf3', 'Nc6', 'Bb5', 'a6', 'Ba4', 'Nf6', 'O-O', 'Be7', 'Re1', 'b5', 'Bb3', 'd6', 'c3', 'O-O', 'h3', 'Na5', 'Bc2', 'c5', 'd4'],

    // ==================== STRATEGY PAGE ====================
    // Section A: Positional Concepts
    'good-bad-bishop': ['e4', 'e6', 'd4', 'd5', 'Nc3', 'Nf6', 'Bg5', 'Be7', 'e5', 'Nfd7', 'Bxe7', 'Qxe7'],
    'open-files': ['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4', 'Nxd4', 'Nf6', 'Nc3', 'a6', 'Be3', 'e6', 'f3', 'Be7', 'Qd2', 'O-O', 'O-O-O', 'Qc7', 'g4', 'Nc6', 'Nxc6', 'bxc6'],
    'weak-squares': ['e4', 'c5', 'Nf3', 'e6', 'd4', 'cxd4', 'Nxd4', 'a6', 'Nc3', 'Qc7', 'Be3', 'Nf6', 'Qd2', 'Be7', 'O-O-O', 'O-O', 'f3', 'Nc6', 'Kb1', 'Nxd4', 'Bxd4', 'b5', 'Nd5'],
    'passed-pawns': ['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4', 'Nxd4', 'Nf6', 'Nc3', 'a6', 'Be3', 'e5', 'Nb3', 'Be6', 'Qd2', 'Be7', 'f3', 'O-O', 'O-O-O', 'Nbd7', 'Kb1', 'b5', 'Nd5'],
    'space-advantage': ['e4', 'e6', 'd4', 'd5', 'Nc3', 'Nf6', 'e5', 'Nfd7', 'f4', 'c5', 'Nf3', 'Nc6', 'Be3'],

    // Section B: Pawn Structures
    'iqp': ['d4', 'd5', 'c4', 'e6', 'Nc3', 'Nf6', 'Bg5', 'Be7', 'e3', 'O-O', 'Nf3', 'Nbd7', 'Rc1', 'c6', 'Bd3', 'dxc4', 'Bxc4'],
    'hanging-pawns': ['d4', 'Nf6', 'c4', 'e6', 'Nf3', 'd5', 'Nc3', 'c5', 'cxd5', 'Nxd5', 'e3', 'Nc6', 'Bd3', 'cxd4', 'exd4'],
    'carlsbad': ['d4', 'd5', 'c4', 'e6', 'Nc3', 'Nf6', 'Bg5', 'Be7', 'e3', 'O-O', 'Nf3', 'Nbd7', 'Rc1', 'c6', 'Bd3', 'dxc4', 'Bxc4', 'Nd5', 'Bxe7', 'Qxe7', 'O-O', 'Nxc3', 'Rxc3'],

    // Section C: How to Make a Plan
    'improve-piece': ['e4', 'e5', 'Nf3', 'Nc6', 'Bb5', 'a6', 'Ba4', 'Nf6', 'O-O', 'Be7', 'Re1', 'b5', 'Bb3', 'd6', 'c3', 'O-O', 'h3', 'Na5', 'Bc2', 'c5', 'd4', 'Qc7', 'Nbd2', 'Nc6', 'Nf1', 'cxd4', 'cxd4', 'Bd7', 'Ne3'],
    'create-weakness': ['e4', 'e5', 'Nf3', 'Nc6', 'Bb5', 'a6', 'Ba4', 'Nf6', 'O-O', 'Be7', 'Re1', 'b5', 'Bb3', 'd6', 'c3', 'O-O', 'h3', 'Na5', 'Bc2', 'c5', 'd4', 'Qc7', 'Nbd2', 'cxd4', 'cxd4', 'Bb7', 'Nf1', 'Rac8', 'Ne3', 'g6'],
    'attack-space': ['d4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6', 'Nf3', 'O-O', 'Be2', 'e5', 'O-O', 'Nc6', 'Be3', 'Ng4', 'Bg5', 'f6', 'Bh4', 'Nh6', 'd5', 'Ne7'],
    'when-trade': ['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4', 'Nxd4', 'Nf6', 'Nc3', 'a6', 'Be3', 'e5', 'Nb3', 'Be6', 'f3', 'Be7', 'Qd2', 'O-O', 'O-O-O', 'Nbd7', 'g4'],

    // ==================== ENDGAMES PAGE ====================
    // Section A: Basic Checkmates
    'queen-king-mate': ['Kd5', 'Kf6', 'Qe4', 'Kg7', 'Ke5', 'Kf7', 'Kf5', 'Kg7', 'Qe6', 'Kh7', 'Qf7', 'Kh8', 'Qg6', 'Kh9', 'Kg5', 'Kh8', 'Kh6', 'Kg8', 'Qg7#'],
    'rook-king-mate': ['Kd5', 'Kf6', 'Re1', 'Kg7', 'Ke5', 'Kf7', 'Kf5', 'Kg7', 'Re7+', 'Kf8', 'Kf6', 'Kg8', 'Rg7+', 'Kh8', 'Kg6', 'Ka8', 'Kh6', 'Kb8', 'Ra7', 'Kc8', 'Kg7', 'Kd8', 'Kf7', 'Ke8', 'Ra8#'],
    'two-rooks-mate': ['Ra4', 'Kd5', 'Rb5+', 'Kc6', 'Ra6+', 'Kd7', 'Rb7+', 'Ke8', 'Ra8#'],
    'two-bishops-mate': ['Ke6', 'Ka8', 'Bd5', 'Kb8', 'Bc5', 'Ka8', 'Bb6', 'Kb8', 'Kd7', 'Ka8', 'Kc7', 'Ka7', 'Bc6', 'Ka6', 'Bb7+', 'Ka5', 'Kc6', 'Ka4', 'Bb5+', 'Ka5', 'Bd4', 'Ka4', 'Bc4', 'Ka5', 'Bc3#'],
    'bishop-knight-mate': ['Kf6', 'Kh8', 'Nf7+', 'Kg8', 'Bb7', 'Kh7', 'Kg5', 'Kg7', 'Kg6', 'Kg8', 'Nd6', 'Kh8', 'Nf7+', 'Kg8', 'Be4', 'Kf8', 'Kf6', 'Ke8', 'Ke6', 'Kf8', 'Kd7', 'Kg7', 'Ke7', 'Kg6', 'Bf5+', 'Kg7', 'Ne5', 'Kg8', 'Kf6', 'Kh8', 'Kg6', 'Kg8', 'Nd7', 'Kh8', 'Nf6', 'Kg8', 'Bg6', 'Kh8', 'Bf7', 'Ka7', 'Nh5#'],

    // Section B: King & Pawn Endgames
    'opposition': ['Ke5', 'Ke7', 'e4', 'Kd7', 'Kf6', 'Ke8', 'e5', 'Kf8', 'Kf7', 'Kf7', 'e6+', 'Ke8', 'Ke7', 'Kd8', 'Kf8', 'Kd7', 'e7', 'Kd6', 'e8=Q'],
    'square-rule': ['h5', 'Ke6', 'h6', 'Kf6', 'Kg4', 'Kg6', 'Kh4', 'Kxh6'],
    'triangulation': ['Ke2', 'Ke7', 'Kd2', 'Kd7', 'Kd3', 'Ke7', 'Ke3', 'Kd7', 'Kf4', 'Ke6', 'Kg5', 'Kf7', 'Kf5', 'Kg7', 'Kg5', 'Kf7', 'Kh6', 'Kg8', 'g6', 'Kh8', 'g7+', 'Kg8', 'Kg6'],
    'outside-passed': ['a5', 'Kd7', 'a6', 'Kc6', 'Kb4', 'Kb6', 'Kc4', 'Kxa6', 'Kd5', 'Kb6', 'Kxe5', 'Kc6', 'Kxf5', 'Kd6', 'Kg6', 'Ke7', 'Kxh6', 'Kf7', 'Kh7'],

    // Section C: Rook Endgames
    'lucena': ['Re1', 'Ra2+', 'Kd7', 'Ra1', 'Re4', 'Rd1+', 'Ke6', 'Re1', 'Kf7', 'Rf1+', 'Kg6', 'Rg1+', 'Kf6', 'Rf1+', 'Kg5', 'e8=Q'],
    'philidor': ['Kf7', 'Ra6', 'Ke7', 'Ra1', 'e6', 'Rc1', 'Kf6', 'Rf1+', 'Ke5', 'Re1+', 'Kd6', 'Rd1+', 'Ke7', 'Re1'],
    'back-rank-defense': ['a6', 'Ra1', 'a7', 'Kg7', 'Kb6', 'Kb8', 'Kb7', 'Ra2', 'a8=Q+', 'Rxa8', 'Kxa8'],
    'rook-behind-pawn': ['Re1', 'Ke7', 'e5', 'Ke6', 'Kd4', 'Kd6', 'e6', 'Ke7', 'Ke5', 'Kf8', 'Kf6', 'Kg8', 'e7', 'Kh7', 'Kf7']
};

// Store all board instances
const lessonBoards = {};


// Initialize everything when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all boards
    for (const [boardId, moves] of Object.entries(boardMoves)) {
        lessonBoards[boardId] = new LessonBoard(boardId, moves);
    }

    // Setup toggle buttons
    document.querySelectorAll('.view-board-btn').forEach(btn => {
        const boardId = btn.getAttribute('data-board-id');
        if (boardId && lessonBoards[boardId]) {
            btn.addEventListener('click', () => {
                lessonBoards[boardId].toggle();
            });
        }
    });

    // Setup navigation controls using data attributes
    document.querySelectorAll('.control-btn').forEach(btn => {
        const action = btn.getAttribute('data-action');
        const boardId = btn.getAttribute('data-board');

        if (action && boardId && lessonBoards[boardId]) {
            btn.addEventListener('click', () => {
                switch (action) {
                    case 'first':
                        lessonBoards[boardId].goToFirstMove();
                        break;
                    case 'prev':
                        lessonBoards[boardId].goPreviousMove();
                        break;
                    case 'next':
                        lessonBoards[boardId].goNextMove();
                        break;
                    case 'last':
                        lessonBoards[boardId].goToLastMove();
                        break;
                }
            });
        }
    });

    // Keyboard navigation for expanded boards
    document.addEventListener('keydown', (e) => {
        // Find the currently visible/expanded board
        const expandedSection = document.querySelector('.board-section.expanded');
        if (!expandedSection) return;

        const boardId = expandedSection.id.replace('board-section-', '');
        const board = lessonBoards[boardId];
        if (!board) return;

        // Only handle arrow keys when not in search input
        if (document.activeElement === document.getElementById('search-input')) return;

        switch (e.key) {
            case 'ArrowLeft':
                board.goPreviousMove();
                e.preventDefault();
                break;
            case 'ArrowRight':
                board.goNextMove();
                e.preventDefault();
                break;
            case 'Home':
                board.goToFirstMove();
                e.preventDefault();
                break;
            case 'End':
                board.goToLastMove();
                e.preventDefault();
                break;
        }
    });

    // Classical games are now loaded statically in HTML for SEO
});
