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
        """Get current base fee from network"""
        # In production: query RPC for latest block
        # Default fallback
        if self.base_fee_history:
            return self.base_fee_history[-1]
        
        return 20  # 20 gwei default
    
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
        gas_limit: int
    ) -> Dict:
        """
        Estimate cost if transaction reverts
        """
        
        # Get typical cost for trade type
        typical_gas = self.revert_costs.get(trade_type, 150000)
        
        # Reverts still pay for gas used
        # We assume 80% of gas limit is consumed on revert
        revert_gas = int(gas_limit * 0.8)
        
        # Estimate cost
        avg_gas_price = 30  # gwei (conservative)
        cost_eth = (revert_gas * avg_gas_price * 1e9) / 1e18
        cost_usd = cost_eth * 1800  # Assume ETH $1800
        
        return {
            "gas_used_on_revert": revert_gas,
            "estimated_cost_eth": cost_eth,
            "estimated_cost_usd": cost_usd,
            "should_include_gas": True  # Always include gas for protection
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


# Factory
def create_gas_strategist(config: Dict) -> GasStrategist:
    """Create gas strategist"""
    return GasStrategist(config)

def create_revert_cost_model() -> RevertCostModel:
    """Create revert cost model"""
    return RevertCostModel()
