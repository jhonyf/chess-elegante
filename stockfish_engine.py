import chess
import chess.engine
import os
import logging
from datetime import datetime


class StockfishEngine:
    def __init__(self, stockfish_path=None, log_file='stockfish_engine.log'):
        """
        Initialize Stockfish engine
        stockfish_path: Path to stockfish binary (auto-detects if not provided)
        log_file: Path to log file for engine outputs
        """
        # Set up logging
        self.logger = logging.getLogger('StockfishEngine')

        # Create file handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)

        # Create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)

        # Create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        # Add the handlers to the logger
        if not self.logger.handlers:
            self.logger.addHandler(fh)
            self.logger.addHandler(ch)

        if stockfish_path is None:
            # Try common locations
            possible_paths = [
                '/opt/homebrew/bin/stockfish',  # Homebrew on Apple Silicon
                '/usr/local/bin/stockfish',     # Homebrew on Intel Mac
                '/usr/games/stockfish',         # Debian/Ubuntu
                '/usr/bin/stockfish',           # Other Linux
                'stockfish'                      # In PATH
            ]

            for path in possible_paths:
                if path == 'stockfish':
                    # Try as last resort (assumes in PATH)
                    stockfish_path = path
                    break
                elif os.path.exists(path):
                    stockfish_path = path
                    break

        if not stockfish_path:
            raise Exception("Stockfish not found. Please install Stockfish.")

        self.stockfish_path = stockfish_path
        self.engine = None

    def start(self):
        """Start the engine"""
        if self.engine is None:
            self.logger.info(f"Starting Stockfish engine from path: {self.stockfish_path}")
            self.engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
            self.logger.info("Stockfish engine started successfully")

    def stop(self):
        """Stop the engine"""
        if self.engine:
            self.logger.info("Stopping Stockfish engine")
            self.engine.quit()
            self.engine = None
            self.logger.info("Stockfish engine stopped")

    def analyze_position(self, fen, depth=20, multipv=3):
        """
        Analyze a position and return evaluation

        Args:
            fen: FEN string of position
            depth: Search depth (default 20)
            multipv: Number of principal variations (default 3)

        Returns:
            dict with analysis results
        """
        self.start()

        try:
            board = chess.Board(fen)
            self.logger.info(f"Analyzing position: {fen}")
            self.logger.info(f"Turn: {'White' if board.turn else 'Black'}")

            # Analyze with multiple principal variations
            info = self.engine.analyse(
                board,
                chess.engine.Limit(depth=depth),
                multipv=multipv
            )

            self.logger.debug(f"Raw Stockfish analysis info: {info}")

            # Format results
            results = {
                'fen': fen,
                'depth': depth,
                'pvs': []
            }

            # Process each principal variation
            for pv_info in info:
                pv_data = {
                    'moves': [],
                    'san_moves': []
                }

                # Get score
                score = pv_info.get('score')
                if score:
                    # Convert score to white's perspective
                    score_white = score.white()

                    if score_white.is_mate():
                        pv_data['mate'] = score_white.mate()
                    else:
                        pv_data['cp'] = score_white.score()

                # Get principal variation (best line)
                pv = pv_info.get('pv')
                if pv:
                    temp_board = board.copy()
                    for move in pv:
                        pv_data['moves'].append(move.uci())
                        pv_data['san_moves'].append(temp_board.san(move))
                        temp_board.push(move)

                # Add additional info
                if 'depth' in pv_info:
                    pv_data['depth'] = pv_info['depth']
                if 'nodes' in pv_info:
                    pv_data['nodes'] = pv_info['nodes']
                if 'time' in pv_info:
                    pv_data['time'] = pv_info['time']

                results['pvs'].append(pv_data)

            self.logger.info(f"Analysis complete. Found {len(results['pvs'])} variations")
            for i, pv in enumerate(results['pvs']):
                eval_str = f"Mate in {pv['mate']}" if 'mate' in pv else f"CP: {pv.get('cp', 'N/A')}"
                self.logger.info(f"  PV {i+1}: {eval_str}, Moves: {' '.join(pv['san_moves'][:3])}")

            return results

        except Exception as e:
            self.logger.error(f"Analysis failed: {str(e)}")
            raise Exception(f"Analysis failed: {str(e)}")

    def get_best_move(self, fen, time_limit=1.0):
        """
        Get the best move for a position

        Args:
            fen: FEN string of position
            time_limit: Time limit in seconds

        Returns:
            dict with best move and evaluation
        """
        self.start()

        try:
            self.logger.info(f"Getting best move for position (time_limit: {time_limit}s)")
            board = chess.Board(fen)
            result = self.engine.play(board, chess.engine.Limit(time=time_limit))

            response = {
                'best_move': result.move.uci(),
                'best_move_san': board.san(result.move)
            }

            self.logger.info(f"Best move found: {response['best_move_san']} ({response['best_move']})")

            # Get evaluation if available
            info = self.engine.analyse(board, chess.engine.Limit(time=time_limit))
            if 'score' in info:
                score = info['score'].white()
                if score.is_mate():
                    response['mate'] = score.mate()
                    self.logger.info(f"Evaluation: Mate in {score.mate()}")
                else:
                    response['cp'] = score.score()
                    self.logger.info(f"Evaluation: {score.score()} cp")

            return response

        except Exception as e:
            self.logger.error(f"Failed to get best move: {str(e)}", exc_info=True)
            raise Exception(f"Failed to get best move: {str(e)}")

    def make_ai_move(self, fen, skill_level=3):
        """
        Make an AI move at a specific skill level (for playing against the engine)

        Args:
            fen: FEN string of current position
            skill_level: Difficulty level 1-5 mapping to Elo ratings:
                        1 = ~1320 Elo (Skill 0-2) - Minimum supported by Stockfish
                        2 = ~1400 Elo (Skill 5-7)
                        3 = ~1500 Elo (Skill 10-12)
                        4 = ~1700 Elo (Skill 14-16)
                        5 = ~1900 Elo (Skill 18-20)

        Returns:
            dict with move in UCI and SAN notation
        """
        self.start()

        try:
            # Map skill levels to Stockfish skill and Elo
            # Note: Stockfish UCI_Elo minimum is 1320
            skill_mapping = {
                1: {'skill': 1, 'elo': 1320},
                2: {'skill': 6, 'elo': 1400},
                3: {'skill': 11, 'elo': 1500},
                4: {'skill': 15, 'elo': 1700},
                5: {'skill': 19, 'elo': 1900}
            }

            config = skill_mapping.get(skill_level, skill_mapping[3])
            self.logger.info(f"Making AI move at skill level {skill_level} (Stockfish skill={config['skill']}, target Elo={config['elo']})")

            # Configure engine for limited strength
            self.engine.configure({
                "Skill Level": config['skill'],
                "UCI_LimitStrength": True,
                "UCI_Elo": config['elo']
            })

            board = chess.Board(fen)

            # Use shorter time for lower levels, longer for higher
            time_limit = 0.1 + (skill_level * 0.2)  # 0.3s to 1.1s

            result = self.engine.play(board, chess.engine.Limit(time=time_limit))

            response = {
                'move': result.move.uci(),
                'move_san': board.san(result.move)
            }

            self.logger.info(f"AI move: {response['move_san']} ({response['move']})")

            # Reset engine to full strength for analysis
            self.engine.configure({
                "Skill Level": 20,
                "UCI_LimitStrength": False
            })

            return response

        except Exception as e:
            self.logger.error(f"Failed to make AI move: {str(e)}", exc_info=True)
            raise Exception(f"Failed to make AI move: {str(e)}")

    def evaluate_move(self, fen, move_uci, previous_position_analysis=None):
        """
        Evaluate a specific move

        Args:
            fen: FEN string of position before the move
            move_uci: Move in UCI format (e.g., 'e2e4')
            previous_position_analysis: Optional analysis of this position from previous move
                                       (to avoid re-analyzing the same position)

        Returns:
            dict with move evaluation and comparison to best move
        """
        self.start()

        try:
            board = chess.Board(fen)
            move = chess.Move.from_uci(move_uci)

            if move not in board.legal_moves:
                raise Exception("Illegal move")

            # Get SAN notation before making the move
            move_san = board.san(move)
            side_to_move = board.turn  # True for White, False for Black

            self.logger.info(f"Evaluating move: {move_san} ({move_uci}) for {'White' if side_to_move else 'Black'}")

            # Get best move evaluation BEFORE the move
            # This tells us the evaluation if we played the best move
            if previous_position_analysis:
                # Reuse analysis from previous move's "after position"
                self.logger.info(f"♻️  Reusing position analysis from previous move")
                best_analysis = previous_position_analysis
            else:
                best_analysis = self.analyze_position(fen, depth=15, multipv=1)

            best_pv = best_analysis['pvs'][0]

            # Get the evaluation from Stockfish
            # IMPORTANT: Our analyze_position always returns cp from White's perspective (see line 114: score.white())
            best_move_eval_white = best_pv.get('cp', 0)

            self.logger.info(f"Best move: {best_pv['moves'][0] if best_pv['moves'] else 'None'}")
            self.logger.info(f"Best move evaluation (White POV): {best_move_eval_white}")

            # Make the actual move and evaluate resulting position
            board.push(move)
            after_analysis = self.analyze_position(board.fen(), depth=15, multipv=1)

            # Get evaluation after our move
            # IMPORTANT: This is also from White's perspective (see line 114: score.white())
            after_move_eval_white = after_analysis['pvs'][0].get('cp', 0)

            self.logger.info(f"After move evaluation (White POV): {after_move_eval_white}")

            # Check if the move hangs a piece (opponent can capture it immediately)
            move_hangs_piece = False
            best_opponent_response = after_analysis['pvs'][0].get('moves', [])
            if best_opponent_response:
                opponent_move_uci = best_opponent_response[0]
                # Check if opponent's best move is a capture of the piece we just moved
                if opponent_move_uci.endswith(move_uci[2:4]):  # Ends with our destination square
                    move_hangs_piece = True
                    self.logger.info(f"WARNING: Move hangs piece! Opponent can capture with {opponent_move_uci}")

            # Calculate move quality
            # Both evaluations are from White's perspective
            # Now convert to the player's perspective for accurate loss calculation
            if side_to_move:  # White played
                eval_before_player = best_move_eval_white
                eval_after_player = after_move_eval_white
            else:  # Black played
                # Negate for Black's perspective (Black wants negative scores)
                eval_before_player = -best_move_eval_white
                eval_after_player = -after_move_eval_white

            self.logger.info(f"Player perspective - Best would give: {eval_before_player}, Our move gives: {eval_after_player}")

            result = {
                'move': move_uci,
                'move_san': move_san,
                'evaluation_before': eval_before_player,
                'evaluation_after': eval_after_player,
                'best_move': best_pv['moves'][0] if best_pv['moves'] else None,
                '_after_position_analysis': after_analysis  # For reuse in next move
            }

            # Categorize move quality
            if result['best_move'] == move_uci:
                result['classification'] = 'best'
                result['eval_loss'] = 0
                self.logger.info(f"Move classification: BEST")
            else:
                # Evaluation loss = how much worse is our move compared to best move
                # From the player's perspective (positive = got worse)
                # Example: Best gives -696, our move gives -790
                # Loss = -696 - (-790) = 94 centipawns (position got worse by 94)
                eval_loss = eval_before_player - eval_after_player
                result['eval_loss'] = eval_loss

                self.logger.info(f"Evaluation loss: {eval_loss} (positive = position got worse)")

                # If eval_loss is positive, position got worse (this is bad)
                # If eval_loss is negative, position got better (shouldn't happen if engine found best move)

                # If the move hangs a piece, automatically classify as at least a mistake
                if move_hangs_piece and eval_loss > 0:
                    # Penalize hanging pieces more severely
                    if eval_loss < 100:
                        result['classification'] = 'inaccuracy'
                        self.logger.info(f"Move classification: INACCURACY (hangs piece, small eval loss)")
                    elif eval_loss < 200:
                        result['classification'] = 'mistake'
                        self.logger.info(f"Move classification: MISTAKE (hangs piece)")
                    else:
                        result['classification'] = 'blunder'
                        self.logger.info(f"Move classification: BLUNDER (hangs piece)")
                elif eval_loss < -50:
                    # Position improved significantly - this shouldn't happen if engine is working correctly
                    result['classification'] = 'best'
                    self.logger.info(f"Move classification: BEST (position improved)")
                elif eval_loss < 50:
                    result['classification'] = 'excellent'
                    self.logger.info(f"Move classification: EXCELLENT")
                elif eval_loss < 100:
                    result['classification'] = 'good'
                    self.logger.info(f"Move classification: GOOD")
                elif eval_loss < 200:
                    result['classification'] = 'inaccuracy'
                    self.logger.info(f"Move classification: INACCURACY")
                elif eval_loss < 400:
                    result['classification'] = 'mistake'
                    self.logger.info(f"Move classification: MISTAKE")
                else:
                    result['classification'] = 'blunder'
                    self.logger.info(f"Move classification: BLUNDER")

            return result

        except Exception as e:
            self.logger.error(f"Move evaluation failed: {str(e)}")
            raise Exception(f"Move evaluation failed: {str(e)}")

    def __enter__(self):
        """Context manager support"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.stop()
