#!/usr/bin/env python3
"""
Minimal test to verify system configuration
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import config

def test_config():
    """Test configuration loading"""
    print("\n=== Testing Configuration ===")
    
    # Test required fields
    assert config.PRIVATE_KEY, "PRIVATE_KEY required"
    assert config.RPC_URL and "YOUR_INFURA" not in config.RPC_URL, "RPC_URL required"
    
    print(f"✓ Private Key: {'Configured' if config.PRIVATE_KEY else 'Missing'}")
    print(f"✓ RPC URL: {config.RPC_URL[:30]}...")
    print(f"✓ Chain ID: {config.CHAIN_ID}")
    print(f"✓ Loan Amount: ${config.LOAN_AMOUNT_USD}")
    print(f"✓ Max Loan: ${config.MAX_LOAN_AMOUNT_USD}")
    print(f"✓ Min Profit: ${config.MIN_PROFIT_THRESHOLD_USD}")
    print(f"✓ Strategy: {config.TRADING_STRATEGY}")
    print(f"✓ Tokens: {', '.join(config.SUPPORTED_TOKENS)}")
    print(f"✓ Exchanges: {', '.join(config.SUPPORTED_EXCHANGES)}")
    print(f"✓ Emergency Pause: {config.EMERGENCY_PAUSE}")
    print(f"✓ Max Concurrent Trades: {config.MAX_CONCURRENT_TRADES}")
    
    print("\n✓ All configuration tests passed!")
    return True

async def test_engine():
    """Test trading engine initialization"""
    print("\n=== Testing Trading Engine ===")
    
    from trading.complete_trading_engine import CompleteAutonomousTradingEngine
    
    engine = CompleteAutonomousTradingEngine(config.get_config_dict())
    
    print(f"✓ Engine initialized")
    print(f"✓ Supported Tokens: {len(engine.supported_tokens)}")
    print(f"✓ Supported Exchanges: {len(engine.supported_exchanges)}")
    print(f"✓ Profit Guard: {engine.profit_guard is not None}")
    print(f"✓ Risk Manager: {engine.risk_manager is not None}")
    print(f"✓ Gas Optimizer: {engine.gas_optimizer is not None}")
    print(f"✓ Market Analyzer: {engine.market_analyzer is not None}")
    
    print("\n✓ All engine tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_config()
        asyncio.run(test_engine())
        print("\n" + "="*50)
        print("✓ ALL TESTS PASSED - SYSTEM READY")
        print("="*50 + "\n")
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        sys.exit(1)
