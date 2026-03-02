"""
Advanced Arbitrage Engine
Multi-path, triangular, and cross-exchange arbitrage detection
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import heapq

logger = logging.getLogger(__name__)


@dataclass
class DEXPrice:
    """Price quote from a DEX"""
    dex: str
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    price: float  # token_out per token_in
    liquidity: float
    gas_cost: float


@dataclass
class ArbitragePath:
    """Complete arbitrage path"""
    path: List[str]  # token addresses
    exchanges: List[str]  # DEX names
    input_amount: float
    expected_output: float
    profit: float
    gas_cost: float
    net_profit: float
    confidence: float
    execution_time_ms: float


class AdvancedArbitrageDetector:
    """
    Advanced arbitrage detection with:
    - Multi-hop paths
    - Triangular arbitrage
    - Cross-DEX opportunities
    - Real-time price aggregation
    """
    
    # DEX Router addresses
    ROUTERS = {
        # Ethereum
        "uniswap_v3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
        "uniswap_v2": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
        "sushiswap": "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F",
        "curve": "0x8F16D6246D52f8Ea5A3A1C84aBb4D8D13d8d82D2",
        "balancer": "0xBA12222222228d8Ba445958a75a0704d566BF2C",
    }
    
    # Common tokens
    TOKENS = {
        "ETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
        "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
        "AAVE": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
    }
    
    def __init__(self, web3=None, rpc_urls: Dict[str, str] = None):
        self.web3 = web3
        self.rpc_urls = rpc_urls or {}
        
        # Price cache
        self.price_cache: Dict[str, List[DEXPrice]] = {}
        self.cache_ttl = 5  # seconds
        
        # Known paths for fast scanning
        self.common_paths = [
            # Stablecoin triangles
            ["USDC", "USDT", "USDC"],
            ["USDC", "DAI", "USDC"],
            ["USDT", "DAI", "USDT"],
            # ETH pairs
            ["ETH", "USDC", "ETH"],
            ["ETH", "USDT", "ETH"],
            ["ETH", "DAI", "ETH"],
            ["ETH", "WBTC", "ETH"],
            # Alt pairs
            ["WBTC", "ETH", "WBTC"],
            ["ETH", "LINK", "ETH"],
            ["ETH", "UNI", "ETH"],
            ["ETH", "AAVE", "ETH"],
        ]
        
        # Gas cost estimates per DEX
        self.gas_costs = {
            "uniswap_v3": 150000,
            "uniswap_v2": 200000,
            "sushiswap": 220000,
            "curve": 180000,
            "balancer": 200000,
        }
    
    async def find_all_opportunities(
        self, 
        min_profit: float = 10,
        max_paths: int = 20
    ) -> List[ArbitragePath]:
        """
        Find all arbitrage opportunities across DEXes
        Returns top opportunities sorted by net profit
        """
        opportunities = []
        
        # Step 1: Fetch prices from all DEXes
        all_prices = await self._fetch_all_prices()
        
        if not all_prices:
            return opportunities
        
        # Step 2: Find triangular arbitrage
        triangular = await self._find_triangular_arbitrage(all_prices, min_profit)
        opportunities.extend(triangular)
        
        # Step 3: Find cross-DEX arbitrage
        cross_dex = await self._find_cross_dex_arbitrage(all_prices, min_profit)
        opportunities.extend(cross_dex)
        
        # Step 4: Find multi-hop paths
        multi_hop = await self._find_multihop_arbitrage(all_prices, min_profit)
        opportunities.extend(multi_hop)
        
        # Sort by net profit and return top opportunities
        opportunities.sort(key=lambda x: x.net_profit, reverse=True)
        
        return opportunities[:max_paths]
    
    async def _fetch_all_prices(self) -> Dict[str, List[DEXPrice]]:
        """Fetch prices from all configured DEXes"""
        prices = defaultdict(list)
        
        # In production, this would query:
        # 1. DEX APIs/subgraphs
        # 2. On-chain data from routers
        # 3. Aggregator APIs (0x, 1inch)
        
        # For now, return empty - would need RPC connection
        return prices
    
    async def _find_triangular_arbitrage(
        self, 
        prices: Dict[str, List[DEXPrice]],
        min_profit: float
    ) -> List[ArbitragePath]:
        """Find triangular arbitrage opportunities"""
        opportunities = []
        
        for path in self.common_paths:
            try:
                result = await self._calculate_triangular_path(
                    path[0], path[1], path[2],
                    10000,  # Input amount
                    prices
                )
                
                if result and result.net_profit >= min_profit:
                    opportunities.append(result)
                    
            except Exception as e:
                logger.debug(f"Triangular path failed: {e}")
        
        return opportunities
    
    async def _calculate_triangular_path(
        self,
        token_a: str,
        token_b: str,
        token_c: str,
        amount: float,
        prices: Dict[str, List[DEXPrice]]
    ) -> Optional[ArbitragePath]:
        """Calculate profit for triangular path: A -> B -> C -> A"""
        
        # Get prices for each leg
        ab_price = await self._get_best_price(token_a, token_b, prices)
        bc_price = await self._get_best_price(token_b, token_c, prices)
        ca_price = await self._get_best_price(token_c, token_a, prices)
        
        if not all([ab_price, bc_price, ca_price]):
            return None
        
        # Calculate output
        leg1 = amount * ab_price.price
        leg2 = leg1 * bc_price.price
        leg3 = leg2 * ca_price.price
        
        expected_output = leg3
        profit = expected_output - amount
        
        # Calculate gas cost
        gas_cost = sum([
            self.gas_costs.get(ab_price.dex, 150000),
            self.gas_costs.get(bc_price.dex, 150000),
            self.gas_costs.get(ca_price.dex, 150000)
        ])
        
        # Estimate gas in USD (assume 30 gwei, ETH $1800)
        gas_cost_usd = (gas_cost * 30e9 / 1e18) * 1800
        
        net_profit = profit - gas_cost_usd
        
        # Confidence based on liquidity
        min_liquidity = min(
            ab_price.liquidity, 
            bc_price.liquidity, 
            ca_price.liquidity
        )
        confidence = min(min_liquidity / 100000, 1.0)
        
        return ArbitragePath(
            path=[self.TOKENS[token_a], self.TOKENS[token_b], self.TOKENS[token_c]],
            exchanges=[ab_price.dex, bc_price.dex, ca_price.dex],
            input_amount=amount,
            expected_output=expected_output,
            profit=profit,
            gas_cost=gas_cost_usd,
            net_profit=net_profit,
            confidence=confidence,
            execution_time_ms=3000  # Estimated
        )
    
    async def _get_best_price(
        self,
        token_in: str,
        token_out: str,
        prices: Dict[str, List[DEXPrice]]
    ) -> Optional[DEXPrice]:
        """Get best price for token pair from cache"""
        key = f"{token_in}_{token_out}"
        
        # In production, use actual fetched prices
        # For now, return None as we'd need RPC
        return None
    
    async def _find_cross_dex_arbitrage(
        self,
        prices: Dict[str, List[DEXPrice]],
        min_profit: float
    ) -> List[ArbitragePath]:
        """Find cross-DEX arbitrage (buy low, sell high)"""
        opportunities = []
        
        # Check all token pairs
        for token_in in self.TOKENS:
            for token_out in self.TOKENS:
                if token_in == token_out:
                    continue
                
                # Find best buy and sell prices
                buy_prices = prices.get(f"{token_in}_{token_out}", [])
                sell_prices = prices.get(f"{token_out}_{token_in}", [])
                
                if not buy_prices or not sell_prices:
                    continue
                
                best_buy = min(buy_prices, key=lambda x: x.price)
                best_sell = max(sell_prices, key=lambda x: x.price)
                
                # Calculate profit
                if best_sell.price > best_buy.price:
                    amount = 10000  # Standard amount
                    profit = amount * (1 / best_buy.price - best_sell.price / 1)
                    
                    if profit >= min_profit:
                        opportunities.append(ArbitragePath(
                            path=[self.TOKENS[token_in], self.TOKENS[token_out]],
                            exchanges=[best_buy.dex, best_sell.dex],
                            input_amount=amount,
                            expected_output=amount + profit,
                            profit=profit,
                            gas_cost=50,  # Approximate
                            net_profit=profit - 50,
                            confidence=min(best_buy.liquidity / 100000, 1.0),
                            execution_time_ms=1000
                        ))
        
        return opportunities
    
    async def _find_multihop_arbitrage(
        self,
        prices: Dict[str, List[DEXPrice]],
        min_profit: float
    ) -> List[ArbitragePath]:
        """Find multi-hop arbitrage opportunities"""
        opportunities = []
        
        # Check longer paths (4+ tokens)
        for token in self.TOKENS:
            path = [token, "USDC", "USDT", token]
            try:
                result = await self._calculate_triangular_path(
                    path[0], path[1], path[2], 10000, prices
                )
                if result and result.net_profit >= min_profit:
                    opportunities.append(result)
            except:
                continue
        
        return opportunities
    
    async def execute_arbitrage(
        self,
        path: ArbitragePath,
        private_key: str
    ) -> Dict:
        """Execute arbitrage trade"""
        try:
            # In production:
            # 1. Get flash loan
            # 2. Execute all swaps in sequence
            # 3. Repay flash loan
            # 4. Keep profit
            
            return {
                "status": "ready_to_execute",
                "path": path.path,
                "exchanges": path.exchanges,
                "input_amount": path.input_amount,
                "expected_profit": path.net_profit,
                "gas_cost": path.gas_cost
            }
            
        except Exception as e:
            logger.error(f"Arbitrage execution failed: {e}")
            return {"status": "failed", "error": str(e)}


class FlashLoanExecutor:
    """
    Flash loan execution for arbitrage
    """
    
    # Aave V3 Flash Loan addresses
    AAVE_V3_POOL = "0x87870Bca3F3fD6335C3F4ce6260135144110A857"
    
    def __init__(self, web3, private_key: str):
        self.web3 = web3
        self.account = web3.eth.account.from_key(private_key)
    
    async def get_flash_loan(
        self,
        token: str,
        amount: float
    ) -> Dict:
        """
        Get flash loan from Aave
        """
        # In production, this would:
        # 1. Encode the flash loan calldata
        # 2. Execute the flash loan via Aave pool
        # 3. Execute arbitrage in the callback
        # 4. Repay the flash loan
        
        return {
            "status": "not_implemented",
            "token": token,
            "amount": amount,
            "fee": amount * 0.0009  # Aave flash loan fee
        }
    
    def build_flash_loan_tx(
        self,
        tokens: List[str],
        amounts: List[int],
        data: bytes
    ) -> Dict:
        """Build flash loan transaction"""
        
        # Aave V3 flash loan function
        # flashLoan(address receiverAddress, address[] calldata assets, uint256[] calldata amounts, uint256[] calldata modes, address onBehalfOf, bytes calldata params, uint16 referralCode)
        
        return {
            "to": self.AAVE_V3_POOL,
            "data": "0x",  # Would be encoded function call
            "value": 0
        }


# Factory
def create_arbitrage_detector(web3=None, rpc_urls: Dict[str, str] = None) -> AdvancedArbitrageDetector:
    """Create advanced arbitrage detector"""
    return AdvancedArbitrageDetector(web3, rpc_urls)
