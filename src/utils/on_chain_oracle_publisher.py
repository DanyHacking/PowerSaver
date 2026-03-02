"""
On-Chain Oracle Publisher
Publishes price data to blockchain (e.g., Chainlink, Uniswap, custom oracle contract)
"""

import asyncio
import logging
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time
import os

logger = logging.getLogger(__name__)


@dataclass
class OracleUpdate:
    """On-chain oracle price update"""
    token: str
    price: int  # Raw price (scaled)
    timestamp: int
    round_id: int


class OnChainOraclePublisher:
    """
    Publishes price data to blockchain
    
    Supports:
    - Chainlink OCR (Off-Chain Reporting)
    - Direct contract write
    - Uniswap price feed updates
    """
    
    def __init__(self, rpc_url: str, private_key: str = None):
        self.rpc_url = rpc_url
        self.private_key = private_key or os.getenv("ORACLE_PRIVATE_KEY")
        self.web3 = None
        
        # Oracle contract addresses (configure per network)
        self.CHAINLINK_ORACLE_CONTRACTS = {
            "mainnet": "0x...",  # Chainlink Oracle contract
            "sepolia": "0x...",
            "arbitrum": "0x...",
        }
        
        # Price feed contract addresses (Chainlink)
        self.PRICE_FEEDS = {
            "ETH": "0x5f4eC3Df9c8cB3b2e4c8c3E8b4F3D9b2c8E4f3D",
            "BTC": "0x9b4932a9C3cD7b5d4c6E8f2a4d9c3b5e8f2a4d9",
            "LINK": "0x...",
            "USDC": "0x8BAaF0cE8a8B3d4F2c9E8f2a4d9c3b5e8f2a4d9",
        }
        
        # Last published prices
        self._last_prices: Dict[str, OracleUpdate] = {}
        
        # Gas settings
        self.gas_limit = 200000
        self.gas_price_multiplier = 1.1
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize web3 connection"""
        if self._initialized:
            return
            
        try:
            from web3 import Web3
            from web3.eth import Account
            
            self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
            
            if not self.web3.is_connected():
                raise ConnectionError(f"Cannot connect to RPC: {self.rpc_url}")
            
            if self.private_key:
                self.account = Account.from_key(self.private_key)
                logger.info(f"Oracle publisher initialized with account: {self.account.address}")
            else:
                logger.warning("No private key - read-only mode")
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize oracle publisher: {e}")
            raise
    
    # ========== CHAINLINK PRICE FEED ==========
    
    async def update_chainlink_price(self, token: str, price: int) -> Optional[str]:
        """
        Update price on Chainlink Price Feed contract
        
        Args:
            token: Token symbol (ETH, BTC, etc.)
            price: Price in wei (scaled by 10^8)
        
        Returns:
            Transaction hash if successful
        """
        await self.initialize()
        
        if not self.account:
            logger.error("No private key configured - cannot send transaction")
            return None
        
        feed_address = self.PRICE_FEEDS.get(token.upper())
        if not feed_address:
            logger.error(f"No price feed for {token}")
            return None
        
        try:
            # Chainlink FeedProxy interface
            # function transmit(uint64[] memory _priceIds, int192[] memory _prices, bytes[] memory _ signatures) external
        
            # Simplified - using direct setter if you have custom oracle contract
            # For standard Chainlink, you'd need OCR setup
        
            # Example: Call custom oracle contract
            oracle_contract = self.web3.eth.contract(
                address=feed_address,
                abi=self._get_oracle_abi()
            )
            
            # Build transaction
            nonce = self.web3.eth.get_transaction_count(self.account.address)
            gas_price = int(self.web3.eth.gas_price * self.gas_price_multiplier)
            
            tx = oracle_contract.functions.updatePrice(
                price,
                int(time.time())
            ).build_transaction({
                "from": self.account.address,
                "nonce": nonce,
                "gas": self.gas_limit,
                "gasPrice": gas_price,
                "chainId": self.web3.eth.chain_id
            })
            
            # Sign and send
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt.status == 1:
                logger.info(f"Price updated on-chain: {token} = {price}")
                return tx_hash.hex()
            else:
                logger.error(f"Transaction failed: {receipt.transactionHash.hex()}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to update Chainlink price: {e}")
            return None
    
    # ========== UNISWAP PRICE FEED ==========
    
    async def update_uniswap_price(self, token_a: str, token_b: str, price: int) -> Optional[str]:
        """
        Update price via Uniswap v3 oracle
        
        Args:
            token_a: First token (e.g., ETH)
            token_b: Second token (e.g., USDC)
            price: TWAP price
        
        Returns:
            Transaction hash
        """
        await self.initialize()
        
        # Uniswap V3 pool oracle update
        # This requires writing to the oracle via pool contract
        
        pool_address = self._get_uniswap_pool(token_a, token_b)
        if not pool_address:
            return None
        
        try:
            pool_contract = self.web3.eth.contract(
                address=pool_address,
                abi=self._get_uniswap_pool_abi()
            )
            
            # Increase observation cardinality to enable oracle
            # This is usually done once per pool
            
            nonce = self.web3.eth.get_transaction_count(self.account.address)
            gas_price = int(self.web3.eth.gas_price * self.gas_price_multiplier)
            
            # Note: Uniswap V3 oracle is updated automatically on swaps
            # This would be for custom oracle contract integration
            
            logger.info(f"Uniswap pool: {pool_address}")
            return None  # Not typically needed as Uniswap updates on swaps
            
        except Exception as e:
            logger.error(f"Failed to update Uniswap oracle: {e}")
            return None
    
    # ========== CUSTOM ORACLE CONTRACT ==========
    
    async def publish_to_oracle_contract(
        self,
        contract_address: str,
        token: str,
        price: float,
        decimals: int = 8
    ) -> Optional[str]:
        """
        Publish price to custom oracle contract
        
        Args:
            contract_address: Oracle contract address
            token: Token symbol
            price: Price as float
            decimals: Price decimals (8 for Chainlink standard)
        
        Returns:
            Transaction hash
        """
        await self.initialize()
        
        if not self.account:
            logger.error("No private key configured")
            return None
        
        # Scale price to decimals
        price_scaled = int(price * (10 ** decimals))
        
        try:
            contract = self.web3.eth.contract(
                address=contract_address,
                abi=self._get_simple_oracle_abi()
            )
            
            nonce = self.web3.eth.get_transaction_count(self.account.address)
            gas_price = int(self.web3.eth.gas_price * self.gas_price_multiplier)
            
            # Call the oracle update function
            # Common names: updatePrice, setPrice, submitPrice, writePrice
            tx = contract.functions.updatePrice(
                self.web3.to_checksum_address(contract_address),
                price_scaled
            ).build_transaction({
                "from": self.account.address,
                "nonce": nonce,
                "gas": self.gas_limit,
                "gasPrice": gas_price,
                "chainId": self.web3.eth.chain_id
            })
            
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt.status == 1:
                logger.info(f"Published on-chain: {token} = {price} (tx: {tx_hash.hex()[:10]}...)")
                return tx_hash.hex()
            else:
                logger.error(f"Oracle update failed")
                return None
                
        except Exception as e:
            logger.error(f"Failed to publish to oracle contract: {e}")
            return None
    
    # ========== BATCH PUBLISH ==========
    
    async def batch_update(
        self,
        prices: Dict[str, float],
        decimals: int = 8
    ) -> Dict[str, str]:
        """
        Publish multiple prices in batch
        
        Args:
            prices: Dict of token -> price
            decimals: Price decimals
        
        Returns:
            Dict of token -> transaction hash
        """
        results = {}
        
        for token, price in prices.items():
            tx_hash = await self.publish_to_oracle_contract(
                contract_address=self.PRICE_FEEDS.get(token.upper()),
                token=token,
                price=price,
                decimals=decimals
            )
            results[token] = tx_hash
            
            # Rate limiting
            await asyncio.sleep(0.5)
        
        return results
    
    # ========== HELPERS ==========
    
    def _get_oracle_abi(self):
        """Chainlink Oracle ABI"""
        return [
            {
                "inputs": [
                    {"name": "price", "type": "int256"},
                    {"name": "timestamp", "type": "uint256"}
                ],
                "name": "updatePrice",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
    
    def _get_simple_oracle_abi(self):
        """Simple Oracle ABI"""
        return [
            {
                "inputs": [
                    {"name": "token", "type": "address"},
                    {"name": "price", "type": "uint256"}
                ],
                "name": "updatePrice",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
    
    def _get_uniswap_pool_abi(self):
        """Uniswap V3 Pool ABI"""
        return [
            {
                "inputs": [],
                "name": "slot0",
                "outputs": [
                    {"name": "sqrtPriceX96", "type": "uint160"},
                    {"name": "tick", "type": "int24"},
                    {"name": "observationIndex", "type": "uint16"},
                    {"name": "observationCardinality", "type": "uint16"},
                    {"name": "observationCardinalityNext", "type": "uint16"},
                    {"name": "feeProtocol", "type": "uint8"},
                    {"name": "unlocked", "type": "bool"}
                ],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    def _get_uniswap_pool(self, token_a: str, token_b: str) -> Optional[str]:
        """Get Uniswap V3 pool address"""
        # Common pool addresses
        pools = {
            ("ETH", "USDC"): "0x88e6A0c2dDD26EEb57e73461300EB8681aBb28e",
            ("WBTC", "ETH"): "0xCBCdF9626bC03E24f779434178A73a0B4bad62eD",
            ("USDC", "USDT"): "0x3041cbd36888becc7bbcbc0045e3b1f144466f5f",
        }
        return pools.get((token_a.upper(), token_b.upper()))


# ========== INTEGRATION WITH SIGNAL API ==========

class OraclePublisherAPI:
    """
    Combined API that:
    1. Receives signals/prices via HTTP
    2. Publishes them to blockchain
    """
    
    def __init__(self, rpc_url: str, private_key: str):
        self.publisher = OnChainOraclePublisher(rpc_url, private_key)
    
    async def handle_price_update(
        self,
        token: str,
        price: float,
        source: str = "manual",
        decimals: int = 8
    ) -> Dict:
        """
        Handle incoming price update - publish to blockchain
        
        Called when signal API receives a price
        """
        # Publish to blockchain
        tx_hash = await self.publisher.publish_to_oracle_contract(
            contract_address=self.publisher.PRICE_FEEDS.get(token.upper()),
            token=token,
            price=price,
            decimals=decimals
        )
        
        return {
            "success": tx_hash is not None,
            "token": token,
            "price": price,
            "tx_hash": tx_hash,
            "source": source
        }


# ========== EXAMPLE USAGE ==========

async def example():
    """Example: Receive signal and publish on-chain"""
    
    rpc_url = os.getenv("ETHEREUM_RPC_URL")
    private_key = os.getenv("ORACLE_PRIVATE_KEY")
    
    publisher = OnChainOraclePublisher(rpc_url, private_key)
    
    # Receive price from signal (e.g., 1850.50 ETH)
    # Then publish to blockchain:
    
    tx_hash = await publisher.publish_to_oracle_contract(
        contract_address="0x...",  # Your oracle contract
        token="ETH",
        price=1850.50,
        decimals=8  # Chainlink standard
    )
    
    if tx_hash:
        print(f"Price published on-chain: https://etherscan.io/tx/{tx_hash}")


if __name__ == "__main__":
    asyncio.run(example())
