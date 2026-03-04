"""
Aave V3 Flashloan Executor
Handles flashloan transactions on Ethereum mainnet
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from eth_abi import encode
from web3 import Web3

logger = logging.getLogger(__name__)


# Aave V3 Contract Addresses (Ethereum Mainnet)
AAVE_V3_POOL = "0x87870Bca3F3fD6335C3F4ce6260135144110A857"
AAVE_ADDRESSES_PROVIDER = "0x2f39d218133AFaB8F2B819B1066c7E434Ad116E"

# Token Addresses (Ethereum Mainnet)
TOKENS = {
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "DAI": "0x6B175474E89094C44Da98b954EedeCc1361d7c17a",
    "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
}

# Uniswap V2 Router
UNISWAP_V2_ROUTER = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
UNISWAP_V2_FACTORY = "0x5C69bEe701ef814a2B6fe3cF77eE1eD5e2b3f2c4"


@dataclass
class FlashLoanResult:
    success: bool
    transaction_hash: str
    profit: float
    gas_used: int
    error: Optional[str] = None


class AaveV3FlashLoanExecutor:
    """
    Executes flashloans via Aave V3 for arbitrage trading
    """
    
    def __init__(self, web3: Web3, private_key: str, contract_address: str = None):
        self.web3 = web3
        self.account = web3.eth.account.from_key(private_key)
        self.contract_address = contract_address
        self.address = self.account.address
        
        # Aave V3 Pool ABI (simplified for flashloan)
        self.pool_abi = [
            {
                "inputs": [
                    {"name": "receiverAddress", "type": "address"},
                    {"name": "assets", "type": "address[]"},
                    {"name": "amounts", "type": "uint256[]"},
                    {"name": "modes", "type": "uint256[]"},
                    {"name": "onBehalfOf", "type": "address"},
                    {"name": "params", "type": "bytes"},
                    {"name": "referralCode", "type": "uint16"}
                ],
                "name": "flashLoan",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
        
        # ERC20 ABI for token approvals
        self.erc20_abi = [
            {
                "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
                "name": "approve",
                "outputs": [{"name": "", "type": "bool"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"name": "account", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        self.pool_contract = web3.eth.contract(address=AAVE_V3_POOL, abi=self.pool_abi)
        
    def get_token_contract(self, token_address: str):
        """Get ERC20 token contract"""
        return self.web3.eth.contract(address=token_address, abi=self.erc20_abi)
    
    async def execute_flashloan_arbitrage(
        self,
        token_in: str,
        token_out: str,
        amount: int,
        path: List[str] = None
    ) -> FlashLoanResult:
        """
        Execute flashloan arbitrage
        
        Args:
            token_in: Input token symbol (e.g., "USDC", "WETH")
            token_out: Output token symbol
            amount: Amount to borrow (in wei)
            path: Swap path (optional)
            
        Returns:
            FlashLoanResult with transaction details
        """
        try:
            # Get token addresses
            token_in_addr = TOKENS.get(token_in.upper())
            token_out_addr = TOKENS.get(token_out.upper())
            
            if not token_in_addr or not token_out_addr:
                return FlashLoanResult(
                    success=False,
                    transaction_hash="",
                    profit=0,
                    gas_used=0,
                    error=f"Unknown token: {token_in} or {token_out}"
                )
            
            logger.info(f"Executing flashloan: {amount} {token_in} -> {token_out}")
            
            # Build flashloan transaction
            assets = [token_in_addr]
            amounts = [amount]
            modes = [0]  # 0 = repay debt
            on_behalf_of = self.address
            referral_code = 0
            
            # Encode params for callback
            # In production, this would include the swap data
            params = b""  # Simplified for demo
            
            # Build transaction
            nonce = self.web3.eth.get_transaction_count(self.address)
            gas_price = self.web3.eth.gas_price
            
            tx = self.pool_contract.functions.flashLoan(
                self.address,  # receiver
                assets,
                amounts,
                modes,
                on_behalf_of,
                params,
                referral_code
            ).build_transaction({
                'from': self.address,
                'nonce': nonce,
                'gasPrice': gas_price,
                'chainId': 1  # Ethereum Mainnet
            })
            
            # Estimate gas
            try:
                gas_estimate = self.web3.eth.estimate_gas(tx)
                tx['gas'] = int(gas_estimate * 1.2)  # Add 20% buffer
            except Exception as e:
                logger.warning(f"Gas estimation failed: {e}, using default gas")
                tx['gas'] = 500000
            
            # Sign transaction
            signed_tx = self.account.sign_transaction(tx)
            
            # Send transaction
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            logger.info(f"Flashloan transaction sent: {tx_hash.hex()}")
            
            # Wait for receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                logger.info(f"Flashloan executed successfully! Gas used: {receipt['gasUsed']}")
                return FlashLoanResult(
                    success=True,
                    transaction_hash=tx_hash.hex(),
                    profit=0,  # Would calculate actual profit in callback
                    gas_used=receipt['gasUsed']
                )
            else:
                return FlashLoanResult(
                    success=False,
                    transaction_hash=tx_hash.hex(),
                    profit=0,
                    gas_used=receipt['gasUsed'],
                    error="Transaction failed"
                )
                
        except Exception as e:
            logger.error(f"Flashloan execution failed: {e}")
            return FlashLoanResult(
                success=False,
                transaction_hash="",
                profit=0,
                gas_used=0,
                error=str(e)
            )
    
    async def get_flashloan_quote(self, token: str, amount: int) -> Dict:
        """
        Get flashloan fee quote
        
        Aave V3 flashloan fee: 0.05% (0.0005)
        """
        token_addr = TOKENS.get(token.upper())
        if not token_addr:
            return {"error": f"Unknown token: {token}"}
        
        # Aave V3 flashloan fee is 0.05%
        fee = int(amount * 0.0005)
        
        return {
            "token": token,
            "amount": amount,
            "fee": fee,
            "fee_percentage": 0.05,
            "repay_amount": amount + fee
        }
    
    def get_token_balance(self, token: str) -> int:
        """Get token balance of the contract"""
        token_addr = TOKENS.get(token.upper())
        if not token_addr:
            return 0
        
        contract = self.get_token_contract(token_addr)
        return contract.functions.balanceOf(self.address).call()


async def create_flashloan_executor(
    rpc_url: str,
    private_key: str,
    contract_address: str = None
) -> Optional[AaveV3FlashLoanExecutor]:
    """
    Create and initialize flashloan executor
    """
    try:
        web3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if not web3.is_connected():
            logger.error(f"Failed to connect to RPC: {rpc_url}")
            return None
        
        # Validate private key
        try:
            account = web3.eth.account.from_key(private_key)
            logger.info(f"Flashloan executor initialized for: {account.address}")
        except Exception as e:
            logger.error(f"Invalid private key: {e}")
            return None
        
        return AaveV3FlashLoanExecutor(web3, private_key, contract_address)
        
    except Exception as e:
        logger.error(f"Failed to create flashloan executor: {e}")
        return None


# Example usage
if __name__ == "__main__":
    import os
    
    RPC_URL = os.getenv("ETHEREUM_RPC_URL", "https://ethereum-rpc.publicnode.com")
    PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
    
    async def main():
        if not PRIVATE_KEY:
            print("PRIVATE_KEY not set")
            return
        
        executor = await create_flashloan_executor(RPC_URL, PRIVATE_KEY)
        if executor:
            # Get quote for 10000 USDC flashloan
            quote = await executor.get_flashloan_quote("USDC", 10000 * 10**6)
            print(f"Flashloan quote: {quote}")
            
            # Check balance
            balance = executor.get_token_balance("USDC")
            print(f"USDC balance: {balance}")
    
    asyncio.run(main())
