"""
Blockchain Data Sources Module
Provides real-time blockchain data for trading system
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import time

import aiohttp
from web3 import Web3

logger = logging.getLogger(__name__)


@dataclass
class TokenPrice:
    """Token price data"""
    token: str
    price_usd: float
    timestamp: float
    source: str
    confidence: float


@dataclass
class GasPrice:
    """Gas price data"""
    gas_price_gwei: float
    timestamp: float
    network: str


@dataclass
class PoolReserves:
    """Liquidity pool reserves"""
    token0: str
    token1: str
    reserve0: float
    reserve1: float
    exchange: str


class CoinGeckoPriceOracle:
    """
    CoinGecko API price oracle
    Free tier: 10-30 calls/minute
    """
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    # Token addresses to CoinGecko IDs
    TOKEN_IDS = {
        "ETH": "ethereum",
        "WBTC": "wrapped-bitcoin",
        "USDC": "usd-coin",
        "DAI": "dai",
        "USDT": "tether",
        "WETH": "weth",
        "MATIC": "matic-network",
        "LINK": "chainlink",
    }
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.price_cache: Dict[str, Tuple[float, float]] = {}  # (price, timestamp)
        self.cache_ttl = 30  # 30 seconds cache
    
    async def get_token_price(self, token: str) -> Optional[TokenPrice]:
        """Get current token price from CoinGecko"""
        token_id = self.TOKEN_IDS.get(token)
        if not token_id:
            logger.warning(f"Unknown token: {token}")
            return None
        
        # Check cache
        cache_key = token
        if cache_key in self.price_cache:
            price, timestamp = self.price_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return TokenPrice(
                    token=token,
                    price_usd=price,
                    timestamp=timestamp,
                    source="coingecko_cache",
                    confidence=1.0
                )
        
        # Fetch from API
        url = f"{self.BASE_URL}/simple/price"
        params = {
            "ids": token_id,
            "vs_currencies": "usd"
        }
        
        if self.api_key:
            params["x_cg_demo_api_key"] = self.api_key
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = data[token_id]["usd"]
                        timestamp = time.time()
                        
                        self.price_cache[cache_key] = (price, timestamp)
                        
                        return TokenPrice(
                            token=token,
                            price_usd=price,
                            timestamp=timestamp,
                            source="coingecko",
                            confidence=0.95
                        )
                    else:
                        logger.error(f"CoinGecko API error: {response.status}")
        except Exception as e:
            logger.error(f"Failed to fetch price from CoinGecko: {e}")
        
        return None
    
    async def get_token_prices(self, tokens: List[str]) -> Dict[str, TokenPrice]:
        """Get prices for multiple tokens"""
        prices = {}
        for token in tokens:
            price = await self.get_token_price(token)
            if price:
                prices[token] = price
            await asyncio.sleep(0.5)  # Rate limiting
        return prices


class EtherscanGasOracle:
    """
    Etherscan gas price oracle
    """
    
    BASE_URL = "https://api.etherscan.io/api"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or "YourApiKeyToken"
        self.gas_cache: Tuple[float, float] = (0, 0)
        self.cache_ttl = 15  # 15 seconds
    
    async def get_gas_price(self) -> Optional[GasPrice]:
        """Get current gas price from Etherscan"""
        # Check cache
        if time.time() - self.gas_cache[1] < self.cache_ttl:
            return GasPrice(
                gas_price_gwei=self.gas_cache[0],
                timestamp=self.gas_cache[1],
                network="ethereum"
            )
        
        url = self.BASE_URL
        params = {
            "module": "gastracker",
            "action": "gasoracle",
            "apikey": self.api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data["status"] == "1":
                            gas_price = float(data["result"]["ProposeGasPrice"])
                            timestamp = time.time()
                            
                            self.gas_cache = (gas_price, timestamp)
                            
                            return GasPrice(
                                gas_price_gwei=gas_price,
                                timestamp=timestamp,
                                network="ethereum"
                            )
        except Exception as e:
            logger.error(f"Failed to fetch gas price: {e}")
        
        return None


class UniswapV2DataProvider:
    """
    Uniswap V2 data provider
    """
    
    def __init__(self, rpc_url: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.factory_abi = [
            {
                "inputs": [{"name": "tokenA", "type": "address"}, {"name": "tokenB", "type": "address"}],
                "name": "getPair",
                "outputs": [{"name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        self.pair_abi = [
            {
                "inputs": [],
                "name": "getReserves",
                "outputs": [{"name": "reserve0", "type": "uint112"}, {"name": "reserve1", "type": "uint112"}, {"name": "blockTimestampLast", "type": "uint32"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        self.factory_address = "0x5C69bEe701ef814a2B6ce3c27052E1803338CD17"
    
    def get_pair_address(self, token0: str, token1: str) -> Optional[str]:
        """Get Uniswap V2 pair address"""
        try:
            factory = self.w3.eth.contract(
                address=self.factory_address,
                abi=self.factory_abi
            )
            pair = factory.functions.getPair(token0, token1).call()
            return pair if pair != "0x0000000000000000000000000000000000000000" else None
        except Exception as e:
            logger.error(f"Failed to get pair address: {e}")
            return None
    
    def get_pool_reserves(self, pair_address: str) -> Optional[PoolReserves]:
        """Get pool reserves for a pair"""
        try:
            pair = self.w3.eth.contract(
                address=pair_address,
                abi=self.pair_abi
            )
            reserves = pair.functions.getReserves().call()
            
            return PoolReserves(
                token0="",
                token1="",
                reserve0=reserves[0],
                reserve1=reserves[1],
                exchange="uniswap_v2"
            )
        except Exception as e:
            logger.error(f"Failed to get reserves: {e}")
            return None


class BlockchainDataAggregator:
    """
    Aggregates data from multiple blockchain sources
    """
    
    def __init__(self, rpc_url: str, etherscan_api_key: str = None, coingecko_api_key: str = None):
        self.rpc_url = rpc_url
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        self.price_oracle = CoinGeckoPriceOracle(coingecko_api_key)
        self.gas_oracle = EtherscanGasOracle(etherscan_api_key)
        self.uniswap = UniswapV2DataProvider(rpc_url)
    
    async def get_token_price(self, token: str) -> Optional[TokenPrice]:
        """Get token price from available sources"""
        # Try CoinGecko first
        price = await self.price_oracle.get_token_price(token)
        if price:
            return price
        
        # Fallback: estimate from ETH price
        if token != "ETH":
            eth_price = await self.price_oracle.get_token_price("ETH")
            if eth_price:
                # Rough estimate based on typical ratios
                ratios = {
                    "WBTC": 0.05,  # BTC/ETH ratio approximation
                    "USDC": 0.0005,
                    "DAI": 0.0005
                }
                ratio = ratios.get(token, 0.001)
                return TokenPrice(
                    token=token,
                    price_usd=eth_price.price_usd * ratio,
                    timestamp=time.time(),
                    source="estimated",
                    confidence=0.5
                )
        
        return None
    
    async def get_gas_price(self) -> Optional[GasPrice]:
        """Get current gas price"""
        gas = await self.gas_oracle.get_gas_price()
        if gas:
            return gas
        
        # Fallback: use web3 default
        try:
            gas_price = self.w3.eth.gas_price
            return GasPrice(
                gas_price_gwei=gas_price / 1e9,
                timestamp=time.time(),
                network="ethereum"
            )
        except Exception as e:
            logger.error(f"Failed to get gas price: {e}")
            return None
    
    async def get_market_data(self, tokens: List[str]) -> Dict:
        """Get comprehensive market data"""
        market_data = {
            "prices": {},
            "gas_price": None,
            "timestamp": time.time()
        }
        
        # Get prices
        for token in tokens:
            price = await self.get_token_price(token)
            if price:
                market_data["prices"][token] = price
        
        # Get gas price
        market_data["gas_price"] = await self.get_gas_price()
        
        return market_data
    
    def is_connected(self) -> bool:
        """Check if connected to blockchain"""
        return self.w3.is_connected()
    
    def get_block_number(self) -> int:
        """Get current block number"""
        return self.w3.eth.block_number


class RealTimeDataManager:
    """
    Manages real-time data updates for the trading system
    """
    
    def __init__(self, data_aggregator: BlockchainDataAggregator, update_interval: int = 5):
        self.data_aggregator = data_aggregator
        self.update_interval = update_interval
        self.is_running = False
        self.latest_data = {}
        self._task = None
    
    async def start(self):
        """Start data updates"""
        self.is_running = True
        self._task = asyncio.create_task(self._update_loop())
        logger.info("Real-time data manager started")
    
    async def stop(self):
        """Stop data updates"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Real-time data manager stopped")
    
    async def _update_loop(self):
        """Main update loop"""
        while self.is_running:
            try:
                tokens = ["ETH", "USDC", "DAI", "WBTC"]
                self.latest_data = await self.data_aggregator.get_market_data(tokens)
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Data update error: {e}")
                await asyncio.sleep(5)
    
    def get_latest_prices(self) -> Dict[str, float]:
        """Get latest prices"""
        return {
            token: data.price_usd 
            for token, data in self.latest_data.get("prices", {}).items()
        }
    
    def get_latest_gas(self) -> Optional[float]:
        """Get latest gas price"""
        if self.latest_data.get("gas_price"):
            return self.latest_data["gas_price"].gas_price_gwei
        return None


# Factory function
def create_blockchain_data_manager(
    rpc_url: str,
    etherscan_api_key: str = None,
    coingecko_api_key: str = None
) -> BlockchainDataAggregator:
    """Create blockchain data manager"""
    return BlockchainDataAggregator(rpc_url, etherscan_api_key, coingecko_api_key)
