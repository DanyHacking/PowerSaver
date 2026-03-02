"""
AGGRESSIVE TRADING OPTIMIZATIONS
Legal competitive edge without manipulation
"""

import asyncio
import logging
import time
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)


# ============== LOW LATENCY INFRASTRUCTURE ==============

class LowLatencyRouter:
    """
    Ultra-low latency routing
    Multiple RPC endpoints with latency tracking
    """
    
    RPC_ENDPOINTS = {
        # Public RPCs (backup)
        "public_eth": "https://eth.llamarpc.com",
        "public_infura": "https://mainnet.infura.io/v3/",
        "publicalchemy": "https://eth-mainnet.g.alchemy.com/v2/",
        
        # Premium/Low latency
        "alchemy": "https://eth-mainnet.g.alchemy.com/v2/",
        "quicknode": "https://some-quicknode-endpoint",
        "flashbots": "https://rpc.mevblocker.io",
        
        # Private P2P
        "bloxroute": "https://bloxroute.blxrbg.com",
        "titan": "https://rpc.titanbuilder.xyz",
        "beaver": "https://rpc.beaverbuild.org",
    }
    
    def __init__(self):
        self._latencies = {name: float('inf') for name in self.RPC_ENDPOINTS}
        self._web3_instances = {}
        self._last_check = {}
        self._check_interval = 5  # seconds
        
        # Best RPC tracking
        self._best_rpc = None
        self._fallback_rpc = None
    
    async def initialize(self):
        """Initialize and test all RPCs"""
        logger.info("🔍 Testing RPC endpoints...")
        
        tasks = []
        for name, url in self.RPC_ENDPOINTS.items():
            tasks.append(self._test_rpc(name, url))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for name, latency in zip(self.RPC_ENDPOINTS.keys(), results):
            if isinstance(latency, (int, float)) and latency < 10000:
                self._latencies[name] = latency
        
        self._update_best_rpc()
        
        logger.info(f"✅ Best RPC: {self._best_rpc} ({self._latencies.get(self._best_rpc, 'inf'):.0f}ms)")
    
    async def _test_rpc(self, name: str, url: str) -> float:
        """Test RPC latency"""
        try:
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(url))
            
            start = time.perf_counter()
            block = w3.eth.block_number
            latency = (time.perf_counter() - start) * 1000
            
            if block > 0:
                return latency
            return float('inf')
        except:
            return float('inf')
    
    def _update_best_rpc(self):
        """Update best RPC based on latency"""
        available = [(n, l) for n, l in self._latencies.items() if l < 10000]
        
        if not available:
            self._best_rpc = "public_eth"
            return
        
        # Sort by latency
        available.sort(key=lambda x: x[1])
        self._best_rpc = available[0][0]
        self._fallback_rpc = available[1][0] if len(available) > 1 else available[0][0]
    
    def get_best_rpc(self) -> str:
        """Get best RPC endpoint"""
        return self._best_rpc or "public_eth"
    
    def get_rpc_for_gas(self) -> str:
        """Get lowest latency RPC for gas updates"""
        # Gas needs fastest RPC
        return self.get_best_rpc()


# ============== BLOCK PREDICTION ==============

class BlockPredictor:
    """
    Statistical block prediction model
    Predicts next block timing for optimal submission
    """
    
    def __init__(self):
        self._block_times = deque(maxlen=100)
        self._base_fees = deque(maxlen=50)
        self._gas_prices = deque(maxlen=50)
        
        # Historical patterns
        self._hourly_pattern = {}  # hour -> avg_block_time
    
    def record_block(self, block_number: int, timestamp: int, base_fee: int):
        """Record block data"""
        self._block_times.append({
            "number": block_number,
            "timestamp": timestamp,
            "base_fee": base_fee
        })
        
        # Record base fee history
        self._base_fees.append(base_fee)
        
        # Track hourly patterns
        hour = time.gmtime(timestamp).tm_hour
        if hour not in self._hourly_pattern:
            self._hourly_pattern[hour] = deque(maxlen=50)
        
        if len(self._block_times) >= 2:
            block_time = self._block_times[-1]["timestamp"] - self._block_times[-2]["timestamp"]
            self._hourly_pattern[hour].append(block_time)
    
    def predict_next_block_time(self) -> float:
        """Predict seconds until next block"""
        if len(self._block_times) < 2:
            return 12.0  # Default
        
        # Average of recent blocks
        recent_times = []
        for i in range(1, min(len(self._block_times), 10)):
            t = self._block_times[-i]["timestamp"] - self._block_times[-i-1]["timestamp"]
            recent_times.append(t)
        
        avg = sum(recent_times) / len(recent_times) if recent_times else 12.0
        
        # Adjust for time of day
        current_hour = time.gmtime().tm_hour
        if current_hour in self._hourly_pattern and self._hourly_pattern[current_hour]:
            hourly_avg = sum(self._hourly_pattern[current_hour]) / len(self._hourly_pattern[current_hour])
            avg = (avg + hourly_avg) / 2
        
        return avg
    
    def predict_base_fee(self) -> int:
        """Predict next block base fee"""
        if len(self._base_fees) < 2:
            return self._base_fees[-1] if self._base_fees else 50000000000
        
        # Simple moving average with trend
        recent = list(self._base_fees)[-10:]
        
        # Calculate trend
        if len(recent) >= 5:
            first_half = sum(recent[:5]) / 5
            second_half = sum(recent[5:]) / 5
            trend = (second_half - first_half) / first_half
            
            # Cap at EIP-1559 max change (12.5%)
            current = recent[-1]
            max_change = current * 0.125
            predicted = current + (trend * max_change)
            
            return int(max(current * 0.875, min(current * 1.125, predicted)))
        
        return int(sum(recent) / len(recent))
    
    def get_optimal_submission_time(self) -> float:
        """Get optimal time to submit (seconds into block)"""
        # Submit in first 1/3 of block for best chance
        block_time = self.predict_next_block_time()
        return block_time / 3


# ============== GAS BIDDING STRATEGY ==============

class GasBiddingStrategy:
    """
    Aggressive gas bidding strategy
    Competitive but not wasteful
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        self.base_multiplier = config.get("base_multiplier", 1.2)  # 20% above base
        self.priority_multiplier = config.get("priority_multiplier", 1.5)
        
        # Block targeting
        self.target_blocks = config.get("target_blocks", 2)  # Within 2 blocks
        
        # History
        self._inclusion_history = deque(maxlen=100)
        self._failed_bids = deque(maxlen=50)
    
    def calculate_bid(
        self,
        current_base_fee: int,
        urgency: str,
        competition_level: float = 0.5
    ) -> Tuple[int, int]:
        """
        Calculate optimal gas bid
        Returns: (max_fee_per_gas, max_priority_fee_per_gas)
        """
        if urgency == "high":
            # High urgency: pay more to get in ASAP
            max_fee = int(current_base_fee * 2.0)
            priority = int(current_base_fee * 1.5)
        elif urgency == "medium":
            # Medium: competitive but not wasteful
            max_fee = int(current_base_fee * self.base_multiplier)
            priority = int(current_base_fee * self.priority_multiplier)
        else:
            # Low: wait for cheaper
            max_fee = int(current_base_fee * 1.1)
            priority = int(current_base_fee * 1.05)
        
        # Adjust for competition
        if competition_level > 0.7:
            max_fee = int(max_fee * 1.3)
            priority = int(priority * 1.3)
        
        return max_fee, priority
    
    def record_inclusion(self, bid: int, included: bool, blocks_waited: int):
        """Record bid outcome for learning"""
        self._inclusion_history.append({
            "bid": bid,
            "included": included,
            "blocks_waited": blocks_waited,
            "timestamp": time.time()
        })
    
    def get_success_rate(self) -> float:
        """Get inclusion success rate"""
        if not self._inclusion_history:
            return 0.5
        
        included = sum(1 for h in self._inclusion_history if h["included"])
        return included / len(self._inclusion_history)


# ============== LIQUIDATION MONITOR ==============

class AggressiveLiquidationMonitor:
    """
    Aggressive liquidation monitoring
    Scans multiple protocols for liquidation opportunities
    """
    
    PROTOCOLS = {
        "aave": {
            "subgraph": "https://api.thegraph.com/subgraphs/name/aave/protocol-v3",
            "health_threshold": 1.0,
            "reward_bps": 500  # 5%
        },
        "compound": {
            "subgraph": "https://api.thegraph.com/subgraphs/name/compoundv3/ethereum",
            "health_threshold": 1.0,
            "reward_bps": 500
        },
        "makerdao": {
            "subgraph": "https://api.thegraph.com/subgraphs/name/makerdao/邯郸",
            "health_threshold": 1.1,
            "reward_bps": 500
        },
        "radiant": {
            "subgraph": "https://api.thegraph.com/subgraphs/name/radiant-v2/arbitrum-one",
            "health_threshold": 1.0,
            "reward_bps": 500
        },
        "sonne": {
            "subgraph": "https://api.thegraph.com/subgraphs/name/sonnefinance/optimism",
            "health_threshold": 1.0,
            "reward_bps": 500
        }
    }
    
    def __init__(self, config: Dict):
        self.config = config
        
        self._opportunities = deque(maxlen=100)
        self._scanned_positions = set()
        
        # Timing
        self.scan_interval = config.get("scan_interval", 3)  # seconds
        self.max_latency = config.get("max_latency", 500)  # ms
    
    async def scan_all_protocols(self) -> List[Dict]:
        """Scan all protocols for liquidations"""
        opportunities = []
        
        tasks = []
        for protocol, config in self.PROTOCOLS.items():
            tasks.append(self._scan_protocol(protocol, config))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for protocol, result in zip(self.PROTOCOLS.keys(), results):
            if isinstance(result, list):
                opportunities.extend(result)
        
        # Sort by reward
        opportunities.sort(key=lambda x: x.get("max_reward", 0), reverse=True)
        
        return opportunities[:10]  # Top 10
    
    async def _scan_protocol(self, protocol: str, config: Dict) -> List[Dict]:
        """Scan single protocol"""
        # In production, would query subgraph
        # Simplified here
        return []
    
    def should_execute(self, opportunity: Dict, current_gas: float) -> bool:
        """Decide if liquidation is worth executing"""
        reward = opportunity.get("max_reward", 0)
        gas_cost_estimate = current_gas * 150000 / 1e9 * 1800  # rough estimate
        
        # Need positive expected value
        net_reward = reward - gas_cost_estimate
        
        return net_reward > self.config.get("min_profit", 10)


# ============== CROSS-CHAIN MONITOR ==============

class CrossChainOpportunityScanner:
    """
    Scan for cross-chain arbitrage opportunities
    """
    
    CHAIN_IDS = {
        "ethereum": 1,
        "arbitrum": 42161,
        "optimism": 10,
        "polygon": 137,
        "avalanche": 43114,
        "bsc": 56,
        "base": 8453,
    }
    
    def __init__(self, config: Dict):
        self.config = config
        
        # RPCs per chain
        self._rpcs = {
            "ethereum": config.get("eth_rpc", "https://eth.llamarpc.com"),
            "arbitrum": config.get("arb_rpc", "https://arb1.arbitrum.io/rpc"),
            "optimism": config.get("opt_rpc", "https://mainnet.optimism.io"),
            "polygon": config.get("poly_rpc", "https://polygon-rpc.com"),
        }
        
        self._prices = {}
    
    async def scan_all_chains(self) -> List[Dict]:
        """Scan all chains for price differences"""
        # Get prices from all chains
        tasks = []
        for chain, rpc in self._rpcs.items():
            tasks.append(self._get_chain_prices(chain, rpc))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Find opportunities
        opportunities = []
        
        # Compare ETH across chains
        if "ethereum" in self._prices and "arbitrum" in self._prices:
            eth_eth = self._prices["ethereum"].get("ETH", 0)
            eth_arb = self._prices["arbitrum"].get("ETH", 0)
            
            if eth_eth > 0 and eth_arb > 0:
                diff = abs(eth_eth - eth_arb) / min(eth_eth, eth_arb)
                
                if diff > 0.01:  # >1% difference
                    opportunities.append({
                        "type": "cross_chain_eth",
                        "buy_chain": "arbitrum" if eth_arb < eth_eth else "ethereum",
                        "sell_chain": "ethereum" if eth_arb < eth_eth else "arbitrum",
                        "profit_pct": diff * 100,
                        "estimated_profit": diff * 10000  # Assuming $10k trade
                    })
        
        return opportunities
    
    async def _get_chain_prices(self, chain: str, rpc: str) -> Dict:
        """Get prices from chain (simplified)"""
        # In production, would use actual oracle
        return {}


# ============== STATISTICAL MODELS ==============

class StatisticalPredictor:
    """
    Statistical models for price/market prediction
    """
    
    def __init__(self):
        self._price_history = {}
        self._volume_history = {}
    
    def add_price_point(self, token: str, price: float, volume: float):
        """Add price data point"""
        if token not in self._price_history:
            self._price_history[token] = deque(maxlen=1000)
            self._volume_history[token] = deque(maxlen=1000)
        
        self._price_history[token].append({
            "price": price,
            "volume": volume,
            "timestamp": time.time()
        })
    
    def predict_next_price(self, token: str) -> Optional[float]:
        """Simple linear regression prediction"""
        if token not in self._price_history or len(self._price_history[token]) < 10:
            return None
        
        prices = list(self._price_history[token])
        
        # Simple moving average
        return sum(p["price"] for p in prices[-10:]) / 10
    
    def get_momentum(self, token: str) -> float:
        """Get price momentum (-1 to 1)"""
        if token not in self._price_history or len(self._price_history[token]) < 5:
            return 0
        
        prices = list(self._price_history[token])
        
        recent = sum(p["price"] for p in prices[-3:]) / 3
        older = sum(p["price"] for p in prices[-5:-3]) / 2 if len(prices) >= 5 else recent
        
        if older == 0:
            return 0
        
        momentum = (recent - older) / older
        
        # Clamp to -1 to 1
        return max(-1, min(1, momentum * 10))


# ============== FACTORIES ==============

def create_low_latency_router() -> LowLatencyRouter:
    return LowLatencyRouter()

def create_block_predictor() -> BlockPredictor:
    return BlockPredictor()

def create_gas_bidding_strategy(config: Dict = None) -> GasBiddingStrategy:
    return GasBiddingStrategy(config or {})

def create_liquidation_monitor(config: Dict = None) -> AggressiveLiquidationMonitor:
    return AggressiveLiquidationMonitor(config or {})

def create_cross_chain_scanner(config: Dict = None) -> CrossChainOpportunityScanner:
    return CrossChainOpportunityScanner(config or {})

def create_statistical_predictor() -> StatisticalPredictor:
    return StatisticalPredictor()
