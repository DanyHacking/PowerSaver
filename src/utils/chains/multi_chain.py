"""
Multi-Chain Trading System
Supports: Ethereum, Arbitrum, Optimism, Base, Avalanche, Polygon
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import aiohttp

logger = logging.getLogger(__name__)


class ChainType(Enum):
    """Supported blockchain networks"""
    ETHEREUM = "ethereum"
    ARBITRUM = "arbitrum_one"
    OPTIMISM = "optimism"
    BASE = "base"
    AVALANCHE = "avalanche"
    POLYGON = "polygon"


@dataclass
class ChainConfig:
    """Chain configuration"""
    chain_id: int
    name: str
    rpc_url: str
    explorer_url: str
    native_token: str
    
    # Protocol addresses on this chain
    aave_pool: str
    uniswap_router: str
    sushiswap_router: str
    
    # Chain specific
    block_time: float  # seconds
    avg_gas_price: int  # gwei
    finality_blocks: int


# Chain configurations
CHAIN_CONFIGS = {
    ChainType.ETHEREUM: ChainConfig(
        chain_id=1,
        name="Ethereum Mainnet",
        rpc_url="",  # User must provide
        explorer_url="https://etherscan.io",
        native_token="ETH",
        aave_pool="0x87870Bca3F3fD6335C3F4ce6260135144110A857",
        uniswap_router="0xE592427A0AEce92De3Edee1F18E0157C05861564",
        sushiswap_router="0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F",
        block_time=12,
        avg_gas_price=30,
        finality_blocks=12
    ),
    ChainType.ARBITRUM: ChainConfig(
        chain_id=42161,
        name="Arbitrum One",
        rpc_url="",  # User must provide
        explorer_url="https://arbiscan.io",
        native_token="ETH",
        aave_pool="0x794a61358D6845594F94dc1DB02A252b5b4814aD",
        uniswap_router="0xE592427A0AEce92De3Edee1F18E0157C05861564",
        sushiswap_router="0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
        block_time=0.25,
        avg_gas_price=0.1,
        finality_blocks=1
    ),
    ChainType.OPTIMISM: ChainConfig(
        chain_id=10,
        name="Optimism",
        rpc_url="",  # User must provide
        explorer_url="https://optimistic.etherscan.io",
        native_token="ETH",
        aave_pool="0x794a61358D6845594F94dc1DB02A252b5b4814aD",
        uniswap_router="0xE592427A0AEce92De3Edee1F18E0157C05861564",
        sushiswap_router="0xE592427A0AEce92De3Edee1F18E0157C05861564",
        block_time=2,
        avg_gas_price=0.001,
        finality_blocks=1
    ),
    ChainType.BASE: ChainConfig(
        chain_id=8453,
        name="Base",
        rpc_url="",  # User must provide
        explorer_url="https://basescan.org",
        native_token="ETH",
        aave_pool="0xA238Dd8C94fD98a97d2e2a47D7D7d3aDb9d3e8D",
        uniswap_router="0x2626664c26033a13818c64f2f2a2E7aC13d3d93",
        sushiswap_router="0x2Db50a0AC005c16cE4f4A365C09B8aB75b3Eb3D8",
        block_time=2,
        avg_gas_price=0.001,
        finality_blocks=1
    ),
    ChainType.AVALANCHE: ChainConfig(
        chain_id=43114,
        name="Avalanche C-Chain",
        rpc_url="",  # User must provide
        explorer_url="https://snowtrace.io",
        native_token="AVAX",
        aave_pool="0x4F01AeD16D97E3aB5ab2b501154DC6bb3F3911cf",
        uniswap_router="0xE54Ca86531e17Ef3616d22ca28b0D86bC9B4fB9F",
        sushiswap_router="0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
        block_time=2,
        avg_gas_price=25,
        finality_blocks=1
    ),
    ChainType.POLYGON: ChainConfig(
        chain_id=137,
        name="Polygon",
        rpc_url="",  # User must provide
        explorer_url="https://polygonscan.com",
        native_token="MATIC",
        aave_pool="0x794a61358D6845594F94dc1DB02A252b5b4814aD",
        uniswap_router="0xE592427A0AEce92De3Edee1F18E0157C05861564",
        sushiswap_router="0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
        block_time=2,
        avg_gas_price=50,
        finality_blocks=1
    )
}


@dataclass
class CrossChainOpportunity:
    """Opportunity found across chains"""
    source_chain: ChainType
    target_chain: ChainType
    token_in: str
    token_out: str
    amount_in: float
    expected_profit: float
    gas_bridge_cost: float
    time_to_bridge: float
    confidence: float


class MultiChainManager:
    """
    Manages trading across multiple chains
    Finds the best opportunities across all supported networks
    """
    
    def __init__(self, rpc_urls: Dict[str, str], private_key: str):
        self.rpc_urls = rpc_urls
        self.private_key = private_key
        self.chains: Dict[ChainType, Any] = {}
        
        # Initialize chain configs
        for chain_type, config in CHAIN_CONFIGS.items():
            if rpc_urls.get(chain_type.value):
                config.rpc_url = rpc_urls[chain_type.value]
                self.chains[chain_type] = config
    
    async def scan_all_chains(self) -> List[CrossChainOpportunity]:
        """
        Scan all configured chains for opportunities
        Returns list of cross-chain opportunities
        """
        opportunities = []
        
        # Scan each chain in parallel
        tasks = [self._scan_chain(chain) for chain in self.chains.keys()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                opportunities.extend(result)
        
        # Sort by profit
        opportunities.sort(key=lambda x: x.expected_profit, reverse=True)
        
        return opportunities[:10]  # Top 10 opportunities
    
    async def _scan_chain(self, chain: ChainType) -> List[CrossChainOpportunity]:
        """Scan a single chain for opportunities"""
        opportunities = []
        
        config = self.chains.get(chain)
        if not config:
            return opportunities
        
        try:
            # Check for arbitrage between DEXes on this chain
            dex_opps = await self._find_dex_arbitrage(chain)
            opportunities.extend(dex_opps)
            
            # Check for liquidation opportunities
            liq_opps = await self._find_liquidations(chain)
            opportunities.extend(liq_opps)
            
        except Exception as e:
            logger.error(f"Chain scan failed for {chain.value}: {e}")
        
        return opportunities
    
    async def _find_dex_arbitrage(self, chain: ChainType) -> List[CrossChainOpportunity]:
        """Find DEX arbitrage opportunities on a chain"""
        opportunities = []
        
        # In production, query DEX prices and find spreads
        # This would analyze price differences between:
        # - Uniswap vs Sushiswap
        # - Different fee tiers on Uniswap V3
        # - Stablecoin pools
        
        return opportunities
    
    async def _find_liquidations(self, chain: ChainType) -> List[CrossChainOpportunity]:
        """Find liquidation opportunities on a chain"""
        opportunities = []
        
        config = self.chains.get(chain)
        if not config:
            return opportunities
        
        # Query the chain's lending protocol for liquidatable positions
        # Aave, Compound, etc. have different addresses per chain
        
        return opportunities
    
    async def execute_cross_chain(
        self, 
        opportunity: CrossChainOpportunity
    ) -> Dict:
        """Execute cross-chain opportunity"""
        # This would involve:
        # 1. Bridge funds to target chain
        # 2. Execute trade
        # 3. Bridge back (if needed)
        
        return {"status": "not_implemented", "opportunity": opportunity}


class GasOptimizer:
    """
    Advanced gas optimization for maximum profit
    """
    
    def __init__(self, chain_config: ChainConfig):
        self.config = chain_config
        self.gas_history: List[float] = []
        
    async def get_optimal_gas(self, urgency: str = "normal") -> Dict:
        """
        Calculate optimal gas strategy based on:
        - Current network congestion
        - Time of day
        - Block utilization
        - Historical patterns
        """
        # In production, this would:
        # 1. Fetch current base fee from network
        # 2. Analyze recent block fills
        # 3. Predict optimal priority fee
        
        base_fee = await self._get_current_base_fee()
        priority_fee = await self._calculate_priority_fee(urgency)
        
        return {
            "maxFeePerGas": base_fee + priority_fee,
            "maxPriorityFeePerGas": priority_fee,
            "estimated_time": self._estimate_inclusion_time(base_fee + priority_fee)
        }
    
    async def _get_current_base_fee(self) -> int:
        """Get current base fee from network"""
        # Would query RPC for latest block
        return int(self.config.avg_gas_price * 1e9)
    
    async def _calculate_priority_fee(self, urgency: str) -> int:
        """Calculate priority fee based on urgency"""
        multipliers = {
            "slow": 1.0,
            "normal": 1.5,
            "fast": 2.0,
            "urgent": 3.0
        }
        multiplier = multipliers.get(urgency, 1.5)
        return int(self.config.avg_gas_price * multiplier * 1e9)
    
    def _estimate_inclusion_time(self, total_gas: int) -> float:
        """Estimate time to block inclusion in seconds"""
        gas_ratio = total_gas / (self.config.avg_gas_price * 1e9)
        
        if gas_ratio > 2:
            return self.config.block_time * 3
        elif gas_ratio > 1.5:
            return self.config.block_time * 2
        elif gas_ratio > 1:
            return self.config.block_time
        else:
            return self.config.block_time * 0.5


class AutoCompound:
    """
    Auto-compound system
    Automatically reinvests profits to maximize compounding
    """
    
    def __init__(self, initial_capital: float, reinvest_threshold: float = 100):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.reinvest_threshold = reinvest_threshold
        self.compound_count = 0
        
    async def check_and_compound(self, current_profit: float) -> Dict:
        """
        Check if profit should be reinvested
        Returns compound action taken
        """
        if current_profit >= self.reinvest_threshold:
            self.current_capital += current_profit
            self.compound_count += 1
            
            return {
                "action": "compound",
                "amount_added": current_profit,
                "new_capital": self.current_capital,
                "compound_count": self.compound_count
            }
        
        return {
            "action": "hold",
            "amount": current_profit,
            "current_capital": self.current_capital
        }
    
    def get_stats(self) -> Dict:
        """Get compound statistics"""
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital * 100
        
        return {
            "initial_capital": self.initial_capital,
            "current_capital": self.current_capital,
            "total_return_percent": total_return,
            "compound_count": self.compound_count,
            "avg_compound_return": total_return / max(1, self.compound_count)
        }


class AdvancedRiskManager:
    """
    Advanced risk management with dynamic position sizing
    """
    
    def __init__(self, config: Dict):
        self.max_position_size = config.get("max_position_size", 50000)
        self.max_daily_loss = config.get("max_daily_loss", 5000)
        self.max_concurrent_trades = config.get("max_concurrent_trades", 3)
        
        # Dynamic risk parameters
        self.risk_multiplier = 1.0
        self.win_rate = 0.5
        self.avg_win = 0
        self.avg_loss = 0
        
        # Daily tracking
        self.daily_pnl = 0
        self.trades_today = 0
    
    def calculate_position_size(
        self, 
        opportunity_profit: float, 
        confidence: float,
        volatility: float
    ) -> float:
        """
        Calculate optimal position size using Kelly Criterion
        """
        # Kelly Criterion: f* = (bp - q) / b
        # where b = odds, p = probability of win, q = probability of loss
        
        if self.win_rate <= 0:
            return self.max_position_size * 0.1  # Conservative
        
        win_loss_ratio = abs(self.avg_win / max(self.avg_loss, 1))
        kelly_fraction = (win_loss_ratio * self.win_rate - (1 - self.win_rate)) / win_loss_ratio
        
        # Apply Kelly with conservative scaling (half-Kelly)
        kelly_fraction = max(0, min(kelly_fraction * 0.5, 0.25))
        
        # Adjust for confidence and volatility
        adjusted_size = self.max_position_size * kelly_fraction * confidence * (1 - volatility)
        
        # Apply risk multiplier
        adjusted_size *= self.risk_multiplier
        
        # Cap at maximum
        return min(adjusted_size, self.max_position_size)
    
    def update_performance(self, profit: float):
        """Update risk manager with trade result"""
        self.daily_pnl += profit
        self.trades_today += 1
        
        # Update win/loss stats
        if profit > 0:
            self.avg_win = (self.avg_win * (self.win_rate) + profit) / (self.win_rate + 1)
            self.win_rate = (self.win_rate * (self.trades_today - 1) + 1) / self.trades_today
        else:
            self.avg_loss = (self.avg_loss * (1 - self.win_rate) + abs(profit)) / (2 - self.win_rate)
            self.win_rate = self.win_rate * (self.trades_today - 1) / self.trades_today
        
        # Adjust risk multiplier based on daily performance
        if self.daily_pnl < -self.max_daily_loss:
            self.risk_multiplier = 0  # Stop trading for the day
        elif self.daily_pnl < 0:
            self.risk_multiplier = max(0.25, self.risk_multiplier * 0.5)
        elif self.daily_pnl > self.max_daily_loss * 2:
            self.risk_multiplier = min(1.5, self.risk_multiplier * 1.2)
    
    def can_trade(self) -> tuple[bool, str]:
        """Check if we can take new trades"""
        if self.trades_today >= self.max_concurrent_trades:
            return False, "Max concurrent trades reached"
        
        if self.daily_pnl <= -self.max_daily_loss:
            return False, "Daily loss limit reached"
        
        if self.risk_multiplier <= 0:
            return False, "Risk limit triggered"
        
        return True, "OK"
    
    def get_stats(self) -> Dict:
        """Get risk management stats"""
        return {
            "daily_pnl": self.daily_pnl,
            "trades_today": self.trades_today,
            "risk_multiplier": self.risk_multiplier,
            "win_rate": self.win_rate,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "can_trade": self.can_trade()[0]
        }
    
    def reset_daily(self):
        """Reset daily counters (call at start of each day)"""
        self.daily_pnl = 0
        self.trades_today = 0


# Factory functions
def create_multi_chain_manager(rpc_urls: Dict[str, str], private_key: str) -> MultiChainManager:
    """Create multi-chain manager"""
    return MultiChainManager(rpc_urls, private_key)

def create_gas_optimizer(chain: ChainType) -> GasOptimizer:
    """Create gas optimizer for chain"""
    config = CHAIN_CONFIGS.get(chain)
    if config:
        return GasOptimizer(config)
    return None

def create_auto_compound(initial_capital: float) -> AutoCompound:
    """Create auto-compound system"""
    return AutoCompound(initial_capital)

def create_advanced_risk_manager(config: Dict) -> AdvancedRiskManager:
    """Create advanced risk manager"""
    return AdvancedRiskManager(config)
