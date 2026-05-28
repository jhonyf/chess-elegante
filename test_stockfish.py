#!/usr/bin/env python3
"""Test Stockfish engine integration"""

from services.stockfish_engine import StockfishEngine

def test_analysis():
    """Test position analysis"""
    print("Testing Stockfish Engine Integration\n")
    print("=" * 50)

    engine = StockfishEngine()

    # Test 1: Starting position
    print("\n1. Analyzing starting position...")
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    try:
        result = engine.analyze_position(fen, depth=15, multipv=3)
        print(f"   ✓ Analysis successful")
        print(f"   Depth: {result['depth']}")
        print(f"   Principal variations: {len(result['pvs'])}")

        for i, pv in enumerate(result['pvs'][:3]):
            eval_str = f"+{pv['cp']/100:.2f}" if pv.get('cp', 0) > 0 else f"{pv['cp']/100:.2f}"
            best_move = pv['san_moves'][0] if pv['san_moves'] else 'N/A'
            print(f"   #{i+1}: {best_move} ({eval_str})")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    # Test 2: Middle game position
    print("\n2. Analyzing middle game position...")
    fen = "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"

    try:
        result = engine.analyze_position(fen, depth=15, multipv=1)
        pv = result['pvs'][0]
        eval_str = f"+{pv['cp']/100:.2f}" if pv.get('cp', 0) > 0 else f"{pv['cp']/100:.2f}"
        best_move = pv['san_moves'][0] if pv['san_moves'] else 'N/A'
        print(f"   ✓ Best move: {best_move} ({eval_str})")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    # Test 3: Move evaluation
    print("\n3. Testing move evaluation...")
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    move = "e2e4"

    try:
        result = engine.evaluate_move(fen, move)
        print(f"   ✓ Move: {result['move_san']}")
        print(f"   Classification: {result['classification']}")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    # Clean up
    engine.stop()

    print("\n" + "=" * 50)
    print("✓ All tests passed!")
    print("\nStockfish integration is working correctly.")
    return True

if __name__ == '__main__':
    test_analysis()
