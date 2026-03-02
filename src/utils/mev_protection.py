"""
Real-Time MEV Protection
Sandwich detection, front-run protection, back-run detection
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


class MEVThreat(Enum):
    """Types of MEV threats"""
    SANDWICH = "sandwich"
    FRONTRUN = "frontrun"
    BACKRUN = "backrun"
    LARGE_ORDER = "large_order"
    FLASH_LOAN = "flash_loan"
    NONE = "none"


@dataclass
class MEVTransaction:
    """Detected transaction"""
    tx_hash: str
    sender: str
    token_in: str
    token_out: str
    amount_in: float
    gas_price: float
    timestamp: float
    threat_level: MEVThreat


@dataclass
class ProtectionResult:
    """MEV protection result"""
    is_safe: bool
    threats: List[MEVThreat]
    recommended_action: str  # "proceed", "delay", "abort", "split"
    adjusted_slippage: float
    reason: str


class MEVProtection:
    """
    Real-time MEV protection system
    - Sandwich detection
    - Front-run monitoring
    - Back-run detection
    - Large order warnings
    - Flash loan detection
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Detection thresholds
        self.sandwich_threshold = config.get("sandwich_threshold", 0.01)  # 1% price impact
        self.frontrun_gas_multiplier = config.get("frontrun_gas_multiplier", 1.5)
        self.large_order_threshold = config.get("large_order_threshold", 100000)  # $100k
        self.flash_loan_amount_threshold = config.get("flash_loan_amount_threshold", 1000000)  # $1M
        
        # Monitored mempool
        self.pending_txs: deque = deque(maxlen=1000)
        self.recent_swaps: deque = deque(maxlen=100)
        
        # Protection mode
        self.mode = config.get("mode", "paranoid")  # "relaxed", "normal", "paranoid"
        
        # Statistics
        self.total_scanned = 0
        self.threats_detected = 0
        self.blocks_protected = 0
    
    async def analyze_transaction(self, tx: Dict) -> ProtectionResult:
        """Analyze a transaction for MEV threats"""
        self.total_scanned += 1
        
        threats = []
        
        # Check for each threat type
        sandwich = await self._detect_sandwich(tx)
        if sandwich:
            threats.append(MEVThreat.SANDWICH)
        
        frontrun = await self._detect_frontrun(tx)
        if frontrun:
            threats.append(MEVThreat.FRONTRUN)
        
        large_order = await self._detect_large_order(tx)
        if large_order:
            threats.append(MEVThreat.LARGE_ORDER)
        
        flash_loan = await self._detect_flash_loan(tx)
        if flash_loan:
            threats.append(MEVThreat.FLASH_LOAN)
        
        # Determine action based on mode and threats
        action, adjusted_slippage, reason = self._determine_protection(
            threats, tx
        )
        
        if threats:
            self.threats_detected += 1
        
        return ProtectionResult(
            is_safe=len(threats) == 0,
            threats=threats,
            recommended_action=action,
            adjusted_slippage=adjusted_slippage,
            reason=reason
        )
    
    async def _detect_sandwich(self, tx: Dict) -> bool:
        """
        Detect potential sandwich attack
        - Look for large swaps before/after our swap
        - Check for suspicious gas patterns
        """
        if self.mode == "relaxed":
            return False
        
        # In production, would monitor mempool for:
        # 1. Large swaps in same block before our tx
        # 2. Large swaps after our tx
        # 3. Same token pair
        # 4. Similar amounts
        
        # For now, use heuristic: high gas + large amount
        gas_price = tx.get("gas_price", 0)
        amount = tx.get("amount", 0)
        
        # If gas is very high (>100 gwei), suspicious
        if gas_price > 100:
            logger.warning(f"⚠️ High gas price detected: {gas_price} gwei")
            return True
        
        return False
    
    async def _detect_frontrun(self, tx: Dict) -> bool:
        """Detect potential front-running"""
        if self.mode == "relaxed":
            return False
        
        gas_price = tx.get("gas_price", 0)
        our_gas = self.config.get("default_gas_gwei", 30)
        
        # If someone is paying significantly more
        if gas_price > our_gas * self.frontrun_gas_multiplier:
            logger.warning(f"⚠️ Possible front-run detected: {gas_price} vs {our_gas} gwei")
            return True
        
        return False
    
    async def _detect_large_order(self, tx: Dict) -> bool:
        """Detect large orders that might be MEV targets"""
        amount = tx.get("amount_usd", 0)
        
        if amount > self.large_order_threshold:
            logger.warning(f"⚠️ Large order detected: ${amount}")
            return True
        
        return False
    
    async def _detect_flash_loan(self, tx: Dict) -> bool:
        """Detect flash loan usage (advanced)"""
        # In production, would analyze:
        # 1. Transaction origin
        # 2. Contract interactions
        # 3. Token flows
        # 4. Profit extraction patterns
        
        # This is complex - requires bytecode analysis
        # For now, use amount threshold as proxy
        
        amount = tx.get("amount_usd", 0)
        
        if amount > self.flash_loan_amount_threshold:
            logger.warning(f"⚠️ Potential flash loan: ${amount}")
            return True
        
        return False
    
    def _determine_protection(
        self,
        threats: List[MEVThreat],
        tx: Dict
    ) -> Tuple[str, float, str]:
        """Determine protection action based on threats"""
        
        if not threats:
            return "proceed", 0.0, "No MEV threats detected"
        
        # Determine adjusted slippage based on threats
        adjusted_slippage = 0.0
        
        if MEVThreat.SANDWICH in threats:
            adjusted_slippage += 0.02  # +2%
        
        if MEVThreat.FRONTRUN in threats:
            adjusted_slippage += 0.01  # +1%
        
        if MEVThreat.LARGE_ORDER in threats:
            adjusted_slippage += 0.03  # +3%
        
        if MEVThreat.FLASH_LOAN in threats:
            adjusted_slippage += 0.05  # +5%
        
        # Determine action based on mode
        if self.mode == "paranoid":
            if threats:
                return "abort", adjusted_slippage, f"Threats detected: {[t.value for t in threats]}"
        
        elif self.mode == "normal":
            if MEVThreat.SANDWICH in threats or MEVThreat.FLASH_LOAN in threats:
                return "delay", adjusted_slippage, "Delaying for safety"
            return "proceed", adjusted_slippage, "Proceeding with adjusted slippage"
        
        else:  # relaxed
            return "proceed", adjusted_slippage, "Proceeding with caution"
        
        return "proceed", adjusted_slippage, "Default proceed"
    
    async def monitor_mempool(self, mempool_txs: List[Dict]) -> List[MEVTransaction]:
        """Monitor mempool for MEV threats"""
        threats = []
        
        for tx in mempool_txs:
            result = await self.analyze_transaction(tx)
            
            if not result.is_safe:
                threats.append(MEVTransaction(
                    tx_hash=tx.get("hash", ""),
                    sender=tx.get("from", ""),
                    token_in=tx.get("token_in", ""),
                    token_out=tx.get("token_out", ""),
                    amount_in=tx.get("amount", 0),
                    gas_price=tx.get("gas_price", 0),
                    timestamp=time.time(),
                    threat_level=result.threats[0] if result.threats else MEVThreat.NONE
                ))
        
        return threats
    
    def get_protection_stats(self) -> Dict:
        """Get protection statistics"""
        return {
            "total_scanned": self.total_scanned,
            "threats_detected": self.threats_detected,
            "protection_rate": (
                self.threats_detected / self.total_scanned 
                if self.total_scanned > 0 else 0
            ),
            "mode": self.mode,
            "blocks_protected": self.blocks_protected
        }


class SandwichProtection:
    """Specialized sandwich attack protection"""
    
    def __init__(self):
        self.swap_history = deque(maxlen=100)
    
    def record_swap(self, token_pair: str, amount: float, price_impact: float):
        """Record a swap for sandwich detection"""
        self.swap_history.append({
            "pair": token_pair,
            "amount": amount,
            "impact": price_impact,
            "timestamp": time.time()
        })
    
    def check_sandwich_risk(self, our_amount: float, token_pair: str) -> float:
        """
        Calculate sandwich risk score (0-1)
        """
        risk = 0.0
        
        # Check recent swaps in same pair
        recent_swaps = [
            s for s in self.swap_history
            if s["pair"] == token_pair
            and time.time() - s["timestamp"] < 60  # Last 60 seconds
        ]
        
        if not recent_swaps:
            return 0.0
        
        # More recent large swaps = higher risk
        for swap in recent_swaps:
            if swap["impact"] > 0.01:  # >1% impact
                risk += 0.3
        
        # Our large amount increases risk
        if our_amount > 100000:  # >$100k
            risk += 0.3
        
        return min(1.0, risk)


# Factory
def create_mev_protection(config: Dict = None) -> MEVProtection:
    """Create MEV protection instance"""
    return MEVProtection(config or {})


def create_sandwich_protection() -> SandwichProtection:
    """Create sandwich protection instance"""
    return SandwichProtection()
