"""
Cross-Chain Oracle Integration
LayerZero, Axelar - for multi-chain price feeds
"""

import asyncio
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CrossChainPrice:
    """Price from cross-chain source"""
    token: str
    price_usd: float
    source: str  # "layerzero", "axelar", "wormhole"
    block_confirmations: int
    timestamp: float


class CrossChainOracle:
    """
    Cross-chain oracle integration for multi-chain price feeds
    - LayerZero OApp
    - Axelar GMP
    - Wormhole
    """
    
    # LayerZero endpoint IDs
    LAYERZERO_CHAIN_IDS = {
        "ethereum": 101,
        "arbitrum": 110,
        "optimism": 111,
        "polygon": 109,
        "avalanche": 106,
        "bsc": 102,
        "base": 184,
    }
    
    # Axelar chain names
    AXELAR_CHAIN_NAMES = {
        "ethereum": "ethereum",
        "arbitrum": "arbitrum",
        "optimism": "optimism",
        "polygon": "polygon",
        "avalanche": "avalanche",
        "bsc": "binance",
    }
    
    def __init__(self, config: Dict):
        self.config = config
        self.layerzero_config = config.get("layerzero", {})
        self.axelar_config = config.get("axelar", {})
        
        # Cache
        self._price_cache: Dict[str, CrossChainPrice] = {}
        self._cache_ttl = 60  # 60 seconds for cross-chain
        
        # Active sources
        self._active_sources = ["layerzero", "axelar"]
    
    async def get_price(self, token: str, chain: str = "ethereum") -> Optional[CrossChainPrice]:
        """Get price from cross-chain oracle"""
        token = token.upper()
        chain = chain.lower()
        
        # Check cache
        cache_key = f"{token}:{chain}"
        if cache_key in self._price_cache:
            cached = self._price_cache[cache_key]
            if (asyncio.get_event_loop().time() - cached.timestamp) < self._cache_ttl:
                return cached
        
        # Fetch from all sources
        prices = []
        
        if "layerzero" in self._active_sources:
            price = await self._get_layerzero_price(token, chain)
            if price:
                prices.append(price)
        
        if "axelar" in self._active_sources:
            price = await self._get_axelar_price(token, chain)
            if price:
                prices.append(price)
        
        if not prices:
            logger.warning(f"No cross-chain price for {token} on {chain}")
            return None
        
        # Return best price (most recent)
        best = max(prices, key=lambda p: p.timestamp)
        self._price_cache[cache_key] = best
        
        return best
    
    async def _get_layerzero_price(self, token: str, chain: str) -> Optional[CrossChainPrice]:
        """Get price via LayerZero"""
        try:
            # In production, would call LayerZero OApp
            # This requires:
            # 1. Deployed OApp contract
            # 2. Configured endpoint
            # 3. Price feed adapter
            
            # For now, return None to use other sources
            # Real implementation would query the OApp
            return None
            
        except Exception as e:
            logger.debug(f"LayerZero price failed: {e}")
            return None
    
    async def _get_axelar_price(self, token: str, chain: str) -> Optional[CrossChainPrice]:
        """Get price via Axelar GMP"""
        try:
            # In production, would call Axelar GMP
            # This requires:
            # 1. Deployed GMP contract
            # 2. Configured validators
            # 3. Gateway setup
            
            return None
            
        except Exception as e:
            logger.debug(f"Axelar price failed: {e}")
            return None
    
    async def get_multi_chain_prices(self, token: str) -> Dict[str, CrossChainPrice]:
        """Get price for token across multiple chains"""
        prices = {}
        
        for chain in self.LAYERZERO_CHAIN_IDS.keys():
            price = await self.get_price(token, chain)
            if price:
                prices[chain] = price
        
        return prices
    
    def get_aggregated_price(self, token: str) -> Optional[float]:
        """Get weighted average across all chains"""
        prices = asyncio.get_event_loop().run_until_complete(
            self.get_multi_chain_prices(token)
        )
        
        if not prices:
            return None
        
        # Simple average (could be weighted by chain TVL)
        return sum(p.price_usd for p in prices.values()) / len(prices)


class LayerZeroIntegrator:
    """LayerZero OApp integration helper"""
    
    def __init__(self, endpoint_id: int, config: Dict):
        self.endpoint_id = endpoint_id
        self.config = config
        self.oapp_address = config.get("oapp_address")
    
    async def send_price_request(self, target_chain: int, token: str) -> bool:
        """Send cross-chain price request"""
        # In production: encode and send via LayerZero
        logger.info(f"Requesting {token} price from chain {target_chain}")
        return True
    
    async def receive_price_response(self) -> Optional[Dict]:
        """Receive price response from cross-chain"""
        # In production: decode from LayerZero message
        return None


class AxelarIntegrator:
    """Axelar GMP integration helper"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.gateway = config.get("gateway")
        self.gas_service = config.get("gas_service")
    
    async def call_contract_via_axelar(
        self,
        destination_chain: str,
        contract_address: str,
        payload: bytes
    ) -> str:
        """Execute cross-chain contract call via Axelar"""
        # In production:
        # 1. Approve tokens if needed
        # 2. Call gateway.execute()
        # 3. Wait for confirmation
        logger.info(f"Calling {contract_address} on {destination_chain}")
        return "pending"
    
    async def get_gas_estimate(
        self,
        destination_chain: str,
        payload_size: int
    ) -> Dict:
        """Estimate gas for cross-chain call"""
        # In production: query Axelar gas service
        return {
            "gas_limit": 200000,
            "gas_price": "0.001",
            "estimated_cost_usd": 5.0
        }


# Factory
def create_cross_chain_oracle(config: Dict) -> CrossChainOracle:
    """Create cross-chain oracle instance"""
    return CrossChainOracle(config)


def create_layerzero_integrator(config: Dict) -> LayerZeroIntegrator:
    """Create LayerZero integrator"""
    return LayerZeroIntegrator(
        endpoint_id=config.get("endpoint_id", 101),
        config=config
    )


def create_axelar_integrator(config: Dict) -> AxelarIntegrator:
    """Create Axelar integrator"""
    return AxelarIntegrator(config)
