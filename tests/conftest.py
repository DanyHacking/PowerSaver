"""
Production Test Configuration
For mainnet autonomous trading system verification
"""
import pytest
import os
import json
from pathlib import Path
from web3 import Web3

# Handle web3 middleware import based on version
try:
    from web3.middleware import geth_poa_middleware
except ImportError:
    geth_middleware = None


@pytest.fixture(scope="session")
def rpc_url():
    """Production RPC URL"""
    return os.getenv("ETHEREUM_RPC_URL", "https://mainnet.infura.io/v3/YOUR_KEY")


@pytest.fixture(scope="session")
def w3(rpc_url):
    """Web3 instance for production"""
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if geth_middleware:
        try:
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        except Exception:
            pass
    return w3


@pytest.fixture(scope="session")
def deployer_account(w3):
    """Deployer account for production"""
    private_key = os.getenv("DEPLOYER_PRIVATE_KEY")
    if not private_key:
        pytest.skip("DEPLOYER_PRIVATE_KEY not configured")
    return w3.eth.account.from_key(private_key)


@pytest.fixture(scope="session")
def flash_loan_contract(w3, deployer_account):
    """Deployed flash loan contract"""
    deployment_file = Path(__file__).parent.parent / "artifacts" / "deployment_addresses.json"
    
    if deployment_file.exists():
        with open(deployment_file) as f:
            addresses = json.load(f)
            if 'FlashLoanExecutor' in addresses:
                return w3.eth.contract(
                    address=addresses['FlashLoanExecutor'],
                    abi=json.load(open(Path(__file__).parent.parent / "artifacts" / "FlashLoanExecutor.json"))
                )
    
    pytest.skip("Contract not deployed")


@pytest.fixture(scope="session")
def trading_config():
    """Production trading configuration"""
    config_file = Path(__file__).parent.parent / "config" / "trading_config.json"
    
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
            # Verify production settings
            assert config.get("trading", {}).get("test_mode") == False
            assert config.get("trading", {}).get("simulate_trades") == False
            assert config.get("trading", {}).get("auto_execute") == True
            return config
    
    pytest.skip("Production config not found")


@pytest.fixture(scope="session")
def mock_price_oracle():
    """Mock oracle for price verification"""
    return {
        "ETH_USD": 2000.0,
        "WBTC_USD": 40000.0,
        "DAI_USD": 1.0
    }


@pytest.fixture(scope="session")
def risk_manager_config():
    """Risk management configuration"""
    return {
        "max_daily_loss_usd": 10000,
        "max_loss_per_trade_usd": 1000,
        "stop_loss_percentage": 5,
        "take_profit_percentage": 10,
        "max_drawdown_percentage": 15
    }


@pytest.fixture(scope="session")
def local_rpc_url():
    """Local RPC URL for testing"""
    return os.getenv("LOCAL_RPC_URL", "http://localhost:8545")
