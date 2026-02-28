"""
Risk Management Module for Autonomous Trading System
Comprehensive risk controls and monitoring
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import time
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskAlert:
    """Risk alert data"""
    alert_id: str
    risk_level: RiskLevel
    category: str
    message: str
    timestamp: float
    action_taken: str


@dataclass
class Position:
    """Trading position"""
    token: str
    amount: float
    entry_price: float
    current_price: float
    pnl: float
    pnl_percentage: float


class RiskManager:
    """Comprehensive risk management system"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.max_loan_amount = config.get("max_loan_amount", 100000)
        self.max_daily_loss = config.get("max_daily_loss", 10000)
        self.max_position_size = config.get("max_position_size", 50000)
        self.min_profit_threshold = config.get("min_profit_threshold", 0.005)
        self.max_concurrent_trades = config.get("max_concurrent_trades", 3)
        
        self.current_loan_amount = 0
        self.daily_loss = 0.0
        self.daily_profit = 0.0
        self.active_positions: List[Position] = []
        self.risk_alerts: List[RiskAlert] = []
        self.is_trading_allowed = True
        
        # Risk metrics
        self.total_trades = 0
        self.successful_trades = 0
        self.failed_trades = 0
    
    def validate_loan_request(self, token: str, amount: float) -> tuple[bool, str]:
        """Validate flash loan request against risk parameters"""
        
        # Check if trading is allowed
        if not self.is_trading_allowed:
            return False, "Trading temporarily disabled due to risk limits"
        
        # Check loan amount
        if amount > self.max_loan_amount:
            self._create_alert(
                RiskLevel.HIGH,
                "LOAN_LIMIT",
                f"Loan amount {amount} exceeds maximum {self.max_loan_amount}"
            )
            return False, f"Loan amount exceeds maximum limit"
        
        # Check daily loss limit
        if self.daily_loss > self.max_daily_loss:
            self._create_alert(
                RiskLevel.CRITICAL,
                "DAILY_LIMIT",
                f"Daily loss limit reached: {self.daily_loss}"
            )
            return False, "Daily loss limit exceeded"
        
        # Check concurrent trades
        if len(self.active_positions) >= self.max_concurrent_trades:
            return False, f"Maximum concurrent trades ({self.max_concurrent_trades}) reached"
        
        return True, "Loan request approved"
    
    def validate_profit_opportunity(self, profit_percentage: float) -> bool:
        """Validate if profit opportunity meets minimum threshold"""
        if profit_percentage < self.min_profit_threshold:
            logger.warning(f"Profit {profit_percentage:.2%} below threshold {self.min_profit_threshold:.2%}")
            return False
        return True
    
    def update_position(self, position: Position):
        """Update position with current price"""
        for i, pos in enumerate(self.active_positions):
            if pos.token == position.token:
                self.active_positions[i] = position
                return
        self.active_positions.append(position)
    
    def calculate_risk_metrics(self) -> Dict:
        """Calculate current risk metrics"""
        total_exposure = sum(pos.amount for pos in self.active_positions)
        total_pnl = sum(pos.pnl for pos in self.active_positions)
        win_rate = (self.successful_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        return {
            "total_exposure": total_exposure,
            "total_pnl": total_pnl,
            "active_positions": len(self.active_positions),
            "daily_loss": self.daily_loss,
            "daily_profit": self.daily_profit,
            "win_rate": win_rate,
            "trading_allowed": self.is_trading_allowed
        }
    
    def _create_alert(
        self,
        risk_level: RiskLevel,
        category: str,
        message: str,
        action_taken: str = "None"
    ):
        """Create risk alert"""
        alert = RiskAlert(
            alert_id=f"ALERT_{int(time.time())}",
            risk_level=risk_level,
            category=category,
            message=message,
            timestamp=time.time(),
            action_taken=action_taken
        )
        self.risk_alerts.append(alert)
        
        logger.warning(f"[{risk_level.value.upper()}] {category}: {message}")
        
        # Auto-disable trading for critical risks
        if risk_level == RiskLevel.CRITICAL:
            self.is_trading_allowed = False
            logger.critical("Trading disabled due to critical risk")
    
    def get_risk_status(self) -> Dict:
        """Get current risk status"""
        metrics = self.calculate_risk_metrics()
        
        # Determine overall risk level
        if metrics["daily_loss"] > self.max_daily_loss * 0.8:
            overall_risk = RiskLevel.CRITICAL
        elif metrics["daily_loss"] > self.max_daily_loss * 0.5:
            overall_risk = RiskLevel.HIGH
        elif metrics["daily_loss"] > self.max_daily_loss * 0.2:
            overall_risk = RiskLevel.MEDIUM
        else:
            overall_risk = RiskLevel.LOW
        
        return {
            "overall_risk": overall_risk.value,
            "metrics": metrics,
            "recent_alerts": [
                {
                    "id": alert.alert_id,
                    "level": alert.risk_level.value,
                    "category": alert.category,
                    "message": alert.message
                }
                for alert in self.risk_alerts[-10:]  # Last 10 alerts
            ],
            "active_positions": [
                {
                    "token": pos.token,
                    "amount": pos.amount,
                    "pnl": pos.pnl,
                    "pnl_percentage": pos.pnl_percentage
                }
                for pos in self.active_positions
            ]
        }
    
    def reset_daily_stats(self):
        """Reset daily statistics"""
        self.daily_loss = 0.0
        self.daily_profit = 0.0
        logger.info("Daily statistics reset")
    
    def record_trade_result(self, successful: bool, profit: float):
        """Record trade result"""
        self.total_trades += 1
        
        if successful:
            self.successful_trades += 1
            self.daily_profit += profit
        else:
            self.failed_trades += 1
            self.daily_loss += abs(profit)
    
    def enable_trading(self):
        """Manually enable trading"""
        self.is_trading_allowed = True
        logger.info("Trading manually enabled")
    
    def disable_trading(self, reason: str):
        """Manually disable trading"""
        self.is_trading_allowed = False
        logger.warning(f"Trading disabled: {reason}")


class ProfitTracker:
    """Track and analyze trading profits"""
    
    def __init__(self):
        self.trades: List[Dict] = []
        self.daily_profits: Dict[str, float] = {}
        self.total_profit = 0.0
    
    def record_trade(self, trade_data: Dict):
        """Record trade data"""
        trade_id = f"TRADE_{len(self.trades) + 1}"
        trade_data["trade_id"] = trade_id
        trade_data["timestamp"] = time.time()
        
        self.trades.append(trade_data)
        self.total_profit += trade_data.get("profit", 0)
        
        # Track daily profit
        date = time.strftime("%Y-%m-%d")
        self.daily_profits[date] = self.daily_profits.get(date, 0) + trade_data.get("profit", 0)
    
    def get_profit_analytics(self) -> Dict:
        """Get profit analytics"""
        if not self.trades:
            return {"message": "No trades recorded"}
        
        profits = [t.get("profit", 0) for t in self.trades]
        avg_profit = sum(profits) / len(profits)
        max_profit = max(profits)
        min_profit = min(profits)
        
        return {
            "total_profit": self.total_profit,
            "total_trades": len(self.trades),
            "average_profit": avg_profit,
            "max_profit": max_profit,
            "min_profit": min_profit,
            "daily_profits": self.daily_profits,
            "recent_trades": self.trades[-20:]  # Last 20 trades
        }


class GasOptimizer:
    """Optimize gas costs for transactions"""
    
    def __init__(self):
        self.gas_prices: List[float] = []
        self.avg_gas_price = 0.0
    
    def update_gas_price(self, gas_price: float):
        """Update current gas price"""
        self.gas_prices.append(gas_price)
        if len(self.gas_prices) > 100:
            self.gas_prices = self.gas_prices[-100:]
        self.avg_gas_price = sum(self.gas_prices) / len(self.gas_prices)
    
    def should_execute(self, estimated_profit: float, gas_cost: float) -> bool:
        """Determine if transaction should execute based on gas costs"""
        return estimated_profit > (gas_cost * 2)  # Require 2x profit over gas cost
    
    def get_optimal_gas_price(self) -> float:
        """Get optimal gas price for execution"""
        # Return slightly above average for faster execution
        return self.avg_gas_price * 1.1


async def main():
    """Test risk management system"""
    config = {
        "max_loan_amount": 100000,
        "max_daily_loss": 10000,
        "max_position_size": 50000,
        "min_profit_threshold": 0.005,
        "max_concurrent_trades": 3
    }
    
    risk_manager = RiskManager(config)
    profit_tracker = ProfitTracker()
    gas_optimizer = GasOptimizer()
    
    # Test loan validation
    valid, message = risk_manager.validate_loan_request("ETH", 50000)
    print(f"Loan validation: {valid}, {message}")
    
    # Test profit validation
    has_profit = risk_manager.validate_profit_opportunity(0.01)
    print(f"Profit opportunity valid: {has_profit}")
    
    # Record some trades
    for i in range(5):
        profit = 100 if i % 2 == 0 else -50
        risk_manager.record_trade_result(successful=profit > 0, profit=profit)
    
    # Get analytics
    analytics = profit_tracker.get_profit_analytics()
    print(f"Profit Analytics: {json.dumps(analytics, indent=2)}")
    
    # Get risk status
    risk_status = risk_manager.get_risk_status()
    print(f"Risk Status: {json.dumps(risk_status, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
