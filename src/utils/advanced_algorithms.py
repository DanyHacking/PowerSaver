"""
ADVANCED TRADING ALGORITHMS
Position sizing, risk management, portfolio optimization
"""

import asyncio
import logging
import time
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)


# ============== KELLY CRITERION ==============

class PositionSizer:
    """
    Optimal position sizing using Kelly Criterion
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Kelly fraction cap
        self.max_kelly = config.get("max_kelly", 0.25)  # Never risk more than 25%
        self.kelly_divisor = config.get("kelly_divisor", 2)  # Half-Kelly for safety
        
        # Historical data
        self._win_history = deque(maxlen=100)
        self._loss_history = deque(maxlen=100)
        self._profit_history = deque(maxlen=1000)
    
    def calculate_position_size(
        self,
        bankroll: float,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        Calculate optimal position size using Kelly Criterion
        """
        if win_rate <= 0 or avg_loss <= 0:
            return 0
        
        # Kelly formula: f* = (bp - q) / b
        # where b = odds, p = win rate, q = loss rate
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - p
        
        kelly = (b * p - q) / b
        
        # Apply safety measures
        kelly = min(kelly, self.max_kelly)  # Cap at max
        kelly = max(kelly, 0)  # No negative
        
        # Use half-Kelly for safety
        kelly = kelly / self.kelly_divisor
        
        return bankroll * kelly
    
    def record_trade(self, profit: float):
        """Record trade result"""
        self._profit_history.append(profit)
        
        if profit > 0:
            self._win_history.append(profit)
        else:
            self._loss_history.append(abs(profit))
    
    def get_win_rate(self) -> float:
        """Calculate current win rate"""
        total = len(self._win_history) + len(self._loss_history)
        if total == 0:
            return 0.5  # Default
        
        return len(self._win_history) / total
    
    def get_avg_win(self) -> float:
        """Calculate average win"""
        if not self._win_history:
            return 100  # Default
        return sum(self._win_history) / len(self._win_history)
    
    def get_avg_loss(self) -> float:
        """Calculate average loss"""
        if not self._loss_history:
            return 100
        return sum(self._loss_history) / len(self._loss_history)


# ============== RISK MANAGER ==============

class RiskManager:
    """
    Advanced risk management
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Limits
        self.max_position_pct = config.get("max_position_pct", 0.2)  # 20% of bankroll
        self.max_daily_loss_pct = config.get("max_daily_loss_pct", 0.05)  # 5%
        self.max_drawdown_pct = config.get("max_drawdown_pct", 0.15)  # 15%
        
        # State
        self.daily_pnl = 0.0
        self.peak_equity = 0.0
        self.current_equity = 0.0
        self.trades_today = 0
        self.losses_today = 0
    
    def can_open_position(
        self,
        position_size: float,
        current_equity: float
    ) -> Tuple[bool, str]:
        """Check if can open new position"""
        
        # Check daily loss limit
        if self.daily_pnl < -current_equity * self.max_daily_loss_pct:
            return False, "Daily loss limit exceeded"
        
        # Check drawdown
        if current_equity < self.peak_equity * (1 - self.max_drawdown_pct):
            return False, "Max drawdown exceeded"
        
        # Check position size
        if position_size > current_equity * self.max_position_pct:
            return False, "Position too large"
        
        return True, "OK"
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        position_size: float,
        risk_pct: float = 0.02
    ) -> float:
        """Calculate stop loss price"""
        return entry_price * (1 - risk_pct)
    
    def calculate_take_profit(
        self,
        entry_price: float,
        risk_reward_ratio: float = 2.0,
        stop_loss: float = None
    ) -> float:
        """Calculate take profit price"""
        if stop_loss:
            risk = entry_price - stop_loss
            return entry_price + (risk * risk_reward_ratio)
        return entry_price * 1.04  # Default 4%


# ============== PORTFOLIO REBALANCER ==============

class PortfolioRebalancer:
    """
    Automatic portfolio rebalancing
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        self.target_allocation = config.get("target_allocation", {
            "ETH": 0.4,
            "USDC": 0.3,
            "WBTC": 0.2,
            "OTHER": 0.1
        })
        
        self.rebalance_threshold = config.get("rebalance_threshold", 0.05)  # 5%
    
    def should_rebalance(self, current_allocation: Dict[str, float]) -> bool:
        """Check if should rebalance"""
        for asset, target in self.target_allocation.items():
            current = current_allocation.get(asset, 0)
            diff = abs(current - target)
            
            if diff > self.rebalance_threshold:
                return True
        
        return False
    
    def calculate_rebalance_trades(
        self,
        current_allocation: Dict[str, float],
        total_value: float
    ) -> List[Dict]:
        """Calculate trades needed for rebalance"""
        trades = []
        
        for asset, target in self.target_allocation.items():
            current = current_allocation.get(asset, 0)
            target_value = total_value * target
            current_value = total_value * current
            
            diff_value = target_value - current_value
            
            if abs(diff_value) > 100:  # Min $100 trade
                trades.append({
                    "asset": asset,
                    "action": "buy" if diff_value > 0 else "sell",
                    "amount": abs(diff_value)
                })
        
        return trades


# ============== ORDER SPLITTER ==============

class OrderSplitter:
    """
    Split large orders to minimize slippage
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        self.max_order_size = config.get("max_order_size", 10000)  # $10k max
        self.split_count = config.get("split_count", 5)
        self.time_delay = config.get("time_delay", 2)  # seconds between
    
    def split_order(self, total_amount: float) -> List[float]:
        """Split order into smaller pieces"""
        if total_amount <= self.max_order_size:
            return [total_amount]
        
        # Calculate split
        split_amount = total_amount / self.split_count
        remainder = total_amount % self.split_count
        
        splits = [split_amount] * self.split_count
        splits[0] += remainder  # Add remainder to first
        
        return splits
    
    def get_execution_schedule(
        self,
        total_amount: float,
        current_price: float
    ) -> List[Dict]:
        """Get execution schedule"""
        splits = self.split_order(total_amount)
        
        schedule = []
        base_time = time.time()
        
        for i, amount in enumerate(splits):
            # TWAP-style execution (simple version)
            schedule.append({
                "amount": amount,
                "execute_after": base_time + (i * self.time_delay),
                "price_limit": current_price * 1.01 if i > 0 else current_price * 1.005
            })
        
        return schedule


# ============== SLIPPAGE OPTIMIZER ==============

class SlippageOptimizer:
    """
    Optimize slippage settings dynamically
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        self.base_slippage = config.get("base_slippage", 0.005)  # 0.5%
        self._slippage_history = deque(maxlen=100)
    
    def calculate_optimal_slippage(
        self,
        trade_size_usd: float,
        liquidity_available: float,
        volatility: float,
        urgency: str
    ) -> float:
        """
        Calculate optimal slippage
        """
        # Base slippage from trade size
        size_slippage = min(trade_size_usd / liquidity_available, 0.1)
        
        # Volatility adjustment
        vol_slippage = volatility * 0.5
        
        # Urgency adjustment
        if urgency == "high":
            urgency_multiplier = 1.5
        elif urgency == "medium":
            urgency_multiplier = 1.2
        else:
            urgency_multiplier = 1.0
        
        # Calculate total
        slippage = (size_slippage + vol_slippage) * urgency_multiplier
        slippage = max(slippage, self.base_slippage)  # At least base
        slippage = min(slippage, 0.20)  # Cap at 20%
        
        return slippage
    
    def record_execution(
        self,
        expected_price: float,
        actual_price: float
    ):
        """Record execution for learning"""
        slippage = abs(actual_price - expected_price) / expected_price
        self._slippage_history.append(slippage)
    
    def get_average_slippage(self) -> float:
        """Get average slippage"""
        if not self._slippage_history:
            return self.base_slippage
        
        return sum(self._slippage_history) / len(self._slippage_history)


# ============== MULTI-STEP ARBITRAGE ==============

class MultiStepArbitrage:
    """
    Multi-step arbitrage execution
    """
    
    # Known profitable routes
    ROUTES = {
        "eth_usdc_uniswap": ["ETH", "USDC", "uniswap_v2"],
        "eth_usdc_sushi": ["ETH", "USDC", "sushiswap"],
        "weth_eth_uniswap": ["WETH", "ETH", "uniswap_v2"],
        "eth_dai_uniswap": ["ETH", "DAI", "uniswap_v2"],
    }
    
    def __init__(self, config: Dict):
        self.config = config
        self._route_profits = {}
    
    async def find_best_route(
        self,
        amount: float,
        token_in: str,
        prices: Dict
    ) -> Optional[Dict]:
        """Find most profitable route"""
        best_route = None
        best_profit = 0
        
        for route_name, route_tokens in self.ROUTES.items():
            if route_tokens[0] != token_in:
                continue
            
            # Simulate route
            profit = await self._simulate_route(
                amount,
                route_tokens,
                prices
            )
            
            if profit > best_profit:
                best_profit = profit
                best_route = {
                    "name": route_name,
                    "tokens": route_tokens,
                    "profit": profit,
                    "profit_pct": profit / amount * 100
                }
        
        return best_route
    
    async def _simulate_route(
        self,
        amount: float,
        route_tokens: List[str],
        prices: Dict
    ) -> float:
        """Simulate route profit"""
        # Simplified - would use actual prices
        # Assuming 0.3% fee per swap
        fee = 0.003
        
        current = amount
        for i in range(len(route_tokens) - 1):
            # Apply swap with fee
            current = current * (1 - fee)
        
        # Return profit
        return max(0, current - amount)


# ============== FACTORIES ==============

def create_position_sizer(config: Dict = None) -> PositionSizer:
    return PositionSizer(config or {})

def create_risk_manager(config: Dict = None) -> RiskManager:
    return RiskManager(config or {})

def create_portfolio_rebalancer(config: Dict = None) -> PortfolioRebalancer:
    return PortfolioRebalancer(config or {})

def create_order_splitter(config: Dict = None) -> OrderSplitter:
    return OrderSplitter(config or {})

def create_slippage_optimizer(config: Dict = None) -> SlippageOptimizer:
    return SlippageOptimizer(config or {})

def create_multi_step_arbitrage(config: Dict = None) -> MultiStepArbitrage:
    return MultiStepArbitrage(config or {})
