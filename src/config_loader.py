"""
Configuration Loader - Load sensitive data from .env file
Never commit sensitive data to version control
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load and manage configuration from environment variables"""
    
    def __init__(self, env_path: str = None):
        self.env_path = env_path or os.path.join(Path(__file__).parent.parent, '.env')
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from .env file"""
        # Load environment variables
        load_dotenv(self.env_path)
        
        # Load all configuration
        self.config = {
            # Blockchain Configuration
            'BLOCKCHAIN_NETWORK': os.getenv('BLOCKCHAIN_NETWORK', 'ethereum'),
            'ETHEREUM_RPC_URL': os.getenv('ETHEREUM_RPC_URL', ''),
            'POLYGON_RPC_URL': os.getenv('POLYGON_RPC_URL', ''),
            'ARBITRUM_RPC_URL': os.getenv('ARBITRUM_RPC_URL', ''),
            'OPTIMISM_RPC_URL': os.getenv('OPTIMISM_RPC_URL', ''),
            'ETHEREUM_CHAIN_ID': int(os.getenv('ETHEREUM_CHAIN_ID', '1')),
            'POLYGON_CHAIN_ID': int(os.getenv('POLYGON_CHAIN_ID', '137')),
            'ARBITRUM_CHAIN_ID': int(os.getenv('ARBITRUM_CHAIN_ID', '42161')),
            'OPTIMISM_CHAIN_ID': int(os.getenv('OPTIMISM_CHAIN_ID', '10')),
            
            # Wallet Configuration
            'TRADING_WALLET_PRIVATE_KEY': os.getenv('TRADING_WALLET_PRIVATE_KEY', ''),
            'TRADING_WALLET_ADDRESS': os.getenv('TRADING_WALLET_ADDRESS', ''),
            'MAX_PRIORITY_FEE_GWEI': int(os.getenv('MAX_PRIORITY_FEE_GWEI', '3')),
            'MAX_FEE_GWEI': int(os.getenv('MAX_FEE_GWEI', '50')),
            
            # DeFi Protocols
            'AAVE_V3_POOL_ADDRESS': os.getenv('AAVE_V3_POOL_ADDRESS', ''),
            'AAVE_FLASH_LOAN_FEE_BPS': int(os.getenv('AAVE_FLASH_LOAN_FEE_BPS', '900')),
            'UNISWAP_V2_FACTORY_ADDRESS': os.getenv('UNISWAP_V2_FACTORY_ADDRESS', ''),
            'UNISWAP_V3_FACTORY_ADDRESS': os.getenv('UNISWAP_V3_FACTORY_ADDRESS', ''),
            'SUSHISWAP_FACTORY_ADDRESS': os.getenv('SUSHISWAP_FACTORY_ADDRESS', ''),
            'BALANCER_V2_VAULT_ADDRESS': os.getenv('BALANCER_V2_VAULT_ADDRESS', ''),
            
            # Token Addresses
            'WETH_ADDRESS': os.getenv('WETH_ADDRESS', ''),
            'USDC_ADDRESS': os.getenv('USDC_ADDRESS', ''),
            'DAI_ADDRESS': os.getenv('DAI_ADDRESS', ''),
            'WBTC_ADDRESS': os.getenv('WBTC_ADDRESS', ''),
            'AAVE_TOKEN_ADDRESS': os.getenv('AAVE_TOKEN_ADDRESS', ''),
            
            # Trading Configuration
            'LOAN_AMOUNT_USD': int(os.getenv('LOAN_AMOUNT_USD', '10000')),
            'MAX_LOAN_AMOUNT_USD': int(os.getenv('MAX_LOAN_AMOUNT_USD', '100000')),
            'MAX_POSITION_SIZE_USD': int(os.getenv('MAX_POSITION_SIZE_USD', '50000')),
            'MIN_PROFIT_THRESHOLD_USD': int(os.getenv('MIN_PROFIT_THRESHOLD_USD', '500')),
            'MAX_CONCURRENT_TRADES': int(os.getenv('MAX_CONCURRENT_TRADES', '3')),
            'TRADING_STRATEGY': os.getenv('TRADING_STRATEGY', 'balanced'),
            'SUPPORTED_TOKENS': os.getenv('SUPPORTED_TOKENS', 'ETH,USDC,DAI,WBTC').split(','),
            'SUPPORTED_EXCHANGES': os.getenv('SUPPORTED_EXCHANGES', 'uniswap_v2,uniswap_v3,sushiswap,balancer').split(','),
            
            # Risk Management
            'MAX_DAILY_LOSS_USD': int(os.getenv('MAX_DAILY_LOSS_USD', '10000')),
            'MAX_LOSS_PER_TRADE_USD': int(os.getenv('MAX_LOSS_PER_TRADE_USD', '1000')),
            'STOP_LOSS_PERCENTAGE': float(os.getenv('STOP_LOSS_PERCENTAGE', '5')),
            'TAKE_PROFIT_PERCENTAGE': float(os.getenv('TAKE_PROFIT_PERCENTAGE', '10')),
            'MAX_DRAWDOWN_PERCENTAGE': float(os.getenv('MAX_DRAWDOWN_PERCENTAGE', '15')),
            'MAX_ERRORS_BEFORE_STOP': int(os.getenv('MAX_ERRORS_BEFORE_STOP', '10')),
            'ERROR_TIME_WINDOW_SECONDS': int(os.getenv('ERROR_TIME_WINDOW_SECONDS', '3600')),
            
            # Monitoring & Alerts
            'ENABLE_EMAIL_ALERTS': os.getenv('ENABLE_EMAIL_ALERTS', 'true').lower() == 'true',
            'SMTP_SERVER': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'SMTP_PORT': int(os.getenv('SMTP_PORT', '587')),
            'SMTP_USERNAME': os.getenv('SMTP_USERNAME', ''),
            'SMTP_PASSWORD': os.getenv('SMTP_PASSWORD', ''),
            'DISCORD_WEBHOOK_URL': os.getenv('DISCORD_WEBHOOK_URL', ''),
            'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN', ''),
            'TELEGRAM_CHAT_ID': os.getenv('TELEGRAM_CHAT_ID', ''),
            
            # API Keys
            'ETHERSCAN_API_KEY': os.getenv('ETHERSCAN_API_KEY', ''),
            'COINGECKO_API_KEY': os.getenv('COINGECKO_API_KEY', ''),
            'INFURA_API_KEY': os.getenv('INFURA_API_KEY', ''),
            'ALCHEMY_API_KEY': os.getenv('ALCHEMY_API_KEY', ''),
            
            # System Configuration
            'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
            'MONITORING_INTERVAL_SECONDS': int(os.getenv('MONITORING_INTERVAL_SECONDS', '30')),
            'HEALTH_CHECK_INTERVAL_SECONDS': int(os.getenv('HEALTH_CHECK_INTERVAL_SECONDS', '10')),
            'RECOVERY_COOLDOWN_SECONDS': int(os.getenv('RECOVERY_COOLDOWN_SECONDS', '300')),
            'MAX_RETRIES_BEFORE_STOP': int(os.getenv('MAX_RETRIES_BEFORE_STOP', '3')),
            'GAS_OPTIMIZATION_ENABLED': os.getenv('GAS_OPTIMIZATION_ENABLED', 'true').lower() == 'true',
            'AI_PREDICTIONS_ENABLED': os.getenv('AI_PREDICTIONS_ENABLED', 'true').lower() == 'true',
            'PORTFOLIO_REBALANCING_ENABLED': os.getenv('PORTFOLIO_REBALANCING_ENABLED', 'true').lower() == 'true',
            
            # Backtesting
            'HISTORICAL_DATA_PATH': os.getenv('HISTORICAL_DATA_PATH', './data/historical_trades.json'),
            'BACKTEST_START_DATE': os.getenv('BACKTEST_START_DATE', '2024-01-01'),
            'BACKTEST_END_DATE': os.getenv('BACKTEST_END_DATE', '2024-12-31'),
            
            # Security
            'ENCRYPT_SENSITIVE_DATA': os.getenv('ENCRYPT_SENSITIVE_DATA', 'true').lower() == 'true',
            'ENCRYPTION_KEY': os.getenv('ENCRYPTION_KEY', ''),
            'API_RATE_LIMIT': int(os.getenv('API_RATE_LIMIT', '60')),
            'MAX_TRADE_EXECUTION_TIME_SECONDS': int(os.getenv('MAX_TRADE_EXECUTION_TIME_SECONDS', '300')),
            
            # Development
            'TEST_MODE': os.getenv('TEST_MODE', 'false').lower() == 'true',
            'SIMULATE_TRADES': os.getenv('SIMULATE_TRADES', 'true').lower() == 'true',
            'SIMULATION_CONFIDENCE': float(os.getenv('SIMULATION_CONFIDENCE', '0.8')),
        }
        
        logger.info(f"Configuration loaded from {self.env_path}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def get_wallet_address(self) -> str:
        """Get wallet address from config"""
        return self.config.get('TRADING_WALLET_ADDRESS', '')
    
    def get_private_key(self) -> str:
        """Get private key from config (use with caution)"""
        return self.config.get('TRADING_WALLET_PRIVATE_KEY', '')
    
    def get_rpc_url(self, chain: str = None) -> str:
        """Get RPC URL for specific chain"""
        if chain == 'polygon':
            return self.config.get('POLYGON_RPC_URL', '')
        elif chain == 'arbitrum':
            return self.config.get('ARBITRUM_RPC_URL', '')
        elif chain == 'optimism':
            return self.config.get('OPTIMISM_RPC_URL', '')
        else:
            return self.config.get('ETHEREUM_RPC_URL', '')
    
    def get_chain_id(self, chain: str = None) -> int:
        """Get chain ID for specific chain"""
        if chain == 'polygon':
            return self.config.get('POLYGON_CHAIN_ID', 137)
        elif chain == 'arbitrum':
            return self.config.get('ARBITRUM_CHAIN_ID', 42161)
        elif chain == 'optimism':
            return self.config.get('OPTIMISM_CHAIN_ID', 10)
        else:
            return self.config.get('ETHEREUM_CHAIN_ID', 1)
    
    def get_token_address(self, token: str) -> str:
        """Get token address for specific token"""
        token_map = {
            'WETH': self.config.get('WETH_ADDRESS', ''),
            'USDC': self.config.get('USDC_ADDRESS', ''),
            'DAI': self.config.get('DAI_ADDRESS', ''),
            'WBTC': self.config.get('WBTC_ADDRESS', ''),
            'AAVE': self.config.get('AAVE_TOKEN_ADDRESS', ''),
        }
        return token_map.get(token.upper(), '')
    
    def get_protocol_address(self, protocol: str) -> str:
        """Get protocol address for specific protocol"""
        protocol_map = {
            'aave_v3': self.config.get('AAVE_V3_POOL_ADDRESS', ''),
            'uniswap_v2': self.config.get('UNISWAP_V2_FACTORY_ADDRESS', ''),
            'uniswap_v3': self.config.get('UNISWAP_V3_FACTORY_ADDRESS', ''),
            'sushiswap': self.config.get('SUSHISWAP_FACTORY_ADDRESS', ''),
            'balancer': self.config.get('BALANCER_V2_VAULT_ADDRESS', ''),
        }
        return protocol_map.get(protocol.lower(), '')
    
    def is_sensitive_data_loaded(self) -> bool:
        """Check if sensitive data is properly loaded"""
        return bool(self.config.get('TRADING_WALLET_PRIVATE_KEY', ''))
    
    def get_trading_config(self) -> Dict[str, Any]:
        """Get trading-specific configuration"""
        return {
            'loan_amount': self.config.get('LOAN_AMOUNT_USD', 10000),
            'max_loan_amount': self.config.get('MAX_LOAN_AMOUNT_USD', 100000),
            'max_position_size': self.config.get('MAX_POSITION_SIZE_USD', 50000),
            'min_profit_threshold': self.config.get('MIN_PROFIT_THRESHOLD_USD', 500),
            'max_concurrent_trades': self.config.get('MAX_CONCURRENT_TRADES', 3),
            'tokens': self.config.get('SUPPORTED_TOKENS', ['ETH', 'USDC', 'DAI']),
            'exchanges': self.config.get('SUPPORTED_EXCHANGES', ['uniswap_v2', 'uniswap_v3', 'sushiswap']),
            'strategy': self.config.get('TRADING_STRATEGY', 'balanced'),
        }
    
    def get_risk_config(self) -> Dict[str, Any]:
        """Get risk management configuration"""
        return {
            'max_loan_amount': self.config.get('MAX_LOAN_AMOUNT_USD', 100000),
            'max_daily_loss': self.config.get('MAX_DAILY_LOSS_USD', 10000),
            'max_position_size': self.config.get('MAX_POSITION_SIZE_USD', 50000),
            'min_profit_threshold': self.config.get('MIN_PROFIT_THRESHOLD_USD', 500),
            'max_concurrent_trades': self.config.get('MAX_CONCURRENT_TRADES', 3),
            'stop_loss_percentage': self.config.get('STOP_LOSS_PERCENTAGE', 5),
            'take_profit_percentage': self.config.get('TAKE_PROFIT_PERCENTAGE', 10),
            'max_drawdown_percentage': self.config.get('MAX_DRAWDOWN_PERCENTAGE', 15),
            'max_errors_before_stop': self.config.get('MAX_ERRORS_BEFORE_STOP', 10),
            'error_time_window': self.config.get('ERROR_TIME_WINDOW_SECONDS', 3600),
        }
    
    def print_config_summary(self):
        """Print configuration summary (without sensitive data)"""
        print("\n" + "="*70)
        print("CONFIGURATION SUMMARY")
        print("="*70)
        print(f"Blockchain: {self.config.get('BLOCKCHAIN_NETWORK', 'ethereum')}")
        print(f"Chain ID: {self.config.get('ETHEREUM_CHAIN_ID', 1)}")
        print(f"Loan Amount: ${self.config.get('LOAN_AMOUNT_USD', 10000)}")
        print(f"Max Loan: ${self.config.get('MAX_LOAN_AMOUNT_USD', 100000)}")
        print(f"Min Profit Threshold: ${self.config.get('MIN_PROFIT_THRESHOLD_USD', 500)}")
        print(f"Max Concurrent Trades: {self.config.get('MAX_CONCURRENT_TRADES', 3)}")
        print(f"Trading Strategy: {self.config.get('TRADING_STRATEGY', 'balanced')}")
        print(f"Supported Tokens: {', '.join(self.config.get('SUPPORTED_TOKENS', []))}")
        print(f"Supported Exchanges: {', '.join(self.config.get('SUPPORTED_EXCHANGES', []))}")
        print(f"Max Daily Loss: ${self.config.get('MAX_DAILY_LOSS_USD', 10000)}")
        print(f"Gas Optimization: {'Enabled' if self.config.get('GAS_OPTIMIZATION_ENABLED') else 'Disabled'}")
        print(f"AI Predictions: {'Enabled' if self.config.get('AI_PREDICTIONS_ENABLED') else 'Disabled'}")
        print(f"Portfolio Rebalancing: {'Enabled' if self.config.get('PORTFOLIO_REBALANCING_ENABLED') else 'Disabled'}")
        print(f"Test Mode: {'Enabled' if self.config.get('TEST_MODE') else 'Disabled'}")
        print("="*70)
        print("⚠️  SENSITIVE DATA (Private Keys, API Keys) NOT SHOWN")
        print("="*70 + "\n")


# Singleton instance
_config_instance: Optional[ConfigLoader] = None


def get_config() -> ConfigLoader:
    """Get configuration loader instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader()
    return _config_instance


def load_config(env_path: str = None) -> ConfigLoader:
    """Load configuration from .env file"""
    global _config_instance
    _config_instance = ConfigLoader(env_path)
    return _config_instance
