"""
Advanced Backtesting System
Test strategies on historical data before deploying to production
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import csv
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Backtest configuration"""
    start_date: str  # "2023-01-01"
    end_date: str    # "2023-12-31"
    initial_capital: float = 10000
    commission: float = 0.003  # 0.3% per trade
    slippage: float = 0.001  # 0.1% slippage


@dataclass
class BacktestResult:
    """Backtest results"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_profit: float
    total_return: float  # percentage
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    trades: List[Dict] = field(default_factory=list)


@dataclass
class Trade:
    """Historical trade record"""
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_percent: float
    strategy: str
    reason: str


class HistoricalDataFetcher:
    """
    Fetches historical price data for backtesting
    """
    
    def __init__(self):
        self.cache = {}
    
    async def get_historical_prices(
        self,
        token: str,
        start_date: str,
        end_date: str,
        interval: str = "1h"
    ) -> List[Dict]:
        """
        Get historical OHLCV data
        In production: fetch from CoinGecko, CoinMetrics, etc.
        """
        
        # Check cache
        cache_key = f"{token}_{start_date}_{end_date}_{interval}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Generate synthetic historical data for testing
        # In production, replace with real API calls
        data = self._generate_synthetic_data(token, start_date, end_date, interval)
        
        self.cache[cache_key] = data
        return data
    
    def _generate_synthetic_data(
        self,
        token: str,
        start_date: str,
        end_date: str,
        interval: str
    ) -> List[Dict]:
        """Generate synthetic data for testing"""
        import random
        
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        
        # Base prices
        base_prices = {
            "ETH": 1800,
            "BTC": 42000,
            "USDC": 1,
            "USDT": 1
        }
        
        base_price = base_prices.get(token.upper(), 1000)
        
        # Generate data points
        interval_hours = int(interval.rstrip('h')) if interval.endswith('h') else 1
        data = []
        
        current = start
        price = base_price
        
        while current <= end:
            # Random walk with trend
            change = random.gauss(0, 0.02)  # 2% std dev
            price *= (1 + change)
            
            # Generate OHLCV
            high = price * (1 + abs(random.gauss(0, 0.01)))
            low = price * (1 - abs(random.gauss(0, 0.01)))
            open_price = price * (1 + random.gauss(0, 0.005))
            close = price
            volume = random.uniform(1000000, 10000000)
            
            data.append({
                "timestamp": current.timestamp(),
                "datetime": current.isoformat(),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume
            })
            
            current += timedelta(hours=interval_hours)
        
        return data


class Backtester:
    """
    Advanced backtesting engine
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.data_fetcher = HistoricalDataFetcher()
        
        # State
        self.capital = config.initial_capital
        self.initial_capital = config.initial_capital
        self.trades: List[Trade] = []
        self.equity_curve = []
        
        # Metrics
        self.peak_capital = config.initial_capital
        self.drawdowns = []
    
    async def run_backtest(
        self,
        strategy: Callable,
        token: str,
        timeframe: str = "1h"
    ) -> BacktestResult:
        """
        Run backtest with given strategy
        """
        logger.info(f"Starting backtest for {token}")
        
        # Get historical data
        prices = await self.data_fetcher.get_historical_prices(
            token,
            self.config.start_date,
            self.config.end_date,
            timeframe
        )
        
        logger.info(f"Loaded {len(prices)} data points")
        
        # Run strategy on historical data
        position = None
        
        for i, candle in enumerate(prices[20:], start=20):  # Skip first 20 for indicators
            # Get lookback data
            lookback = prices[:i]
            
            # Generate signal
            signal = await strategy(lookback)
            
            if signal and not position:
                # Enter position
                entry_price = candle["close"] * (1 + self.config.slippage)
                
                position = {
                    "entry_time": datetime.fromisoformat(candle["datetime"]),
                    "entry_price": entry_price,
                    "size": self._calculate_position_size(entry_price),
                    "stop_loss": signal.get("stop_loss"),
                    "take_profit": signal.get("take_profit")
                }
            
            elif position:
                # Check exit conditions
                current_price = candle["close"]
                
                # Check stop loss
                if position["stop_loss"] and current_price <= position["stop_loss"]:
                    self._close_trade(position, current_price, "stop_loss")
                    position = None
                
                # Check take profit
                elif position["take_profit"] and current_price >= position["take_profit"]:
                    self._close_trade(position, current_price, "take_profit")
                    position = None
                
                # Check time-based exit
                elif (datetime.fromisoformat(candle["datetime"]) - position["entry_time"]).total_seconds() > 7200:
                    self._close_trade(position, current_price, "time_exit")
                    position = None
        
        # Close any open position
        if position:
            self._close_trade(position, prices[-1]["close"], "end_of_backtest")
        
        # Calculate final metrics
        return self._calculate_results()
    
    def _calculate_position_size(self, entry_price: float) -> float:
        """Calculate position size based on risk"""
        # Fixed fraction of capital
        return self.capital * 0.1 / entry_price
    
    def _close_trade(self, position: Dict, exit_price: float, reason: str):
        """Close a trade and record it"""
        # Apply slippage on exit
        exit_price = exit_price * (1 - self.config.slippage)
        
        # Calculate PnL
        pnl = (exit_price - position["entry_price"]) * position["size"]
        pnl_percent = (exit_price - position["entry_price"]) / position["entry_price"]
        
        # Subtract commission
        commission = position["entry_price"] * position["size"] * self.config.commission
        commission += exit_price * position["size"] * self.config.commission
        pnl -= commission
        
        # Update capital
        self.capital += pnl
        
        # Record trade
        trade = Trade(
            entry_time=position["entry_time"],
            exit_time=datetime.now(),
            entry_price=position["entry_price"],
            exit_price=exit_price,
            size=position["size"],
            pnl=pnl,
            pnl_percent=pnl_percent,
            strategy="ml_strategy",
            reason=reason
        )
        self.trades.append(trade)
        
        # Update equity curve
        self.equity_curve.append({
            "timestamp": trade.exit_time.timestamp(),
            "capital": self.capital
        })
        
        # Update peak and drawdown
        if self.capital > self.peak_capital:
            self.peak_capital = self.capital
        
        drawdown = (self.peak_capital - self.capital) / self.peak_capital
        self.drawdowns.append(drawdown)
        
        logger.info(f"Trade closed: {reason} | PnL: ${pnl:.2f} | Capital: ${self.capital:.2f}")
    
    def _calculate_results(self) -> BacktestResult:
        """Calculate final backtest results"""
        if not self.trades:
            return BacktestResult(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                total_profit=0,
                total_return=0,
                max_drawdown=0,
                sharpe_ratio=0,
                win_rate=0,
                avg_win=0,
                avg_loss=0,
                profit_factor=0
            )
        
        winning = [t for t in self.trades if t.pnl > 0]
        losing = [t for t in self.trades if t.pnl <= 0]
        
        total_profit = sum(t.pnl for t in self.trades)
        total_return = (self.capital - self.initial_capital) / self.initial_capital * 100
        
        max_drawdown = max(self.drawdowns) if self.drawdowns else 0
        
        # Sharpe ratio (simplified)
        returns = [t.pnl_percent for t in self.trades]
        avg_return = sum(returns) / len(returns)
        std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
        sharpe_ratio = (avg_return / std_return * (252 ** 0.5)) if std_return > 0 else 0
        
        # Profit factor
        gross_wins = sum(t.pnl for t in winning) if winning else 0
        gross_losses = abs(sum(t.pnl for t in losing)) if losing else 1
        profit_factor = gross_wins / gross_losses if gross_losses > 0 else 0
        
        return BacktestResult(
            total_trades=len(self.trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            total_profit=total_profit,
            total_return=total_return,
            max_drawdown=max_drawdown * 100,
            sharpe_ratio=sharpe_ratio,
            win_rate=len(winning) / len(self.trades) * 100,
            avg_win=sum(t.pnl for t in winning) / len(winning) if winning else 0,
            avg_loss=sum(t.pnl for t in losing) / len(losing) if losing else 0,
            profit_factor=profit_factor,
            trades=[{
                "entry": t.entry_time.isoformat(),
                "exit": t.exit_time.isoformat(),
                "pnl": t.pnl,
                "pnl_percent": t.pnl_percent * 100
            } for t in self.trades]
        )
    
    def export_results(self, filepath: str):
        """Export results to CSV"""
        result = self._calculate_results()
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Entry", "Exit", "Entry Price", "Exit Price", 
                "Size", "PnL", "PnL %", "Reason"
            ])
            
            for trade in self.trades:
                writer.writerow([
                    trade.entry_time.isoformat(),
                    trade.exit_time.isoformat(),
                    trade.entry_price,
                    trade.exit_price,
                    trade.size,
                    trade.pnl,
                    trade.pnl_percent * 100,
                    trade.reason
                ])
        
        logger.info(f"Results exported to {filepath}")


# Strategy examples
async def moving_average_crossover_strategy(prices: List[Dict]) -> Optional[Dict]:
    """Example: Moving average crossover strategy"""
    if len(prices) < 50:
        return None
    
    # Calculate SMAs
    sma20 = sum(p["close"] for p in prices[-20:]) / 20
    sma50 = sum(p["close"] for p in prices[-50:]) / 50
    
    current_price = prices[-1]["close"]
    
    # Golden cross
    if sma20 > sma50 and prices[-2]["close"] <= prices[-2]["close"]:
        return {
            "action": "buy",
            "stop_loss": current_price * 0.95,
            "take_profit": current_price * 1.10
        }
    
    # Death cross
    elif sma20 < sma50:
        return {
            "action": "sell",
            "stop_loss": current_price * 1.05,
            "take_profit": current_price * 0.90
        }
    
    return None


# Factory
def create_backtester(
    start_date: str,
    end_date: str,
    initial_capital: float = 10000
) -> Backtester:
    """Create backtester"""
    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital
    )
    return Backtester(config)
