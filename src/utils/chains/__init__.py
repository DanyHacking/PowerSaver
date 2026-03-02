"""Multi-chain support module"""

from .multi_chain import (
    ChainType,
    ChainConfig,
    MultiChainManager,
    GasOptimizer,
    AutoCompound,
    AdvancedRiskManager,
    CHAIN_CONFIGS,
    create_multi_chain_manager,
    create_gas_optimizer,
    create_auto_compound,
    create_advanced_risk_manager
)

__all__ = [
    "ChainType",
    "ChainConfig", 
    "MultiChainManager",
    "GasOptimizer",
    "AutoCompound",
    "AdvancedRiskManager",
    "CHAIN_CONFIGS",
    "create_multi_chain_manager",
    "create_gas_optimizer",
    "create_auto_compound",
    "create_advanced_risk_manager"
]
