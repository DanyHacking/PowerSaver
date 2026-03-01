"""
Wallet Manager - Secure Fund Management
Handles ETH and token transfers to safe wallets
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from web3 import Web3
from web3.contract import Contract
import logging

logger = logging.getLogger(__name__)


@dataclass
class TokenBalance:
    symbol: str
    address: str
    balance: float
    decimals: int


class WalletManager:
    """
    Manages fund transfers between wallets
    Ensures profits go to safe cold wallet
    """
    
    # Common token addresses (mainnet)
    COMMON_TOKENS = {
        "ETH": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
    }
    
    def __init__(self, web3: Web3, private_key: str, safe_wallet: str):
        self.web3 = web3
        self.account = web3.eth.account.from_key(private_key)
        self.safe_wallet = safe_wallet
        
    async def get_eth_balance(self, address: str = None) -> float:
        """Get ETH balance"""
        addr = address or self.account.address
        balance_wei = self.web3.eth.get_balance(addr)
        return self.web3.from_wei(balance_wei, 'ether')
    
    async def get_token_balance(self, token_address: str, address: str = None) -> TokenBalance:
        """Get token balance"""
        addr = address or self.account.address
        
        token = self.web3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=self._get_erc20_abi()
        )
        
        try:
            balance_wei = token.functions.balanceOf(addr).call()
            decimals = token.functions.decimals().call()
            symbol = token.functions.symbol().call()
            
            return TokenBalance(
                symbol=symbol,
                address=token_address,
                balance=balance_wei / (10 ** decimals),
                decimals=decimals
            )
        except Exception as e:
            logger.error(f"Error getting token balance: {e}")
            return TokenBalance(symbol="UNKNOWN", address=token_address, balance=0, decimals=18)
    
    async def get_all_balances(self, address: str = None) -> Dict[str, TokenBalance]:
        """Get all token balances"""
        balances = {}
        
        eth_balance = await self.get_eth_balance(address)
        balances["ETH"] = TokenBalance(
            symbol="ETH",
            address="0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
            balance=eth_balance,
            decimals=18
        )
        
        for symbol, token_addr in self.COMMON_TOKENS.items():
            if symbol != "ETH":
                balances[symbol] = await self.get_token_balance(token_addr, address)
        
        return balances
    
    async def transfer_eth(self, to_address: str, amount_eth: float) -> str:
        """Transfer ETH to safe wallet"""
        to = Web3.to_checksum_address(to_address)
        amount_wei = self.web3.to_wei(amount_eth, 'ether')
        
        tx = {
            'from': self.account.address,
            'to': to,
            'value': amount_wei,
            'gas': 21000,
            'gasPrice': self.web3.eth.gas_price,
            'nonce': self.web3.eth.get_transaction_count(self.account.address),
            'chainId': 1
        }
        
        signed = self.account.sign_transaction(tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction)
        
        logger.info(f"✅ Transferred {amount_eth} ETH to {to}")
        return tx_hash.hex()
    
    async def transfer_token(self, token_address: str, to_address: str, amount: float) -> str:
        """Transfer tokens to safe wallet"""
        token = self.web3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=self._get_erc20_abi()
        )
        
        decimals = token.functions.decimals().call()
        amount_wei = int(amount * (10 ** decimals))
        
        to = Web3.to_checksum_address(to_address)
        
        tx = token.functions.transfer(to, amount_wei).build_transaction({
            'from': self.account.address,
            'gas': 100000,
            'gasPrice': self.web3.eth.gas_price,
            'nonce': self.web3.eth.get_transaction_count(self.account.address),
            'chainId': 1
        })
        
        signed = self.account.sign_transaction(tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction)
        
        symbol = token.functions.symbol().call()
        logger.info(f"✅ Transferred {amount} {symbol} to {to}")
        return tx_hash.hex()
    
    async def withdraw_profits(self, min_balance_eth: float = 0.1) -> Dict:
        """Withdraw profits to safe wallet when above threshold"""
        eth_balance = await self.get_eth_balance()
        
        if eth_balance < min_balance_eth:
            return {"status": "below_threshold", "balance": eth_balance}
        
        amount_to_withdraw = eth_balance - 0.01
        
        tx_hash = await self.transfer_eth(self.safe_wallet, amount_to_withdraw)
        
        return {
            "status": "success",
            "amount": amount_to_withdraw,
            "tx_hash": tx_hash,
            "safe_wallet": self.safe_wallet
        }
    
    def _get_erc20_abi(self) -> List:
        """Standard ERC20 ABI"""
        return [
            {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
            {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
            {"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
        ]
