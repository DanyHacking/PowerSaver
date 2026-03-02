"""
Flash Loan Detection
Detect and analyze flash loan usage in transactions
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class FlashLoanInfo:
    """Flash loan details"""
    tx_hash: str
    protocol: str  # "aave", "uniswap", "dydx", "balancer"
    tokens: List[str]
    total_amount_usd: float
    block_number: int
    timestamp: float


@dataclass
class FlashLoanAnalysis:
    """Analysis result"""
    is_flash_loan: bool
    protocols_used: List[str]
    total_borrowed_usd: float
    profit_usd: float
    is_suspicious: bool
    risk_score: float  # 0-1


class FlashLoanDetector:
    """
    Flash Loan Detection System
    - Detect flash loan usage in transactions
    - Analyze patterns
    - Identify suspicious activity
    """
    
    # Known flash loan protocols
    FLASH_LOAN_PROTOCOLS = {
        # Aave
        "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9": "aave_v2",
        "0x87870Bca3F3fD6335C3FbdC83E7a82f43aa5B6": "aave_v3",
        
        # Uniswap
        "0xE592427A0AEce92De3Edee1F18E0157C05861564": "uniswap_v3",
        
        # dYdX
        "0x1E0447b19BB6ECFdAE41AE6E5a7eB7CbEaE2aEd": "dydx",
        
        # Balancer
        "0xBA12222222228d8Ba445958a75a0704d566BF2C8": "balancer_vault",
        
        # MakerDAO
        "0x35fA164735182de50AfBaeAeF1248d9d4CC17a1": "makerdao",
        
        # Cream
        "0xB636e7c1C38c9F72eDa5cE3b8358a3C6016D0A0": "cream",
    }
    
    # Flash loan tokens (commonly borrowed)
    FL_TOKEN_ADDRESSES = {
        "0x6B175474E89094C44Da98b954EedE6C8EDc609666",  # DAI
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
        "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # USDT
        "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",  # WBTC
        "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
    }
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Detection settings
        self.min_amount_usd = config.get("min_amount_usd", 10000)  # $10k minimum
        self.max_profit_usd = config.get("max_profit_usd", 1000)  # $1k reasonable profit
        
        # History
        self.detected_loans: deque = deque(maxlen=100)
        self.address_history: Dict[str, List[FlashLoanInfo]] = {}
        
        # Statistics
        self.total_scanned = 0
        self.total_detected = 0
    
    async def analyze_transaction(self, tx: Dict) -> FlashLoanAnalysis:
        """
        Analyze a transaction for flash loan usage
        """
        self.total_scanned += 1
        
        protocols_used = []
        total_borrowed = 0.0
        
        # In production, would analyze:
        # 1. Transaction trace
        # 2. Internal transactions
        # 3. Token transfers
        # 4. Contract calls
        
        # Check if any known flash loan protocol was called
        for addr, protocol in self.FLASH_LOAN_PROTOCOLS.items():
            if addr in str(tx.get("to", "")).lower():
                protocols_used.append(protocol)
        
        # Check for large token transfers in
        # (would require full trace in production)
        
        is_flash_loan = len(protocols_used) > 0
        
        if is_flash_loan:
            self.total_detected += 1
            self.detected_loans.append(FlashLoanInfo(
                tx_hash=tx.get("hash", ""),
                protocol=", ".join(protocols_used),
                tokens=[],
                total_amount_usd=total_borrowed,
                block_number=tx.get("block_number", 0),
                timestamp=tx.get("timestamp", 0)
            ))
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(
            is_flash_loan, protocols_used, total_borrowed
        )
        
        is_suspicious = risk_score > 0.7
        
        return FlashLoanAnalysis(
            is_flash_loan=is_flash_loan,
            protocols_used=protocols_used,
            total_borrowed_usd=total_borrowed,
            profit_usd=0,  # Would calculate from trace
            is_suspicious=is_suspicious,
            risk_score=risk_score
        )
    
    def _calculate_risk_score(
        self,
        is_flash_loan: bool,
        protocols: List[str],
        amount_usd: float
    ) -> float:
        """
        Calculate risk score for flash loan transaction
        0 = safe, 1 = very suspicious
        """
        score = 0.0
        
        if not is_flash_loan:
            return 0.0
        
        # Multiple protocols = more suspicious
        if len(protocols) > 1:
            score += 0.3
        
        # Very large amount = more suspicious
        if amount_usd > 1000000:  # >$1M
            score += 0.3
        elif amount_usd > 100000:  # >$100k
            score += 0.1
        
        # Unknown protocol = more suspicious
        # (would check against known safe protocols)
        
        return min(1.0, score)
    
    async def check_address(self, address: str) -> List[FlashLoanInfo]:
        """Get flash loan history for an address"""
        return self.address_history.get(address.lower(), [])
    
    def get_stats(self) -> Dict:
        """Get detection statistics"""
        return {
            "total_scanned": self.total_scanned,
            "total_detected": self.total_detected,
            "detection_rate": (
                self.total_detected / self.total_scanned
                if self.total_scanned > 0 else 0
            )
        }


class FlashLoanProtection:
    """Protection against flash loan attacks"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.min_blocks = config.get("min_confirmation_blocks", 1)
        
        # Known flash loan attack patterns
        self.attack_patterns = {
            "oracle_manipulation": ["swap", "oracle", "update"],
            "double_trading": ["swap", "swap", "transfer"],
            "arbitrage": ["swap", "swap"],
        }
    
    def should_block(self, analysis: FlashLoanAnalysis) -> Tuple[bool, str]:
        """
        Determine if transaction should be blocked
        Returns: (should_block, reason)
        """
        if not analysis.is_flash_loan:
            return False, ""
        
        # If suspicious risk score, block
        if analysis.risk_score > 0.8:
            return True, f"High risk score: {analysis.risk_score:.2f}"
        
        # If multiple protocols used, might be attack
        if len(analysis.protocols_used) > 2:
            return True, "Multiple flash loan protocols"
        
        return False, ""
    
    def get_recommended_slippage(
        self,
        is_flash_loan: bool,
        amount_usd: float
    ) -> float:
        """
        Get recommended slippage based on flash loan presence
        """
        base_slippage = 0.003  # 0.3%
        
        if not is_flash_loan:
            return base_slippage
        
        # Increase slippage for flash loans
        if amount_usd > 1000000:
            return base_slippage * 5  # 1.5%
        elif amount_usd > 100000:
            return base_slippage * 3  # 0.9%
        
        return base_slippage * 2  # 0.6%


# Factory
def create_flash_loan_detector(config: Dict = None) -> FlashLoanDetector:
    """Create flash loan detector"""
    return FlashLoanDetector(config or {})


def create_flash_loan_protection(config: Dict = None) -> FlashLoanProtection:
    """Create flash loan protection"""
    return FlashLoanProtection(config or {})
