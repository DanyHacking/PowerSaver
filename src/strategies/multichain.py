"""
Multi-Chain Support - BSC, Arbitrum, Optimism, Polygon
Less competition = more profit!
"""

from typing import Dict, List
from dataclasses import dataclass
from web3 import Web3
import asyncio


@dataclass
class ChainConfig:
    name: str
    chain_id: int
    rpc: str
    explorers: List[str]
    dexes: Dict[str, str]


class MultiChainArbitrage:
    """Arbitrage across multiple chains"""
    
    # Chain configurations
    CHAINS = {
        "ethereum": ChainConfig(
            name="Ethereum",
            chain_id=1,
            rpc="",
            explorers=["https://etherscan.io"],
            dexes={
                "uniswap_v2": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
                "uniswap_v3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "sushiswap": "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F",
            }
        ),
        "arbitrum": ChainConfig(
            name="Arbitrum One",
            chain_id=42161,
            rpc="",
            explorers=["https://arbiscan.io"],
            dexes={
                "uniswap_v3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "sushiswap": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
                "camelot": "0xc873fEcBd354F25A9CC2a8A0f543E9F8c64c3C05",
            }
        ),
        "optimism": ChainConfig(
            name="Optimism",
            chain_id=10,
            rpc="",
            explorers=["https://optimistic.etherscan.io"],
            dexes={
                "uniswap_v3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "sushiswap": "0x4B4445D5b723b1b73f72B2F9253D0eC4B8e42a2f",
                "velodrome": "0x3Ac6b2A24D5E08A67c2D66eD1A5E2B9c5c1Aa2b",
            }
        ),
        "polygon": ChainConfig(
            name="Polygon",
            chain_id=137,
            rpc="",
            explorers=["https://polygonscan.com"],
            dexes={
                "quickswap": "0xa5E0829CaCEd8fFDD4De3c43696c1767C07C0d4",
                "sushiswap": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
                "uniswap_v3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
            }
        ),
        "bsc": ChainConfig(
            name="BNB Smart Chain",
            chain_id=56,
            rpc="",
            explorers=["https://bscscan.com"],
            dexes={
                "pancakeswap": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
                "biswap": "0x3a6d15c0D1517E1a3D64f8b80f7E8C8d4c1EaC7",
                "apeswap": "0xcF0feBd3Fe17f8C1bf3C0E3b1b2E89A6c9b3e1C",
            }
        ),
    }
    
    def __init__(self, rpc_urls: Dict[str, str]):
        self.rpc_urls = rpc_urls
        self.web3_instances = {}
        
    def connect_chain(self, chain_name: str) -> Web3:
        """Connect to a specific chain"""
        if chain_name not in self.rpc_urls:
            raise ValueError(f"No RPC URL for {chain_name}")
        
        if chain_name not in self.web3_instances:
            self.web3_instances[chain_name] = Web3(Web3.HTTPProvider(self.rpc_urls[chain_name]))
        
        return self.web3_instances[chain_name]
    
    async def find_cross_chain_opportunities(self) -> List[Dict]:
        """Find arbitrage between chains"""
        opportunities = []
        
        # Compare ETH price across chains
        eth_prices = {}
        
        for chain_name, config in self.CHAINS.items():
            try:
                if chain_name in self.rpc_urls:
                    w3 = self.connect_chain(chain_name)
                    # Get ETH price on this chain
                    # Simplified - use USDC pair
                    price = await self._get_eth_price(w3, config)
                    if price:
                        eth_prices[chain_name] = price
            except Exception as e:
                continue
        
        # Find price differences
        if len(eth_prices) >= 2:
            prices = list(eth_prices.values())
            min_price = min(prices)
            max_price = max(prices)
            
            if max_price - min_price > 10:  # > $10 difference
                for chain, price in eth_prices.items():
                    if price == min_price:
                        opportunities.append({
                            "type": "cross_chain",
                            "buy_chain": chain,
                            "sell_chain": [c for c, p in eth_prices.items() if p == max_price][0],
                            "profit_estimate": max_price - min_price,
                            "token": "ETH"
                        })
        
        return opportunities
    
    async def _get_eth_price(self, web3: Web3, config: ChainConfig) -> float:
        """Get ETH price on a chain (simplified)"""
        # In production: query actual DEX pairs
        # Return placeholder
        return 0
    
    def get_available_chains(self) -> List[str]:
        """Get list of chains with RPC configured"""
        return list(self.rpc_urls.keys())
