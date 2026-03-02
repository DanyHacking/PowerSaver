#!/usr/bin/env python3
"""
PowerSaver Ultimate Trading System
All-in-one CLI and Dashboard

Usage:
    python ultimate_cli.py start --engine aggressive
    python ultimate_cli.py status
    python ultimate_cli.py trade --token ETH --amount 1.0
    python ultimate_cli.py dashboard
"""

import asyncio
import argparse
import os
import sys
from typing import Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class PowerSaverCLI:
    """Command-line interface for PowerSaver"""
    
    def __init__(self):
        self.rpc_url = os.getenv("ETHEREUM_RPC_URL")
        self.private_key = os.getenv("PRIVATE_KEY")
        
        self.engines = {}
    
    def _load_engine(self, engine_name: str):
        """Load engine by name"""
        if engine_name == "twap":
            from src.utils.twap_manipulator import TWAPManipulator
            return TWAPManipulator(self.rpc_url, self.private_key)
        
        elif engine_name == "aggressive":
            from src.utils.aggressive_twap_engine import AggressiveTWAPEngine
            return AggressiveTWAPEngine(self.rpc_url, self.private_key)
        
        elif engine_name == "automated":
            from src.utils.automated_twap_oracle import AutomatedTWAPOracle, AutomationConfig
            config = AutomationConfig(
                target_prices={"ETH": 1850.0},
                trade_size=1.0
            )
            return AutomatedTWAPOracle(self.rpc_url, self.private_key, config)
        
        elif engine_name == "ultimate":
            from src.utils.ultimate_profit_engine import UltimateProfitEngine, UltraConfig
            config = UltraConfig()
            return UltimateProfitEngine(config)
        
        else:
            raise ValueError(f"Unknown engine: {engine_name}")
    
    async def cmd_start(self, args):
        """Start an engine"""
        print(f"🚀 Starting {args.engine} engine...")
        
        engine = self._load_engine(args.engine)
        self.engines[args.engine] = engine
        
        if hasattr(engine, 'start'):
            await engine.start()
    
    async def cmd_stop(self, args):
        """Stop an engine"""
        if args.engine in self.engines:
            engine = self.engines[args.engine]
            if hasattr(engine, 'stop'):
                await engine.stop()
            print(f"🛑 Stopped {args.engine}")
        else:
            print(f"Engine {args.engine} not running")
    
    async def cmd_status(self, args):
        """Show status"""
        print("\n" + "=" * 50)
        print("🔍 POWERSAVER STATUS")
        print("=" * 50)
        
        print(f"\n📡 RPC: {self.rpc_url or 'Not configured'}")
        print(f"🔑 Wallet: {self._get_wallet_address() or 'Not configured'}")
        
        print(f"\n📊 Active Engines: {len(self.engines)}")
        for name, engine in self.engines.items():
            status = getattr(engine, 'is_running', None)
            print(f"   - {name}: {'🟢 Running' if status else '🔴 Stopped'}")
        
        print("\n" + "=" * 50)
    
    async def cmd_trade(self, args):
        """Execute a trade"""
        print(f"💱 Executing trade: {args.amount} {args.token}")
        
        from src.utils.twap_manipulator import TWAPManipulator
        
        engine = TWAPManipulator(self.rpc_url, self.private_key)
        
        result = await engine.update_twap_and_read(
            token_a=args.token,
            token_b=args.token_out or "USDC",
            trade_amount=args.amount,
            target_price=args.price or 0
        )
        
        if result:
            print(f"✅ Trade successful!")
            print(f"   Input: {result.amount_in} {result.token_in}")
            print(f"   Output: {result.amount_out} {result.token_out}")
            print(f"   New TWAP: ${result.new_twap_price:.2f}")
            print(f"   TX: {result.tx_hash[:20]}...")
        else:
            print("❌ Trade failed")
    
    async def cmd_publish(self, args):
        """Publish price to oracle"""
        print(f"⛓️ Publishing {args.price} for {args.token}...")
        
        from src.utils.on_chain_oracle_publisher import OnChainOraclePublisher
        
        publisher = OnChainOraclePublisher(self.rpc_url, self.private_key)
        
        tx_hash = await publisher.publish_to_oracle_contract(
            contract_address=args.contract or "",
            token=args.token,
            price=args.price
        )
        
        if tx_hash:
            print(f"✅ Published!")
            print(f"   TX: https://etherscan.io/tx/{tx_hash}")
        else:
            print("❌ Publish failed")
    
    async def cmd_oracle(self, args):
        """Oracle commands"""
        if args.subcmd == "status":
            from src.utils.advanced_data_feed import UniswapV3Oracle
            
            oracle = UniswapV3Oracle(self.rpc_url)
            
            for token in ["ETH", "WBTC"]:
                price = await oracle.get_price(token)
                print(f"   {token}: ${price:.2f}" if price else f"   {token}: N/A")
    
    def _get_wallet_address(self) -> Optional[str]:
        """Get wallet address from private key"""
        if not self.private_key:
            return None
        
        try:
            from web3 import Web3
            from web3.eth import Account
            account = Account.from_key(self.private_key)
            return account.address
        except:
            return None


def main():
    parser = argparse.ArgumentParser(description="PowerSaver Trading System")
    subparsers = parser.add_subparsers(dest="command")
    
    # start
    start_parser = subparsers.add_parser("start", help="Start engine")
    start_parser.add_argument("--engine", default="aggressive", 
                              choices=["twap", "automated", "aggressive", "ultimate"])
    
    # stop
    stop_parser = subparsers.add_parser("stop", help="Stop engine")
    stop_parser.add_argument("--engine", required=True)
    
    # status
    subparsers.add_parser("status", help="Show status")
    
    # trade
    trade_parser = subparsers.add_parser("trade", help="Execute trade")
    trade_parser.add_argument("--token", default="ETH")
    trade_parser.add_argument("--token-out", default="USDC")
    trade_parser.add_argument("--amount", type=float, default=1.0)
    trade_parser.add_argument("--price", type=float, default=0)
    
    # publish
    publish_parser = subparsers.add_parser("publish", help="Publish to oracle")
    publish_parser.add_argument("--token", default="ETH")
    publish_parser.add_argument("--price", type=float, required=True)
    publish_parser.add_argument("--contract", default="")
    
    # oracle
    oracle_parser = subparsers.add_parser("oracle", help="Oracle commands")
    oracle_parser.add_argument("subcmd", choices=["status", "set"])
    
    args = parser.parse_args()
    
    # Run command
    cli = PowerSaverCLI()
    
    if args.command == "start":
        asyncio.run(cli.cmd_start(args))
    elif args.command == "stop":
        asyncio.run(cli.cmd_stop(args))
    elif args.command == "status":
        asyncio.run(cli.cmd_status(args))
    elif args.command == "trade":
        asyncio.run(cli.cmd_trade(args))
    elif args.command == "publish":
        asyncio.run(cli.cmd_publish(args))
    elif args.command == "oracle":
        asyncio.run(cli.cmd_oracle(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
