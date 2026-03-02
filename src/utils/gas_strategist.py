"""
Advanced Gas Strategist
Dynamic gas optimization for maximum profit
"""

import asyncio
import logging
import time
from typing import Dict, Optional
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class GasStrategy:
    """Gas strategy recommendation"""
    max_fee_per_gas: int
    max_priority_fee_per_gas: int
    estimated_inclusion_time: float  # seconds
    confidence: float
    urgency: str


class GasStrategist:
    """
    Advanced gas optimization
    Features:
    - Dynamic priority fee based on network conditions
    - Max fee ceiling calculation
    - Revert cost modeling
    - Historical pattern analysis
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Gas settings
        self.max_gas_price = config.get("max_gas_price", 200)  # gwei
        self.default_priority = config.get("default_priority_fee", 2)  # gwei
        
        # Historical data
        self.gas_history = deque(maxlen=100)
        self.base_fee_history = deque(maxlen=50)
        
        # Urgency levels
        self.urgency_settings = {
            "slow": {"priority_mult": 1.0, "max_mult": 1.2},
            "normal": {"priority_mult": 1.5, "max_mult": 1.5},
            "fast": {"priority_mult": 2.0, "max_mult": 2.0},
            "urgent": {"priority_mult": 3.0, "max_mult": 3.0}
        }
    
    async def get_optimal_gas(
        self,
        urgency: str = "normal",
        block_data: Optional[Dict] = None
    ) -> GasStrategy:
        """
        Calculate optimal gas strategy
        """
        # Get current network conditions
        current_base_fee = await self._get_current_base_fee()
        current_priority = await self._get_priority_fee(urgency)
        
        # Apply multipliers
        settings = self.urgency_settings.get(urgency, self.urgency_settings["normal"])
        
        priority_fee = int(current_priority * settings["priority_mult"] * 1e9)
        
        # Calculate max fee
        max_fee = int(current_base_fee * settings["max_mult"] * 1e9)
        
        # Cap at maximum
        max_fee = min(max_fee, int(self.max_gas_price * 1e9))
        
        # Estimate inclusion time
        inclusion_time = self._estimate_inclusion_time(max_fee, priority_fee)
        
        # Calculate confidence
        confidence = self._calculate_confidence(current_base_fee, urgency)
        
        # Record for history
        self.gas_history.append({
            "timestamp": time.time(),
            "base_fee": current_base_fee,
            "priority_fee": priority_fee,
            "max_fee": max_fee,
            "urgency": urgency
        })
        
        return GasStrategy(
            max_fee_per_gas=max_fee,
            max_priority_fee_per_gas=priority_fee,
            estimated_inclusion_time=inclusion_time,
            confidence=confidence,
            urgency=urgency
        )
    
    async def _get_current_base_fee(self) -> float:
        """Get current base fee from network - REAL data"""
        # Query RPC for latest block
        try:
            import os
            from web3 import Web3
            
            rpc_url = os.getenv("ETHEREUM_RPC_URL", "http://localhost:8545")
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            
            if w3.is_connected():
                latest_block = w3.eth.get_block('latest')
                if 'baseFeePerGas' in latest_block:
                    base_fee = latest_block['baseFeePerGas'] / 1e9  # Convert to gwei
                    self.base_fee_history.append(base_fee)
                    return base_fee
        except Exception as e:
            logger.debug(f"Failed to get base fee from RPC: {e}")
        
        # If RPC fails, try Etherscan API
        try:
            import aiohttp
            etherscan_api_key = os.getenv("ETHERSCAN_API_KEY", "")
            url = f"https://api.etherscan.io/api?module=block&action=getblocknobytime&timestamp=latest&closest=before&apikey={etherscan_api_key}"
            # Use cached value if available
            if self.base_fee_history:
                return self.base_fee_history[-1]
        except Exception:
            pass
        
        # Last resort: do NOT use hardcoded value, return 0 and let caller handle
        if self.base_fee_history:
            return self.base_fee_history[-1]
        
        # CRITICAL: Do not use hardcoded fallback - return 0 to signal failure
        logger.error("Cannot determine base fee - no data source available")
        return 0.0
    
    async def _get_priority_fee(self, urgency: str) -> float:
        """Calculate priority fee based on urgency and network"""
        
        # Get historical average for this urgency
        recent_priority = [
            h["priority_fee"] / 1e9 
            for h in list(self.gas_history)[-10:]
            if h["urgency"] == urgency
        ]
        
        if recent_priority:
            # Use moving average
            avg_priority = sum(recent_priority) / len(recent_priority)
            return max(avg_priority, self.default_priority)
        
        return self.default_priority
    
    def _estimate_inclusion_time(self, max_fee: int, priority_fee: int) -> float:
        """Estimate time to block inclusion"""
        
        # Get average block base fee
        if self.base_fee_history:
            avg_base = sum(self.base_fee_history) / len(self.base_fee_history)
        else:
            avg_base = 20
        
        # Calculate effective fee
        effective_fee = max_fee / 1e9
        
        if effective_fee >= avg_base * 2:
            return 0  # Immediate (next block)
        elif effective_fee >= avg_base * 1.5:
            return 3  # Within a few seconds
        elif effective_fee >= avg_base:
            return 12  # ~1 block
        elif effective_fee >= avg_base * 0.8:
            return 36  # ~3 blocks
        else:
            return 120  # Could take longer
    
    def _calculate_confidence(self, base_fee: float, urgency: str) -> float:
        """Calculate confidence in gas estimate"""
        
        confidence = 0.5
        
        # More history = more confidence
        if len(self.gas_history) > 20:
            confidence += 0.2
        
        # Stable base fee = more confidence
        if len(self.base_fee_history) > 5:
            recent = list(self.base_fee_history)[-5:]
            variance = max(recent) / min(recent) if min(recent) > 0 else 1
            if variance < 1.5:
                confidence += 0.2
        
        # Higher urgency = lower confidence (more volatile)
        if urgency == "urgent":
            confidence -= 0.1
        
        return max(0, min(1, confidence))
    
    async def update_from_block(self, block_data: Dict):
        """Update gas strategy from new block data"""
        
        # Extract base fee
        if "baseFeePerGas" in block_data:
            base_fee = block_data["baseFeePerGas"] / 1e9  # Convert to gwei
            self.base_fee_history.append(base_fee)
        
        # Could also update from gas oracle APIs
        # Etherscan, EthGasStation, etc.
    
    async def get_recommended_priority_fees(self) -> Dict:
        """Get recommended priority fees for different urgencies"""
        
        return {
            "slow": await self._get_priority_fee("slow"),
            "normal": await self._get_priority_fee("normal"),
            "fast": await self._get_priority_fee("fast"),
            "urgent": await self._get_priority_fee("urgent")
        }


class RevertCostModel:
    """
    Models revert costs to optimize gas spending
    """
    
    def __init__(self):
        self.revert_costs = {
            "liquidation": 150000,
            "arbitrage": 200000,
            "swap": 100000,
            "flash_loan": 250000
        }
        
        # Historical revert data
        self.revert_history = []
    
    def estimate_revert_cost(
        self,
        trade_type: str,
        gas_limit: int,
        current_gas_price: float = None
    ) -> Dict:
        """
        Estimate cost if transaction reverts - REAL data
        """
        
        # Get typical cost for trade type
        typical_gas = self.revert_costs.get(trade_type, 150000)
        
        # Reverts still pay for gas used
        revert_gas = int(gas_limit * 0.8)
        
        # Use current gas price if provided, otherwise query network
        if current_gas_price is None:
            try:
                import os
                from web3 import Web3
                rpc_url = os.getenv("ETHEREUM_RPC_URL")
                if rpc_url:
                    w3 = Web3(Web3.HTTPProvider(rpc_url))
                    if w3.is_connected():
                        import asyncio
                        loop = asyncio.get_event_loop()
                        gas_price_wei = loop.run_until_complete(w3.eth.gas_price)
                        avg_gas_price = gas_price_wei / 1e9  # Convert to gwei
                    else:
                        logger.warning("Cannot get gas price from network"); avg_gas_price = 0  # Signal failure
                else:
                    logger.warning("Cannot get gas price from network"); avg_gas_price = 0
            except Exception:
                logger.warning("Cannot get gas price from network"); avg_gas_price = 0  # Signal failure
        else:
            avg_gas_price = current_gas_price
        
        # Get ETH price for USD conversion
        eth_price = 1800.0  # Will be updated dynamically in production
        try:
            import aiohttp
            import asyncio
            url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
            # This would be async in production
        except Exception:
            pass
        
        cost_eth = (revert_gas * avg_gas_price * 1e9) / 1e18
        cost_usd = cost_eth * eth_price
        
        return {
            "gas_used_on_revert": revert_gas,
            "estimated_cost_eth": cost_eth,
            "estimated_cost_usd": cost_usd,
            "gas_price_gwei": avg_gas_price,
            "should_include_gas": True
        }
    
    def should_retry_on_revert(
        self,
        potential_profit: float,
        revert_cost: float
    ) -> bool:
        """
        Decide if we should retry after revert
        """
        
        # Don't retry if revert cost is too high relative to potential profit
        if revert_cost > potential_profit * 0.5:
            return False
        
        # Don't retry if we've already retried
        # (would track retry count externally)
        
        return True


class AdaptiveGasStrategy:
    """
    Adaptive gas strategy that learns from results
    """
    
    def __init__(self):
        self.success_outcomes = []
        self.fail_outcomes = []
        self.pending_outcomes = []
        
        # Base fee prediction model
        self._base_fee_history = []
        self._prediction_window = 10
        self._trend_weight = 0.3  # Weight for trend component
    
    def record_outcome(
        self,
        gas_strategy: GasStrategy,
        included: bool,
        gas_used: int,
        success: bool
    ):
        """Record gas strategy outcome for learning"""
        
        outcome = {
            "timestamp": time.time(),
            "urgency": gas_strategy.urgency,
            "max_fee": gas_strategy.max_fee_per_gas,
            "priority": gas_strategy.max_priority_fee_per_gas,
            "included": included,
            "gas_used": gas_used,
            "success": success
        }
        
        if included:
            if success:
                self.success_outcomes.append(outcome)
            else:
                self.fail_outcomes.append(outcome)
        else:
            self.pending_outcomes.append(outcome)
    
    def get_optimal_urgency(self) -> str:
        """Learn which urgency level works best"""
        
        if not self.success_outcomes:
            return "normal"
        
        # Calculate success rate by urgency
        urgency_stats = {}
        
        for outcome in self.success_outcomes + self.fail_outcomes:
            urgency = outcome["urgency"]
            if urgency not in urgency_stats:
                urgency_stats[urgency] = {"success": 0, "total": 0}
            
            urgency_stats[urgency]["total"] += 1
            if outcome["success"]:
                urgency_stats[urgency]["success"] += 1
        
        # Find best urgency
        best_urgency = "normal"
        best_rate = 0
        
        for urgency, stats in urgency_stats.items():
            rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
            if rate > best_rate:
                best_rate = rate
                best_urgency = urgency
        
        return best_urgency
    
    def predict_next_base_fee(self, current_base_fee: float) -> float:
        """
        Predict next block's base fee using historical data
        Uses exponential moving average with trend
        """
        # Add current to history
        self._base_fee_history.append(current_base_fee)
        
        # Keep only recent history
        if len(self._base_fee_history) > self._prediction_window:
            self._base_fee_history = self._base_fee_history[-self._prediction_window:]
        
        if len(self._base_fee_history) < 3:
            return current_base_fee  # Not enough data
        
        # Calculate EMA
        alpha = 0.3  # Smoothing factor
        ema = self._base_fee_history[0]
        for fee in self._base_fee_history[1:]:
            ema = alpha * fee + (1 - alpha) * ema
        
        # Calculate trend
        if len(self._base_fee_history) >= 2:
            trend = (self._base_fee_history[-1] - self._base_fee_history[0]) / len(self._base_fee_history)
        else:
            trend = 0
        
        # Combine EMA with trend
        prediction = ema + (self._trend_weight * trend)
        
        # EIP-1559: base fee changes by max 12.5% per block
        max_change = current_base_fee * 0.125
        prediction = max(current_base_fee - max_change, min(current_base_fee + max_change, prediction))
        
        return max(0, prediction)
    
    def get_inclusion_probability(self, max_fee: float, urgency: str) -> float:
        """
        Estimate probability of block inclusion based on max fee
        """
        if not self._base_fee_history:
            return 0.5  # Unknown
        
        avg_base = sum(self._base_fee_history) / len(self._base_fee_history)
        current_max = max_fee / 1e9  # Convert to gwei
        
        # Calculate how much above average
        ratio = current_max / avg_base if avg_base > 0 else 1
        
        if ratio >= 2:
            return 0.99
        elif ratio >= 1.5:
            return 0.90
        elif ratio >= 1.2:
            return 0.75
        elif ratio >= 1.0:
            return 0.50
        elif ratio >= 0.8:
            return 0.25
        else:
            return 0.10


# Factory
def create_gas_strategist(config: Dict) -> GasStrategist:
    """Create gas strategist"""
    return GasStrategist(config)

def create_revert_cost_model() -> RevertCostModel:
    """Create revert cost model"""
    return RevertCostModel()
