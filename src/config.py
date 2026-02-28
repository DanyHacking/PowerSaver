"""
Minimal configuration loader for trading system
"""

import os
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables
load_dotenv()

class Config:
    """Minimal configuration class"""
    
    # AAVE Flash Loan
    AAVE_POOL_ADDRESS = os.getenv("AAVE_POOL_ADDRESS", "0x87870Bca3F3fD6335C3F4ce6260135144110A857")
    AAVE_PROVIDER_ADDRESS = os.getenv("AAVE_PROVIDER_ADDRESS", "0x2f39d218133AFaB8F2B819B1066c7E484DD26110")
    
    # Ethereum Network
    RPC_URL = os.getenv("RPC_URL", "https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID")
    PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
    CHAIN_ID = int(os.getenv("CHAIN_ID", "1"))
    
    # Trading Configuration
    LOAN_AMOUNT_USD = int(os.getenv("LOAN_AMOUNT_USD", "10000"))
    MAX_LOAN_AMOUNT_USD = int(os.getenv("MAX_LOAN_AMOUNT_USD", "100000"))
    MAX_DAILY_LOSS_USD = int(os.getenv("MAX_DAILY_LOSS_USD", "10000"))
    MIN_PROFIT_THRESHOLD_USD = int(os.getenv("MIN_PROFIT_THRESHOLD_USD", "500"))
    TRADING_STRATEGY = os.getenv("TRADING_STRATEGY", "balanced")
    
    # Exchanges
    SUPPORTED_TOKENS = os.getenv("SUPPORTED_TOKENS", "ETH,USDC,DAI,WBTC").split(",")
    SUPPORTED_EXCHANGES = os.getenv("SUPPORTED_EXCHANGES", "uniswap_v2,uniswap_v3,sushiswap,balancer").split(",")
    
    # Security
    EMERGENCY_PAUSE = os.getenv("EMERGENCY_PAUSE", "false").lower() == "true"
    MAX_CONCURRENT_TRADES = int(os.getenv("MAX_CONCURRENT_TRADES", "3"))
    GAS_OPTIMIZATION_ENABLED = os.getenv("GAS_OPTIMIZATION_ENABLED", "true").lower() == "true"
    AI_PREDICTIONS_ENABLED = os.getenv("AI_PREDICTIONS_ENABLED", "true").lower() == "true"
    
    # Monitoring
    SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
    EMAIL_ALERTS = os.getenv("EMAIL_ALERTS", "false").lower() == "true"
    SMS_ALERTS = os.getenv("SMS_ALERTS", "false").lower() == "true"
    
    # API Keys (Optional)
    ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
    CHAINLINK_API_KEY = os.getenv("CHAINLINK_API_KEY", "")
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return {
            "loan_amount": cls.LOAN_AMOUNT_USD,
            "max_loan_amount": cls.MAX_LOAN_AMOUNT_USD,
            "max_daily_loss": cls.MAX_DAILY_LOSS_USD,
            "min_profit_threshold": cls.MIN_PROFIT_THRESHOLD_USD,
            "trading_strategy": cls.TRADING_STRATEGY,
            "max_concurrent_trades": cls.MAX_CONCURRENT_TRADES,
            "tokens": cls.SUPPORTED_TOKENS,
            "exchanges": cls.SUPPORTED_EXCHANGES,
            "gas_optimization_enabled": cls.GAS_OPTIMIZATION_ENABLED,
            "ai_predictions_enabled": cls.AI_PREDICTIONS_ENABLED
        }
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        if not cls.PRIVATE_KEY:
            raise ValueError("PRIVATE_KEY is required")
        if not cls.RPC_URL or "YOUR_INFURA_PROJECT_ID" in cls.RPC_URL:
            raise ValueError("RPC_URL must be configured with valid Infura project ID")
        return True

# Initialize configuration
config = Config()
