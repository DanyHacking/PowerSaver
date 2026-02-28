#!/usr/bin/env python3
"""
Minimal startup script for autonomous trading system
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import config
from trading.complete_trading_engine import CompleteAutonomousTradingEngine, StrategyType

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point"""
    try:
        # Validate configuration
        config.validate()
        logger.info("Configuration validated successfully")
        
        # Initialize trading engine
        engine = CompleteAutonomousTradingEngine(config.get_config_dict())
        
        # Start trading
        await engine.start()
        logger.info("Trading engine started")
        
        # Set initial strategy
        engine.set_strategy(StrategyType.BALANCED)
        
        # Run trading loop
        await engine._trading_loop()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt - shutting down")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        await engine.stop()
        logger.info("Trading engine stopped")


if __name__ == "__main__":
    asyncio.run(main())
