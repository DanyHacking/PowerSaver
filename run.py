#!/usr/bin/env python3
"""
PowerSaver MEV Trading System
Main entry point for 24/7 operation
Supports both testnet and mainnet
"""

import asyncio
import argparse
import logging
import signal
import sys
import os
from datetime import datetime
from typing import Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============== CONFIGURATION ==============

TESTNET_CONFIG = {
    "name": "sepolia",
    "rpc_url": "https://rpc.sepolia.org",
    "chain_id": 11155111,
    "native_token": "ETH",
    "explorer": "https://sepolia.etherscan.io",
    
    # Trading parameters (conservative for testnet)
    "min_profit_usd": 1,
    "min_confidence": 0.5,
    "max_slippage": 0.10,
    "max_gas_gwei": 50,
    "max_position_pct": 0.1,
    "mev_mode": "relaxed",
    
    # Testnet wallets (replace with your test wallets)
    "wallet_address": "0x0000000000000000000000000000000000000000",
    "private_key": "0x0000000000000000000000000000000000000000000000000000000000000000",
    
    # Builder endpoints (testnet)
    "builders": {
        "flashbots": "https://relay-sepolia.flashbots.net",
        "builder0x69": "https://builder0x69.io/testnet",
    }
}

MAINNET_CONFIG = {
    "name": "ethereum",
    "rpc_url": "https://eth.llamarpc.com",
    "chain_id": 1,
    "native_token": "ETH",
    "explorer": "https://etherscan.io",
    
    # Trading parameters (optimized for mainnet)
    "min_profit_usd": 10,
    "min_confidence": 0.7,
    "max_slippage": 0.03,
    "max_gas_gwei": 100,
    "max_position_pct": 0.2,
    "mev_mode": "normal",
    
    # Mainnet wallet (MUST BE CONFIGURED)
    "wallet_address": os.getenv("WALLET_ADDRESS", ""),
    "private_key": os.getenv("PRIVATE_KEY", ""),
    
    # Builder endpoints (mainnet)
    "builders": {
        "flashbots": "https://relay.flashbots.net",
        "builder0x69": "https://builder0x69.io",
        "eden": "https://api.edennetwork.io/v1/bundle",
        "blocknative": "https://api.blocknative.com/v1/bundle",
    }
}


# ============== TRADING SYSTEM ==============

class PowerSaverSystem:
    """
    Main trading system
    24/7 operation capable
    """
    
    def __init__(self, config: Dict, is_testnet: bool = False):
        self.config = config
        self.is_testnet = is_testnet
        
        # Components
        self.trading_engine = None
        self.oracle = None
        self.health_monitor = None
        
        # State
        self.is_running = False
        self.cycle_count = 0
        self.start_time = None
        
        # Statistics
        self.stats = {
            "total_cycles": 0,
            "total_trades": 0,
            "total_profit": 0.0,
            "failed_trades": 0,
            "uptime_seconds": 0,
        }
    
    async def initialize(self) -> bool:
        """Initialize all components"""
        logger.info("="*60)
        logger.info(f"🚀 PowerSaver Trading System v1.0")
        logger.info(f"🌐 Network: {self.config['name'].upper()}")
        logger.info(f"🔗 RPC: {self.config['rpc_url'][:40]}...")
        logger.info("="*60)
        
        try:
            # Initialize trading engine
            logger.info("📡 Initializing Trading Engine...")
            from src.trading.trading_engine_v2 import create_trading_engine
            
            engine_config = {
                "rpc_url": self.config["rpc_url"],
                "min_profit_usd": self.config["min_profit_usd"],
                "min_confidence": self.config["min_confidence"],
                "max_slippage": self.config["max_slippage"],
                "max_gas_gwei": self.config["max_gas_gwei"],
                "mev_mode": self.config["mev_mode"],
            }
            
            self.trading_engine = create_trading_engine(engine_config)
            initialized = await self.trading_engine.initialize()
            
            if not initialized:
                logger.error("❌ Failed to initialize trading engine")
                return False
            
            logger.info("✅ Trading Engine initialized")
            
            # Initialize aggressive optimizations
            logger.info("⚡ Initializing Low-Latency Router...")
            from src.utils.aggressive_optimizations import create_low_latency_router
            
            self.latency_router = create_low_latency_router()
            await self.latency_router.initialize()
            logger.info("✅ Low-Latency Router initialized")
            
            # Initialize block predictor
            logger.info("📊 Initializing Block Predictor...")
            from src.utils.aggressive_optimizations import create_block_predictor
            
            self.block_predictor = create_block_predictor()
            logger.info("✅ Block Predictor initialized")
            
            # Initialize liquidation monitor
            logger.info("💰 Initializing Liquidation Monitor...")
            from src.utils.aggressive_optimizations import create_liquidation_monitor
            
            self.liquidation_monitor = create_liquidation_monitor({
                "scan_interval": 5,
                "min_profit": self.config["min_profit_usd"]
            })
            logger.info("✅ Liquidation Monitor initialized")
            
            # Initialize advanced algorithms
            logger.info("🎯 Initializing Trading Algorithms...")
            from src.utils.advanced_algorithms import (
                create_position_sizer,
                create_risk_manager,
                create_order_splitter,
                create_slippage_optimizer
            )
            
            self.position_sizer = create_position_sizer({
                "max_kelly": 0.25,
                "kelly_divisor": 2
            })
            
            self.risk_manager = create_risk_manager({
                "max_position_pct": self.config["max_position_pct"],
                "max_daily_loss_pct": 0.05,
                "max_drawdown_pct": 0.15
            })
            
            self.order_splitter = create_order_splitter({
                "max_order_size": 10000,
                "split_count": 5
            })
            
            self.slippage_optimizer = create_slippage_optimizer()
            
            logger.info("✅ Trading Algorithms initialized")
            
            self.start_time = datetime.now()
            self.is_running = True
            
            logger.info("="*60)
            logger.info("✅ SYSTEM INITIALIZED SUCCESSFULLY")
            logger.info("="*60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run_cycle(self):
        """Run one trading cycle"""
        self.cycle_count += 1
        
        try:
            # Run trading engine cycle
            results = await self.trading_engine.run_cycle()
            
            # Update stats
            self.stats["total_cycles"] += 1
            
            if results:
                for result in results:
                    self.stats["total_trades"] += 1
                    if result.success:
                        self.stats["total_profit"] += result.profit_actual
                    else:
                        self.stats["failed_trades"] += 1
            
            # Log status every 10 cycles
            if self.cycle_count % 10 == 0:
                self._log_status()
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Cycle error: {e}")
            return []
    
    def _log_status(self):
        """Log current status"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        logger.info("─"*60)
        logger.info(f"📈 STATUS | Cycle: {self.cycle_count} | Uptime: {uptime/3600:.1f}h")
        logger.info(f"💵 Trades: {self.stats['total_trades']} | Profit: ${self.stats['total_profit']:.2f}")
        logger.info(f"❌ Failed: {self.stats['failed_trades']}")
        
        # Health status
        if self.trading_engine:
            health = self.trading_engine.health_monitor.check_health()
            logger.info(f"💚 Health: {health.status.value}")
        
        logger.info("─"*60)
    
    async def run_forever(self):
        """Run system continuously"""
        if not self.is_running:
            logger.error("❌ System not initialized")
            return
        
        logger.info("▶ Starting 24/7 operation...")
        logger.info("💡 Press Ctrl+C to stop")
        
        cycle_interval = 5  # seconds between cycles
        
        try:
            while self.is_running:
                await self.run_cycle()
                
                # Wait before next cycle
                await asyncio.sleep(cycle_interval)
                
        except KeyboardInterrupt:
            logger.info("\n⚠️ Received stop signal")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown system gracefully"""
        logger.info("🛑 Shutting down...")
        
        self.is_running = False
        
        # Stop components
        if self.trading_engine and self.trading_engine.health_monitor:
            self.trading_engine.health_monitor.stop()
        
        # Final stats
        logger.info("="*60)
        logger.info("📊 FINAL STATISTICS")
        logger.info("="*60)
        logger.info(f"Total Cycles: {self.stats['total_cycles']}")
        logger.info(f"Total Trades: {self.stats['total_trades']}")
        logger.info(f"Total Profit: ${self.stats['total_profit']:.2f}")
        logger.info(f"Failed Trades: {self.stats['failed_trades']}")
        
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()
            logger.info(f"Total Uptime: {uptime/3600:.2f} hours")
        
        logger.info("✅ Shutdown complete")
        
        sys.exit(0)


# ============== MAIN ==============

async def main():
    parser = argparse.ArgumentParser(description="PowerSaver MEV Trading System")
    parser.add_argument(
        "--network",
        choices=["testnet", "mainnet"],
        default="testnet",
        help="Network to run on"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Custom config file (JSON)"
    )
    
    args = parser.parse_args()
    
    # Load config
    if args.network == "testnet":
        config = TESTNET_CONFIG
    else:
        config = MAINNET_CONFIG
    
    # Override with custom config if provided
    if args.config:
        import json
        with open(args.config) as f:
            custom = json.load(f)
            config.update(custom)
    
    # Check mainnet credentials
    if args.network == "mainnet":
        if not config.get("wallet_address") or not config.get("private_key"):
            logger.error("❌ Mainnet requires WALLET_ADDRESS and PRIVATE_KEY environment variables")
            logger.info("💡 Set them with:")
            logger.info("   export WALLET_ADDRESS=0x...")
            logger.info("   export PRIVATE_KEY=0x...")
            sys.exit(1)
        
        logger.warning("⚠️ RUNNING ON MAINNET - REAL MONEY AT STAKE")
        logger.warning("⚠️ Make sure you have configured your wallet correctly")
    
    # Create and run system
    system = PowerSaverSystem(config, is_testnet=(args.network == "testnet"))
    
    # Handle signals
    def signal_handler(sig, frame):
        logger.info("⚠️ Received interrupt signal")
        system.is_running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize and run
    if await system.initialize():
        await system.run_forever()
    else:
        logger.error("❌ Failed to start system")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
