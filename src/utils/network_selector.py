"""
Network Selector - Switch between mainnet and testnet
"""

import os
import json
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class NetworkConfig:
    """Network configuration"""
    name: str
    chain_id: int
    rpc_url: str
    explorer: str
    tokens: list
    exchanges: list
    contracts: dict


class NetworkSelector:
    """Select and manage network configurations"""
    
    def __init__(self, config_file: str = "config_networks.json"):
        self.config_file = config_file
        self.configs = self._load_configs()
        
        # Check environment
        self.testnet = os.getenv("TESTNET", "").lower() == "true"
        self.network = self._get_network()
    
    def _load_configs(self) -> Dict:
        """Load network configurations"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"mainnet": {}, "testnet": {}}
    
    def _get_network(self) -> str:
        """Determine which network to use"""
        if self.testnet:
            return "testnet"
        return "mainnet"
    
    def get_config(self) -> NetworkConfig:
        """Get current network configuration"""
        network_data = self.configs.get(self.network, {})
        
        return NetworkConfig(
            name=self.network,
            chain_id=network_data.get("chain_id", 1 if self.network == "mainnet" else 11155111),
            rpc_url=network_data.get("rpc_url", "http://localhost:8545"),
            explorer=network_data.get("explorer", "https://etherscan.io"),
            tokens=network_data.get("tokens", []),
            exchanges=network_data.get("exchanges", []),
            contracts=network_data.get("contracts", {})
        )
    
    def is_testnet(self) -> bool:
        """Check if running on testnet"""
        return self.testnet
    
    def is_mainnet(self) -> bool:
        """Check if running on mainnet"""
        return not self.testnet
    
    def get_rpc_url(self) -> str:
        """Get RPC URL for current network"""
        # Priority: env var > config file
        if self.testnet:
            return os.getenv("SEPOLIA_RPC_URL", self.get_config().rpc_url)
        else:
            return os.getenv("ETHEREUM_RPC_URL", self.get_config().rpc_url)
    
    def get_explorer_url(self, tx_hash: str = None, address: str = None) -> str:
        """Get explorer URL"""
        base = self.get_config().explorer
        
        if tx_hash:
            return f"{base}/tx/{tx_hash}"
        elif address:
            return f"{base}/address/{address}"
        return base
    
    def switch_to_mainnet(self):
        """Switch to mainnet"""
        self.testnet = False
        self.network = "mainnet"
    
    def switch_to_testnet(self):
        """Switch to testnet"""
        self.testnet = True
        self.network = "testnet"


# Factory function
def get_network(rpc_url: str = None, testnet: bool = False) -> NetworkConfig:
    """Get network configuration"""
    if testnet:
        os.environ["TESTNET"] = "true"
    
    if rpc_url:
        os.environ["ETHEREUM_RPC_URL"] = rpc_url
    
    selector = NetworkSelector()
    return selector.get_config()


# Decorator for network-aware functions
def requires_network(network: str):
    """Decorator to ensure correct network"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            selector = NetworkSelector()
            if network == "mainnet" and not selector.is_mainnet():
                raise RuntimeError("This function requires mainnet")
            if network == "testnet" and not selector.is_testnet():
                raise RuntimeError("This function requires testnet")
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Example usage
if __name__ == "__main__":
    import sys
    
    # Default to mainnet
    selector = NetworkSelector()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--testnet":
            selector.switch_to_testnet()
        elif sys.argv[1] == "--mainnet":
            selector.switch_to_mainnet()
    
    config = selector.get_config()
    
    print(f"""
╔═══════════════════════════════════════════╗
║         NETWORK CONFIGURATION              ║
╠═══════════════════════════════════════════╣
║  Network:    {config.name:^30}║
║  Chain ID:   {config.chain_id:^30}║
║  RPC:        {config.rpc_url[:30]:^30}║
║  Explorer:   {config.explorer[:30]:^30}║
║  Tokens:     {len(config.tokens):^30}║
║  Exchanges:  {len(config.exchanges):^30}║
╚═══════════════════════════════════════════╝
    """)
