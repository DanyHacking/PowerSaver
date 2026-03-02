"""
Alchemy RPC Integration
Fast, reliable Ethereum node with enhanced APIs
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AlchemyConfig:
    """Alchemy configuration"""
    api_key: str
    network: str  # eth-mainnet, eth-sepolia, arb-mainnet, etc.
    webhook_id: Optional[str] = None
    max_requests_per_second: int = 50


class AlchemyProvider:
    """
    Alchemy Ethereum provider
    Features:
    - Enhanced APIs (debug, trace, txpool)
    - WebSocket support
    - Webhook notifications
    - Higher rate limits
    """
    
    BASE_URLS = {
        "eth-mainnet": "https://eth-mainnet.alchemyapi.io/v2",
        "eth-sepolia": "https://eth-sepolia.alchemyapi.io/v2",
        "arb-mainnet": "https://arb-mainnet.g.alchemy.com/v2",
        "arb-sepolia": "https://arb-sepolium.g.alchemy.com/v2",
        "opt-mainnet": "https://opt-mainnet.g.alchemy.com/v2",
        "opt-sepolia": "https://opt-sepolia.g.alchemy.com/v2",
        "base-mainnet": "https://base-mainnet.g.alchemy.com/v2",
        "base-sepolia": "https://base-sepolia.g.alchemy.com/v2",
        "polygon-mainnet": "https://polygon-mainnet.g.alchemy.com/v2",
        "polygon-amoy": "https://polygon-amoy.g.alchemy.com/v2",
    }
    
    def __init__(self, config: AlchemyConfig):
        self.config = config
        self.api_key = config.api_key
        self.network = config.network
        
        # Get base URL
        self.base_url = self.BASE_URLS.get(network, f"https://{network}.alchemyapi.io/v2")
        
        # Full URL
        self.url = f"{self.base_url}/{self.api_key}"
        
        # Enhanced API endpoints
        self.ws_url = self.url.replace("https://", "wss://").replace("/v2/", "/ws/")
        
        # Rate limiting
        self.max_rps = config.max_requests_per_second
        self.request_timestamps: List[float] = []
        
        # Caching
        self.block_cache: Dict[int, Dict] = {}
        self.price_cache: Dict[str, float] = {}
        
        logger.info(f"Alchemy initialized: {self.network}")
    
    async def _request(self, method: str, params: List = None) -> Any:
        """Make rate-limited request to Alchemy"""
        import aiohttp
        
        # Rate limiting
        now = asyncio.get_event_loop().time()
        self.request_timestamps = [t for t in self.request_timestamps if now - t < 1]
        
        if len(self.request_timestamps) >= self.max_rps:
            wait_time = 1 - (now - self.request_timestamps[0])
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self.request_timestamps.append(now)
        
        # Make request
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": 1
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, json=payload) as resp:
                data = await resp.json()
                if "error" in data:
                    raise Exception(data["error"])
                return data.get("result")
    
    # ═══════════════════════════════════════════════════════════
    # STANDARD ETH METHODS
    # ═══════════════════════════════════════════════════════════
    
    async def get_block_number(self) -> int:
        """Get latest block number"""
        result = await self._request("eth_blockNumber")
        return int(result, 16)
    
    async def get_block(self, block_number: int = None, full: bool = False) -> Dict:
        """Get block by number"""
        if block_number is None:
            block_number = await self.get_block_number()
        
        block_hex = hex(block_number)
        result = await self._request("eth_getBlockByNumber", [block_hex, full])
        
        # Cache full blocks
        if full:
            self.block_cache[block_number] = result
        
        return result
    
    async def get_balance(self, address: str, block: str = "latest") -> int:
        """Get ETH balance"""
        result = await self._request("eth_getBalance", [address, block])
        return int(result, 16)
    
    async def get_transaction_count(self, address: str, block: str = "latest") -> int:
        """Get transaction count (nonce)"""
        result = await self._request("eth_getTransactionCount", [address, block])
        return int(result, 16)
    
    async def get_transaction(self, tx_hash: str) -> Optional[Dict]:
        """Get transaction by hash"""
        result = await self._request("eth_getTransactionByHash", [tx_hash])
        return result
    
    async def get_transaction_receipt(self, tx_hash: str) -> Optional[Dict]:
        """Get transaction receipt"""
        result = await self._request("eth_getTransactionReceipt", [tx_hash])
        return result
    
    async def call(self, tx: Dict, block: str = "latest") -> str:
        """Execute call without creating transaction"""
        result = await self._request("eth_call", [tx, block])
        return result
    
    async def estimate_gas(self, tx: Dict) -> int:
        """Estimate gas for transaction"""
        result = await self._request("eth_estimateGas", [tx])
        return int(result, 16)
    
    async def get_gas_price(self) -> int:
        """Get current gas price"""
        result = await self._request("eth_gasPrice")
        return int(result, 16)
    
    async def send_raw_transaction(self, signed_tx: str) -> str:
        """Send signed transaction"""
        result = await self._request("eth_sendRawTransaction", [signed_tx])
        return result
    
    # ═══════════════════════════════════════════════════════════
    # ENHANCED ALCHEMY METHODS
    # ═══════════════════════════════════════════════════════════
    
    async def get_token_balances(self, address: str, tokens: List[str] = None) -> Dict:
        """
        Get token balances (Alchemy enhanced)
        Much faster than individual calls
        """
        if tokens:
            result = await self._request("alchemy_getTokenBalances", [address, tokens])
        else:
            # Get all ERC20 tokens
            result = await self._request("alchemy_getTokenBalances", [address, "erc20"])
        
        return result
    
    async def get_token_metadata(self, token_address: str) -> Dict:
        """Get token metadata (decimals, symbol, name)"""
        result = await self._request("alchemy_getTokenMetadata", [token_address])
        return result
    
    async def find_contract_deployments(self, address: str) -> List[Dict]:
        """Find contracts deployed by address"""
        result = await self._request("alchemy_findContractDeployments", [address])
        return result
    
    # ═══════════════════════════════════════════════════════════
    # DEBUG METHODS (Alchemy enhanced)
    # ═══════════════════════════════════════════════════════════
    
    async def debug_trace_call(self, tx: Dict, block: str = "latest", trace_type: List = None) -> Dict:
        """Debug trace a call"""
        if trace_type is None:
            trace_type = ["trace"]
        
        params = {
            "call": tx,
            "blockNumber": block,
            "traceType": trace_type
        }
        
        result = await self._request("debug_traceCall", [params])
        return result
    
    async def debug_trace_transaction(self, tx_hash: str, trace_type: List = None) -> Dict:
        """Debug trace a transaction"""
        if trace_type is None:
            trace_type = ["trace"]
        
        params = {
            "txHash": tx_hash,
            "traceType": trace_type
        }
        
        result = await self._request("debug_traceTransaction", [params])
        return result
    
    # ═══════════════════════════════════════════════════════════
    # TRANSACTION POOL (Alchemy enhanced)
    # ═══════════════════════════════════════════════════════════
    
    async def get_txpool_content(self) -> Dict:
        """Get transaction pool content"""
        result = await self._request("txpool_content")
        return result
    
    async def get_txpool_inspect(self) -> Dict:
        """Get transaction pool inspect"""
        result = await self._request("txpool_inspect")
        return result
    
    async def get_txpool_status(self) -> Dict:
        """Get transaction pool status"""
        result = await self._request("txpool_status")
        return result
    
    # ═══════════════════════════════════════════════════════════
    # WEBSOCKET SUBSCRIPTIONS
    # ═══════════════════════════════════════════════════════════
    
    async def subscribe(self, subscriptions: List[str]) -> str:
        """
        Subscribe to WebSocket events
        Types: newHeads, logs, pendingTransactions, alchemy_pendingTransactions
        """
        import aiohttp
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "alchemy_subscribe",
            "params": subscriptions
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(self.ws_url) as ws:
                await ws.send_json(payload)
                response = await ws.receive_json()
                return response.get("result")
    
    # ═══════════════════════════════════════════════════════════
    # PRICE FEEDS (Alchemy)
    # ═══════════════════════════════════════════════════════════
    
    async def get_asset_responses(self, addresses: List[str]) -> Dict:
        """Get price data for addresses (Alchemy)"""
        result = await self._request("alchemy_getAssetTransfers", [{
            "fromBlock": "0x0",
            "toBlock": "latest",
            "contractAddresses": addresses,
            "maxCount": "0x1"
        }])
        return result
    
    # ═══════════════════════════════════════════════════════════
    # BATCH REQUESTS
    # ═══════════════════════════════════════════════════════════
    
    async def batch_request(self, calls: List[Dict]) -> List[Any]:
        """
        Execute batch requests (Alchemy optimized)
        Much faster than individual calls
        """
        import aiohttp
        
        # Build batch payload
        payload = []
        for i, call in enumerate(calls):
            payload.append({
                "jsonrpc": "2.0",
                "method": call.get("method"),
                "params": call.get("params", []),
                "id": i
            })
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, json=payload) as resp:
                results = await resp.json()
                
                # Return in order
                return [r.get("result") for r in results]


# ═══════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════

def create_alchemy_from_env() -> AlchemyProvider:
    """Create Alchemy provider from environment variables"""
    api_key = os.getenv("ALCHEMY_API_KEY")
    network = os.getenv("ALCHEMY_NETWORK", "eth-mainnet")
    
    if not api_key:
        raise ValueError("ALCHEMY_API_KEY not set")
    
    config = AlchemyConfig(
        api_key=api_key,
        network=network,
        max_requests_per_second=int(os.getenv("ALCHEMY_MAX_RPS", "50"))
    )
    
    return AlchemyProvider(config)


def get_alchemy_url(network: str, api_key: str) -> str:
    """Get Alchemy URL for network"""
    base_urls = {
        "mainnet": "https://eth-mainnet.alchemyapi.io/v2",
        "sepolia": "https://eth-sepolia.alchemyapi.io/v2",
        "arbitrum": "https://arb-mainnet.g.alchemy.com/v2",
        "optimism": "https://opt-mainnet.g.alchemy.com/v2",
        "base": "https://base-mainnet.g.alchemy.com/v2",
        "polygon": "https://polygon-mainnet.g.alchemy.com/v2",
    }
    
    base = base_urls.get(network, base_urls["mainnet"])
    return f"{base}/{api_key}"


# Example usage
async def example():
    """Example Alchemy usage"""
    
    # From environment
    # export ALCHEMY_API_KEY=your_key
    # export ALCHEMY_NETWORK=eth-mainnet
    
    try:
        alchemy = create_alchemy_from_env()
    except ValueError:
        # Or provide directly
        config = AlchemyConfig(
            api_key="your_api_key",
            network="eth-mainnet"
        )
        alchemy = AlchemyProvider(config)
    
    # Get block number
    block = await alchemy.get_block_number()
    print(f"Current block: {block}")
    
    # Get gas price
    gas = await alchemy.get_gas_price()
    print(f"Gas price: {gas / 1e9:.2f} gwei")
    
    # Batch request example
    # results = await alchemy.batch_request([
    #     {"method": "eth_blockNumber", "params": []},
    #     {"method": "eth_gasPrice", "params": []},
    # ])


if __name__ == "__main__":
    asyncio.run(example())
