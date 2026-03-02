"""
TRADING ENGINE INTEGRATION
Full integration of all oracle and protection systems
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TradeDirection(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class TradeDecision:
    """Complete trade decision"""
    action: TradeDirection
    token_in: str
    token_out: str
    amount_in: float
    amount_out_expected: float
    price_used: float
    price_source: str
    slippage_estimate: float
    gas_estimate: float
    profit_estimate: float
    confidence: float
    should_execute: bool
    reasons: List[str]


@dataclass
class ExecutionResult:
    """Result of trade execution"""
    success: bool
    tx_hash: Optional[str]
    amount_out_actual: float
    gas_used: float
    profit_actual: float
    revert_reason: Optional[str]
    block_number: int


class TradingEngineV2:
    """
    FULLY INTEGRATED Trading Engine
    - Production Oracle
    - MEV Protection
    - Flash Loan Detection
    - Health Monitoring
    - Builder Optimization
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Initialize components
        self._init_oracle()
        self._init_mev_protection()
        self._init_flash_loan_detection()
        self._init_health_monitor()
        self._init_builder_optimizer()
        
        # Trading config
        self.min_profit_usd = config.get("min_profit_usd", 10)
        self.min_confidence = config.get("min_confidence", 0.7)
        self.max_slippage = config.get("max_slippage", 0.03)  # 3%
        self.max_gas_gwei = config.get("max_gas_gwei", 100)
        
        # State
        self.is_running = False
        self.total_trades = 0
        self.total_profit = 0.0
    
    def _init_oracle(self):
        """Initialize production oracle"""
        from src.utils.production_oracle_v2 import create_production_oracle
        
        rpc_url = self.config.get("rpc_url", "https://eth.llamarpc.com")
        self.oracle = create_production_oracle(rpc_url)
        logger.info("📡 Oracle initialized")
    
    def _init_mev_protection(self):
        """Initialize MEV protection"""
        from src.utils.mev_protection import create_mev_protection
        
        self.mev_protection = create_mev_protection({
            "mode": self.config.get("mev_mode", "normal"),
            "sandwich_threshold": 0.01,
            "large_order_threshold": 50000
        })
        logger.info("🛡️ MEV Protection initialized")
    
    def _init_flash_loan_detection(self):
        """Initialize flash loan detection"""
        from src.utils.flash_loan_detection import create_flash_loan_detector
        
        self.flash_loan_detector = create_flash_loan_detector({
            "min_amount_usd": 10000
        })
        logger.info("🔍 Flash Loan Detection initialized")
    
    def _init_health_monitor(self):
        """Initialize health monitor"""
        from src.utils.health_monitor import create_health_monitor
        
        self.health_monitor = create_health_monitor({
            "max_revert_rate": 0.15,
            "min_builder_acceptance": 0.3,
            "max_latency_ms": 5000
        })
        self.health_monitor.start()
        logger.info("💚 Health Monitor initialized")
    
    def _init_builder_optimizer(self):
        """Initialize builder optimizer"""
        from src.utils.builder_optimizer import create_builder_optimizer
        
        self.builder_optimizer = create_builder_optimizer({
            "bundle_value_threshold": 10,
            "retry_count": 3
        })
        self.builder_optimizer.start()
        logger.info("🏗️ Builder Optimizer initialized")
    
    async def initialize(self) -> bool:
        """Initialize all async components"""
        try:
            return await self.oracle.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    # ============== MAIN TRADING LOGIC ==============
    
    async def analyze_and_decide(
        self,
        token_in: str,
        token_out: str,
        amount_in: float
    ) -> TradeDecision:
        """
        MAIN DECISION FUNCTION
        Full analysis and decision making
        """
        reasons = []
        
        # 1. Get current price from oracle
        price_result = await self.oracle.get_price(token_in)
        if not price_result:
            return self._reject_trade(
                "Failed to get price",
                token_in, token_out, amount_in
            )
        
        price = price_result.price_usd
        reasons.append(f"Price: ${price:.2f} (confidence: {price_result.confidence:.1%})")
        
        # 2. Check confidence
        if price_result.confidence < self.min_confidence:
            return self._reject_trade(
                f"Low confidence: {price_result.confidence:.1%}",
                token_in, token_out, amount_in
            )
        
        # 3. Estimate slippage
        slippage = await self.oracle.get_slippage_estimate(token_in, amount_in)
        if slippage > self.max_slippage:
            return self._reject_trade(
                f"High slippage: {slippage:.2%}",
                token_in, token_out, amount_in
            )
        
        reasons.append(f"Slippage: {slippage:.2%}")
        
        # 4. Check MEV protection
        mev_result = await self.mev_protection.analyze_transaction({
            "token_in": token_in,
            "token_out": token_out,
            "amount": amount_in,
            "amount_usd": amount_in * price
        })
        
        if not mev_result.is_safe:
            return self._reject_trade(
                f"MEV threat: {mev_result.threats}",
                token_in, token_out, amount_in
            )
        
        # Update slippage based on MEV adjustment
        slippage += mev_result.adjusted_slippage
        reasons.append(f"MEV adjusted slippage: {slippage:.2%}")
        
        # 5. Check if now is good time to trade
        if not self.oracle.should_trade_now(token_in):
            return self._reject_trade(
                "Poor trading conditions",
                token_in, token_out, amount_in
            )
        
        reasons.append("Trading conditions OK")
        
        # 6. Calculate expected output
        amount_out_expected = amount_in * price * (1 - slippage)
        
        # 7. Estimate gas
        gas_estimate = self._estimate_gas()
        
        # 8. Calculate profit estimate
        profit_estimate = self._calculate_profit_estimate(
            amount_in, amount_out_expected, gas_estimate, price
        )
        
        reasons.append(f"Profit estimate: ${profit_estimate:.2f}")
        
        # 9. Check against health monitor
        health = self.health_monitor.check_health()
        if health.status.value == "critical":
            return self._reject_trade(
                "System health critical",
                token_in, token_out, amount_in
            )
        
        if health.status.value == "degraded":
            reasons.append("⚠️ System degraded")
        
        # 10. Make final decision
        should_execute = (
            profit_estimate >= self.min_profit_usd and
            slippage <= self.max_slippage and
            price_result.confidence >= self.min_confidence
        )
        
        return TradeDecision(
            action=TradeDirection.BUY if should_execute else TradeDirection.HOLD,
            token_in=token_in,
            token_out=token_out,
            amount_in=amount_in,
            amount_out_expected=amount_out_expected,
            price_used=price,
            price_source="production_oracle",
            slippage_estimate=slippage,
            gas_estimate=gas_estimate,
            profit_estimate=profit_estimate,
            confidence=price_result.confidence,
            should_execute=should_execute,
            reasons=reasons
        )
    
    async def execute_trade(
        self,
        decision: TradeDecision
    ) -> ExecutionResult:
        """Execute a trade based on decision"""
        if not decision.should_execute:
            return ExecutionResult(
                success=False,
                tx_hash=None,
                amount_out_actual=0,
                gas_used=0,
                profit_actual=0,
                revert_reason="Decision: no execute",
                block_number=0
            )
        
        # Record in health monitor
        start_time = time.time()
        
        try:
            # 1. Build transaction
            tx = await self._build_transaction(decision)
            
            # 2. Submit to builder
            bundle_hash = await self.builder_optimizer.submit_bundle(
                tx,
                decision.profit_estimate
            )
            
            if not bundle_hash:
                # Fallback to public mempool
                tx_hash = await self._send_to_mempool(tx)
            else:
                tx_hash = bundle_hash
            
            # 3. Wait for confirmation
            result = await self._wait_for_confirmation(tx_hash)
            
            # 4. Record result
            self.total_trades += 1
            
            if result["success"]:
                self.total_profit += decision.profit_estimate
                self.health_monitor.record_trade(
                    decision.profit_estimate,
                    success=True
                )
                self.health_monitor.record_builder_response(True)
            else:
                self.health_monitor.record_trade(
                    0, success=False, reverted=True
                )
                self.health_monitor.record_builder_response(False)
            
            latency = time.time() - start_time
            self.health_monitor.record_latency(latency * 1000)
            
            return ExecutionResult(
                success=result["success"],
                tx_hash=tx_hash,
                amount_out_actual=decision.amount_out_expected,  # Simplified
                gas_used=decision.gas_estimate,
                profit_actual=decision.profit_estimate if result["success"] else 0,
                revert_reason=result.get("error"),
                block_number=result.get("block_number", 0)
            )
            
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            return ExecutionResult(
                success=False,
                tx_hash=None,
                amount_out_actual=0,
                gas_used=0,
                profit_actual=0,
                revert_reason=str(e),
                block_number=0
            )
    
    async def run_cycle(self) -> List[ExecutionResult]:
        """Run one trading cycle"""
        results = []
        
        # Check health first
        if not self.health_monitor.is_running:
            return results
        
        # Get opportunities
        opportunities = await self._find_opportunities()
        
        for opp in opportunities:
            decision = await self.analyze_and_decide(
                opp["token_in"],
                opp["token_out"],
                opp["amount"]
            )
            
            if decision.should_execute:
                result = await self.execute_trade(decision)
                results.append(result)
            
            # Small delay between trades
            await asyncio.sleep(0.5)
        
        return results
    
    # ============== HELPER METHODS ==============
    
    def _reject_trade(
        self,
        reason: str,
        token_in: str,
        token_out: str,
        amount: float
    ) -> TradeDecision:
        """Create a rejected trade decision"""
        return TradeDecision(
            action=TradeDirection.HOLD,
            token_in=token_in,
            token_out=token_out,
            amount_in=amount,
            amount_out_expected=0,
            price_used=0,
            price_source="none",
            slippage_estimate=0,
            gas_estimate=0,
            profit_estimate=0,
            confidence=0,
            should_execute=False,
            reasons=[f"REJECTED: {reason}"]
        )
    
    async def _find_opportunities(self) -> List[Dict]:
        """Find trading opportunities"""
        opportunities = []
        
        # Check arbitrage between tokens
        tokens = ["ETH", "WETH", "WBTC", "LINK", "UNI", "AAVE"]
        
        for token in tokens:
            arb = await self.oracle.get_arbitrage_opportunity(token, "USDC")
            if arb and arb.get("profit_pct", 0) > 0.5:
                opportunities.append({
                    "type": "arbitrage",
                    "token_in": token,
                    "token_out": "USDC",
                    "amount": 10000,  # Default
                    "profit_pct": arb["profit_pct"]
                })
        
        return opportunities
    
    def _estimate_gas(self) -> float:
        """Estimate gas cost in USD"""
        # In production, would get real gas price
        gas_limit = 150000
        gas_price = 30  # gwei
        eth_price = self.oracle.get_price_sync("ETH") or 1800
        
        return gas_limit * gas_price * eth_price / 1e9
    
    def _calculate_profit_estimate(
        self,
        amount_in: float,
        amount_out: float,
        gas_cost: float,
        price: float
    ) -> float:
        """Calculate profit estimate"""
        # Simplified: profit = output - input - gas
        input_usd = amount_in * price
        return amount_out - input_usd - gas_cost
    
    async def _build_transaction(self, decision: TradeDecision) -> Dict:
        """Build transaction"""
        # In production, would build real transaction
        return {
            "to": "0x...",
            "data": "0x...",
            "value": decision.amount_in,
            "gas": int(decision.gas_estimate * 1.5)
        }
    
    async def _send_to_mempool(self, tx: Dict) -> Optional[str]:
        """Send to public mempool"""
        # In production, would sign and send
        return None
    
    async def _wait_for_confirmation(self, tx_hash: str) -> Dict:
        """Wait for transaction confirmation"""
        # In production, would wait for confirmations
        return {"success": True, "block_number": 0}
    
    def get_stats(self) -> Dict:
        """Get trading stats"""
        return {
            "total_trades": self.total_trades,
            "total_profit": self.total_profit,
            "health": self.health_monitor.get_stats(),
            "oracle": self.oracle.get_stats(),
            "mev_protection": self.mev_protection.get_protection_stats()
        }


# ============== FACTORY ==============

def create_trading_engine(config: Dict) -> TradingEngineV2:
    """Create trading engine"""
    return TradingEngineV2(config)


# ============== USAGE ==============

async def main():
    """Example usage"""
    config = {
        "rpc_url": "https://eth.llamarpc.com",
        "min_profit_usd": 10,
        "min_confidence": 0.7,
        "max_slippage": 0.03,
        "mev_mode": "normal"
    }
    
    engine = create_trading_engine(config)
    
    if await engine.initialize():
        print("✅ Trading Engine initialized")
        
        # Make a decision
        decision = await engine.analyze_and_decide("ETH", "USDC", 10000)
        
        print(f"\n📊 Trade Decision:")
        print(f"   Action: {decision.action.value}")
        print(f"   Amount: {decision.amount_in} {decision.token_in}")
        print(f"   Expected output: {decision.amount_out_expected:.2f} {decision.token_out}")
        print(f"   Price: ${decision.price_used:.2f}")
        print(f"   Slippage: {decision.slippage_estimate:.2%}")
        print(f"   Profit estimate: ${decision.profit_estimate:.2f}")
        print(f"   Confidence: {decision.confidence:.1%}")
        print(f"   Should execute: {decision.should_execute}")
        print(f"\n📝 Reasons:")
        for r in decision.reasons:
            print(f"   - {r}")
        
        # Run cycle
        results = await engine.run_cycle()
        print(f"\n🔄 Cycle complete: {len(results)} trades")
        
        # Stats
        stats = engine.get_stats()
        print(f"\n📈 Stats:")
        print(f"   Total trades: {stats['total_trades']}")
        print(f"   Total profit: ${stats['total_profit']:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
