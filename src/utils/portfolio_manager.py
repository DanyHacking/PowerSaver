"""
Advanced Portfolio Management System
Dynamic allocation, rebalancing, and multi-asset optimization
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class Asset:
    """Portfolio asset"""
    symbol: str
    address: str
    balance: float
    value_usd: float
    allocation_percent: float
    historical_returns: List[float] = field(default_factory=list)


@dataclass
class PortfolioAllocation:
    """Target portfolio allocation"""
    symbol: str
    target_percent: float
    min_percent: float
    max_percent: float


@dataclass
class RebalanceResult:
    """Rebalancing result"""
    timestamp: datetime
    trades: List[Dict]
    total_value_before: float
    total_value_after: float
    fees_paid: float


class PortfolioManager:
    """
    Advanced portfolio management with dynamic allocation
    """
    
    def __init__(self, initial_capital: float, config: Dict = None):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.config = config or {}
        
        # Current holdings
        self.assets: Dict[str, Asset] = {}
        
        # Target allocation
        self.target_allocation: List[PortfolioAllocation] = []
        
        # Performance history
        self.performance_history: List[Dict] = []
        
        # Rebalance threshold
        self.rebalance_threshold = self.config.get("rebalance_threshold", 0.05)  # 5%
    
    def set_target_allocation(self, allocation: List[PortfolioAllocation]):
        """Set target portfolio allocation"""
        self.target_allocation = allocation
        
        # Initialize assets if needed
        for alloc in allocation:
            if alloc.symbol not in self.assets:
                self.assets[alloc.symbol] = Asset(
                    symbol=alloc.symbol,
                    address="",
                    balance=0,
                    value_usd=0,
                    allocation_percent=0
                )
    
    async def update_portfolio_value(self, prices: Dict[str, float]):
        """Update portfolio with current prices"""
        total_value = 0
        
        for symbol, asset in self.assets.items():
            price = prices.get(symbol, 0)
            asset.value_usd = asset.balance * price
            total_value += asset.value_usd
        
        # Update allocations
        for symbol, asset in self.assets.items():
            if total_value > 0:
                asset.allocation_percent = (asset.value_usd / total_value) * 100
            else:
                asset.allocation_percent = 0
        
        self.current_capital = total_value
        
        return total_value
    
    def check_rebalance_needed(self) -> bool:
        """Check if portfolio needs rebalancing"""
        for alloc in self.target_allocation:
            symbol = alloc.symbol
            if symbol not in self.assets:
                return True
            
            current = self.assets[symbol].allocation_percent
            target = alloc.target_percent
            
            # Check if deviation exceeds threshold
            if abs(current - target) > (self.rebalance_threshold * 100):
                return True
        
        return False
    
    def calculate_rebalance_trades(self) -> List[Dict]:
        """Calculate trades needed to rebalance portfolio"""
        trades = []
        
        total_value = self.current_capital
        
        for alloc in self.target_allocation:
            symbol = alloc.symbol
            target_percent = alloc.target_percent
            target_value = total_value * (target_percent / 100)
            
            current_value = self.assets.get(symbol, Asset(symbol, "", 0, 0, 0)).value_usd
            diff_value = target_value - current_value
            
            if abs(diff_value) > 10:  # Min $10 trade
                # Get price (would be from price feed in production)
                price = 1  # Simplified
                
                if diff_value > 0:
                    # Buy
                    amount = diff_value / price
                    trades.append({
                        "action": "buy",
                        "symbol": symbol,
                        "amount": amount,
                        "value": diff_value
                    })
                else:
                    # Sell
                    amount = abs(diff_value) / price
                    trades.append({
                        "action": "sell",
                        "symbol": symbol,
                        "amount": amount,
                        "value": abs(diff_value)
                    })
        
        return trades
    
    async def execute_rebalance(self, prices: Dict[str, float]) -> RebalanceResult:
        """Execute portfolio rebalancing"""
        total_before = await self.update_portfolio_value(prices)
        
        trades = self.calculate_rebalance_trades()
        
        # Simulate trades (in production, execute on DEX)
        for trade in trades:
            logger.info(f"Rebalance: {trade['action']} {trade['amount']} {trade['symbol']}")
            
            # Update holdings
            symbol = trade["symbol"]
            if symbol not in self.assets:
                self.assets[symbol] = Asset(
                    symbol=symbol,
                    address="",
                    balance=0,
                    value_usd=0,
                    allocation_percent=0
                )
            
            if trade["action"] == "buy":
                self.assets[symbol].balance += trade["amount"]
            else:
                self.assets[symbol].balance -= trade["amount"]
        
        # Update values
        total_after = await self.update_portfolio_value(prices)
        
        # Calculate fees (estimate)
        fees = sum(t["value"] for t in trades) * 0.003  # 0.3% fee
        
        result = RebalanceResult(
            timestamp=datetime.now(),
            trades=trades,
            total_value_before=total_before,
            total_value_after=total_after,
            fees_paid=fees
        )
        
        # Record performance
        self.performance_history.append({
            "timestamp": result.timestamp,
            "total_value": total_after,
            "fees": fees,
            "trades_count": len(trades)
        })
        
        return result
    
    def get_performance_metrics(self) -> Dict:
        """Get portfolio performance metrics"""
        if not self.performance_history:
            return {}
        
        initial = self.performance_history[0]["total_value"]
        current = self.performance_history[-1]["total_value"]
        
        total_return = (current - initial) / initial * 100
        
        # Calculate volatility
        returns = []
        for i in range(1, len(self.performance_history)):
            prev = self.performance_history[i-1]["total_value"]
            curr = self.performance_history[i]["total_value"]
            ret = (curr - prev) / prev
            returns.append(ret)
        
        import numpy as np
        volatility = np.std(returns) * 100 if returns else 0
        
        # Sharpe ratio (assuming 5% risk-free rate)
        sharpe = ((total_return - 5) / volatility) if volatility > 0 else 0
        
        return {
            "initial_capital": initial,
            "current_value": current,
            "total_return_percent": total_return,
            "volatility_percent": volatility,
            "sharpe_ratio": sharpe,
            "total_trades": sum(p["trades_count"] for p in self.performance_history),
            "total_fees": sum(p["fees"] for p in self.performance_history)
        }
    
    def get_current_allocation(self) -> Dict:
        """Get current portfolio allocation"""
        return {
            symbol: {
                "balance": asset.balance,
                "value_usd": asset.value_usd,
                "allocation_percent": asset.allocation_percent
            }
            for symbol, asset in self.assets.items()
        }


class YieldOptimizer:
    """
    Optimizes yield by automatically deploying idle capital
    """
    
    # Yield protocols (simplified)
    YIELD_SOURCES = {
        "aave": {
            "protocol": "Aave V3",
            "token": "aETH",
            "apr_estimate": 0.04,  # 4% APY
            "risk_level": "low"
        },
        "compound": {
            "protocol": "Compound",
            "token": "cETH",
            "apr_estimate": 0.035,
            "risk_level": "low"
        },
        "yearn": {
            "protocol": "Yearn Finance",
            "token": "yETH",
            "apr_estimate": 0.06,
            "risk_level": "medium"
        },
        "lido": {
            "protocol": "Lido",
            "token": "stETH",
            "apr_estimate": 0.045,
            "risk_level": "medium"
        }
    }
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.deployed_positions = {}
    
    def find_best_yield(self, token: str, amount: float) -> Optional[Dict]:
        """Find best yield opportunity for token"""
        opportunities = []
        
        for source_id, source in self.YIELD_SOURCES.items():
            # Check if token is supported
            if source_id in ["aave", "compound", "lido"] and token.upper() in ["ETH", "WETH"]:
                opportunities.append({
                    "source": source_id,
                    "protocol": source["protocol"],
                    "apr": source["apr_estimate"],
                    "risk": source["risk_level"]
                })
        
        if not opportunities:
            return None
        
        # Sort by APR
        opportunities.sort(key=lambda x: x["apr"], reverse=True)
        
        return opportunities[0]
    
    async def deploy_capital(self, token: str, amount: float) -> Dict:
        """Deploy capital to yield source"""
        opportunity = self.find_best_yield(token, amount)
        
        if not opportunity:
            return {"success": False, "reason": "No yield opportunity found"}
        
        # In production, would execute deposit to yield protocol
        position_id = f"{opportunity['source']}_{token}_{datetime.now().timestamp()}"
        
        self.deployed_positions[position_id] = {
            "source": opportunity["source"],
            "token": token,
            "amount": amount,
            "apr": opportunity["apr"],
            "deposit_time": datetime.now()
        }
        
        logger.info(f"Deployed ${amount} to {opportunity['protocol']} at {opportunity['apr']*100}% APY")
        
        return {
            "success": True,
            "position_id": position_id,
            "protocol": opportunity["protocol"],
            "apr": opportunity["apr"]
        }
    
    async def harvest_yields(self) -> Dict:
        """Harvest accumulated yields"""
        total_yield = 0
        
        for position_id, position in self.deployed_positions.items():
            # Calculate accumulated yield
            days = (datetime.now() - position["deposit_time"]).total_seconds() / 86400
            yield_amount = position["amount"] * position["apr"] * (days / 365)
            total_yield += yield_amount
        
        logger.info(f"Harvested ${total_yield:.2f} in yields")
        
        return {
            "total_yield": total_yield,
            "positions": len(self.deployed_positions)
        }


class Dashboard:
    """
    Real-time trading dashboard
    """
    
    def __init__(self, portfolio_manager: PortfolioManager):
        self.portfolio = portfolio_manager
        self.alerts = []
    
    async def update(self):
        """Update dashboard with current state"""
        allocation = self.portfolio.get_current_allocation()
        metrics = self.portfolio.get_performance_metrics()
        
        # Build dashboard data
        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "portfolio_value": self.portfolio.current_capital,
            "allocation": allocation,
            "metrics": metrics,
            "alerts": self.alerts[-10:]  # Last 10 alerts
        }
        
        return dashboard
    
    def add_alert(self, message: str, level: str = "info"):
        """Add alert to dashboard"""
        self.alerts.append({
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "level": level  # info, warning, error, success
        })
    
    def print_dashboard(self):
        """Print dashboard to console"""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 60)
        print("   🚀 POWERSAVER TRADING DASHBOARD")
        print("=" * 60)
        
        metrics = self.portfolio.get_performance_metrics()
        
        if metrics:
            print(f"\n📊 Portfolio Value: ${metrics.get('current_value', 0):,.2f}")
            print(f"📈 Total Return: {metrics.get('total_return_percent', 0):.2f}%")
            print(f"📉 Volatility: {metrics.get('volatility_percent', 0):.2f}%")
            print(f"⚖️ Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        
        print("\n💰 Current Allocation:")
        allocation = self.portfolio.get_current_allocation()
        for symbol, data in allocation.items():
            bar_len = int(data["allocation_percent"] / 2)
            bar = "█" * bar_len
            print(f"  {symbol:8} {bar:25} {data['allocation_percent']:.1f}%")
        
        print("\n" + "=" * 60)


# Factory functions
def create_portfolio_manager(initial_capital: float) -> PortfolioManager:
    """Create portfolio manager"""
    return PortfolioManager(initial_capital)

def create_yield_optimizer() -> YieldOptimizer:
    """Create yield optimizer"""
    return YieldOptimizer()

def create_dashboard(portfolio: PortfolioManager) -> Dashboard:
    """Create dashboard"""
    return Dashboard(portfolio)
