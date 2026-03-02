"""
Automated TWAP + Oracle Publisher
Fully automated: monitors price → moves TWAP → publishes on-chain → other protocols read
"""

import asyncio
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass
import time
import os

logger = logging.getLogger(__name__)


@dataclass
class AutomationConfig:
    """Configuration for automated TWAP oracle"""
    # Price targets
    target_prices: Dict[str, float]  # token -> target price
    
    # TWAP manipulation settings
    trade_size: float = 1.0  # ETH per trade
    max_twap_deviation: float = 0.01  # 1% deviation triggers update
    
    # Publishing settings
    publish_to_chain: bool = True
    publish_interval: int = 60  # seconds
    
    # Risk management
    max_daily_trades: int = 100
    max_daily_spend: float = 10.0  # ETH
    
    # Monitoring
    check_interval: int = 10  # seconds
    price_sources: List[str] = ["uniswap", "coinbase", "binance"]


class AutomatedTWAPOracle:
    """
    Fully automated TWAP manipulation + on-chain publishing
    
    Flow:
    1. Monitor price from multiple sources
    2. If deviation > threshold, execute trade to move TWAP
    3. Publish new price to on-chain oracle
    4. Other protocols read the updated price
    """
    
    def __init__(
        self,
        rpc_url: str,
        private_key: str,
        config: AutomationConfig
    ):
        from src.utils.twap_manipulator import TWAPManipulator
        from src.utils.on_chain_oracle_publisher import OnChainOraclePublisher
        
        self.config = config
        self.manipulator = TWAPManipulator(rpc_url, private_key)
        self.publisher = OnChainOraclePublisher(rpc_url, private_key)
        
        # State
        self.is_running = False
        self.trades_today = 0
        self.spent_today = 0.0
        self.last_reset = time.time()
        self.last_publish = {}
        
        # Stats
        self.total_twap_updates = 0
        self.total_chain_publishes = 0
        self.profit = 0.0
    
    async def start(self):
        """Start automated oracle"""
        self.is_running = True
        logger.info(f"🤖 Automated TWAP Oracle started")
        logger.info(f"   Target prices: {self.config.target_prices}")
        logger.info(f"   Trade size: {self.config.trade_size} ETH")
        
        await self.manipulator.initialize()
        
        # Main loop
        while self.is_running:
            try:
                # Reset daily counters
                self._check_daily_reset()
                
                # Monitor and update each token
                for token, target_price in self.config.target_prices.items():
                    await self._process_token(token, target_price)
                
                # Wait before next check
                await asyncio.sleep(self.config.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in automation loop: {e}")
                await asyncio.sleep(5)
    
    async def stop(self):
        """Stop automated oracle"""
        self.is_running = False
        logger.info("🛑 Automated TWAP Oracle stopped")
    
    async def _process_token(self, token: str, target_price: float):
        """Process single token - monitor, update TWAP, publish"""
        
        # Step 1: Get current market price
        current_price = await self._get_market_price(token)
        if not current_price:
            logger.warning(f"No price for {token}")
            return
        
        # Step 2: Check deviation
        deviation = abs(current_price - target_price) / target_price
        
        if deviation > self.config.max_twap_deviation:
            logger.info(f"📊 {token}: Current ${current_price:.2f} vs Target ${target_price:.2f} (dev: {deviation*100:.2f}%)")
            
            # Step 3: Execute TWAP update trade
            if self.trades_today < self.config.max_daily_trades:
                result = await self.manipulator.update_twap_and_read(
                    token_a=token,
                    token_b="USDC",
                    trade_amount=self.config.trade_size,
                    target_price=target_price
                )
                
                if result:
                    self.trades_today += 1
                    self.spent_today += self.config.trade_size
                    self.total_twap_updates += 1
                    
                    logger.info(f"✅ TWAP updated: {token} = ${result.new_twap_price:.2f}")
                    
                    # Step 4: Publish to on-chain oracle
                    if self.config.publish_to_chain:
                        await self._publish_to_chain(token, result.new_twap_price)
        else:
            # Just publish current price
            if self.config.publish_to_chain:
                await self._maybe_publish(token, current_price)
    
    async def _get_market_price(self, token: str) -> Optional[float]:
        """Get average price from multiple sources"""
        prices = []
        
        # Could integrate multiple price sources here
        # For now, use Uniswap
        
        try:
            twap = await self.manipulator._get_current_twap(token, "USDC")
            if twap > 0:
                prices.append(twap)
        except:
            pass
        
        if prices:
            return sum(prices) / len(prices)
        return None
    
    async def _publish_to_chain(self, token: str, price: float):
        """Publish price to on-chain oracle"""
        try:
            tx_hash = await self.publisher.publish_to_oracle_contract(
                contract_address=self.publisher.PRICE_FEEDS.get(token.upper()),
                token=token,
                price=price
            )
            
            if tx_hash:
                self.total_chain_publishes += 1
                self.last_publish[token] = time.time()
                logger.info(f"⛓️ Published {token} = ${price:.2f} (tx: {tx_hash[:10]}...)")
                
        except Exception as e:
            logger.error(f"Failed to publish to chain: {e}")
    
    async def _maybe_publish(self, token: str, price: float):
        """Publish periodically even without TWAP update"""
        last = self.last_publish.get(token, 0)
        
        if time.time() - last > self.config.publish_interval:
            await self._publish_to_chain(token, price)
    
    def _check_daily_reset(self):
        """Reset daily counters at midnight"""
        now = time.time()
        if now - self.last_reset > 86400:  # 24 hours
            self.trades_today = 0
            self.spent_today = 0.0
            self.last_reset = now
            logger.info("📅 Daily counters reset")
    
    def get_status(self) -> Dict:
        """Get oracle status"""
        return {
            "is_running": self.is_running,
            "target_prices": self.config.target_prices,
            "trades_today": f"{self.trades_today}/{self.config.max_daily_trades}",
            "spent_today_eth": self.spent_today,
            "total_twap_updates": self.total_twap_updates,
            "total_chain_publishes": self.total_chain_publishes,
            "last_publish": self.last_publish
        }


# ========== MAIN ENTRY POINT ==========

async def main():
    """Run automated TWAP oracle"""
    
    rpc_url = os.getenv("ETHEREUM_RPC_URL")
    private_key = os.getenv("PRIVATE_KEY")
    
    config = AutomationConfig(
        target_prices={
            "ETH": 1850.0,
            "WBTC": 42000.0,
            "LINK": 15.0
        },
        trade_size=1.0,
        max_twap_deviation=0.005,  # 0.5% triggers update
        publish_to_chain=True,
        check_interval=10
    )
    
    oracle = AutomatedTWAPOracle(rpc_url, private_key, config)
    
    print("🤖 Automated TWAP Oracle")
    print("=" * 50)
    
    try:
        await oracle.start()
    except KeyboardInterrupt:
        await oracle.stop()
    
    print(oracle.get_status())


if __name__ == "__main__":
    asyncio.run(main())
