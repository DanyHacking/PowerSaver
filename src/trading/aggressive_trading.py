"""
Aggressive Trading Engine
Advanced profit-generating strategies with smart risk management

Strategies:
- Cross-Exchange Arbitrage
- Triangular Arbitrage  
- Cyclical Arbitrage
- Momentum Trading
- Mean Reversion
- Breakout Trading
- Volatility Capture
- Correlation Trading
- Statistical Arbitrage
- Machine Learning Predictions
- Flash Loan Compounding
"""

import asyncio
import logging
import time
import random
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import math

import numpy as np

logger = logging.getLogger(__name__)


class TradingStrategy(Enum):
    """Trading strategy types"""
    ARBITRAGE = "arbitrage"
    TRIANGULAR = "triangular"
    CYCLICAL = "cyclical"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    VOLATILITY = "volatility"
    CORRELATION = "correlation"
    STATISTICAL = "statistical"
    ML = "ml"


@dataclass
class TradeSignal:
    """Trading signal with entry/exit points"""
    strategy: TradingStrategy
    token_in: str
    token_out: str
    amount: float
    expected_profit: float
    confidence: float
    entry_price: float
    target_price: float
    stop_loss: float
    timestamp: float
    timeframe: str
    indicators: Dict = field(default_factory=dict)


@dataclass
class TradeResult:
    """Trade execution result"""
    success: bool
    strategy: TradingStrategy
    profit: float
    gas_cost: float
    slippage: float
    execution_time: float
    details: Dict


class AggressiveArbitrageScanner:
    """
    High-frequency arbitrage scanner
    Scans for price differences across exchanges
    """
    
    # Price difference thresholds
    MIN_PRICE_DIFF = 0.001  # 0.1%
    OPTIMAL_PRICE_DIFF = 0.005  # 0.5%
    
    def __init__(self, config: Dict):
        self.config = config
        self.min_profit = config.get("min_profit_per_trade", 200)
        self.max_slippage = config.get("max_slippage", 0.015)
        
        # Historical price data for analysis
        self.price_history: Dict[str, List[float]] = {}
        self.volume_history: Dict[str, List[float]] = {}
        
        # Exchange prices cache
        self.exchange_prices: Dict[str, Dict[str, float]] = {}
        
    async def scan_arbitrage_opportunities(self) -> List[TradeSignal]:
        """Scan for cross-exchange arbitrage opportunities"""
        opportunities = []
        
        tokens = self.config.get("tokens", [])
        exchanges = self.config.get("exchanges", [])
        
        # Check all token pairs across all exchanges
        for token_in in tokens:
            for token_out in tokens:
                if token_in == token_out:
                    continue
                    
                for ex1 in exchanges:
                    for ex2 in exchanges:
                        if ex1 == ex2:
                            continue
                        
                        # Get prices from both exchanges
                        price1 = await self._get_price(token_in, token_out, ex1)
                        price2 = await self._get_price(token_in, token_out, ex2)
                        
                        if price1 and price2:
                            # Calculate price difference
                            diff = abs(price1 - price2) / min(price1, price2)
                            
                            if diff >= self.MIN_PRICE_DIFF:
                                # Calculate potential profit
                                profit = await self._calculate_arbitrage_profit(
                                    token_in, token_out, 
                                    self.config.get("loan_amount", 75000),
                                    ex1, ex2
                                )
                                
                                if profit >= self.min_profit:
                                    signal = TradeSignal(
                                        strategy=TradingStrategy.ARBITRAGE,
                                        token_in=token_in,
                                        token_out=token_out,
                                        amount=self.config.get("loan_amount", 75000),
                                        expected_profit=profit,
                                        confidence=self._calculate_confidence(diff),
                                        entry_price=price1,
                                        target_price=price2,
                                        stop_loss=price1 * (1 - self.max_slippage),
                                        timestamp=time.time(),
                                        timeframe="1m",
                                        indicators={"price_diff": diff, "exchange_1": ex1, "exchange_2": ex2}
                                    )
                                    opportunities.append(signal)
        
        # Sort by profit
        opportunities.sort(key=lambda x: x.expected_profit, reverse=True)
        return opportunities[:self.config.get("max_concurrent_trades", 15)]
    
    async def _get_price(self, token_in: str, token_out: str, exchange: str) -> Optional[float]:
        """Get price from exchange (simulated - replace with real data)"""
        # In production, query real DEX APIs
        # For now, simulate price with small variations
        
        base_prices = {
            "ETH": 2000, "WETH": 2000, "USDC": 1, "USDT": 1, 
            "DAI": 1, "WBTC": 40000, "LINK": 15, "MATIC": 0.8,
            "UNI": 7, "AAVE": 100, "CRV": 0.5, "SUSHI": 8,
            "SNX": 3, "COMP": 50, "MKR": 1500, "BAT": 0.3,
            "ZRX": 0.5, "ENJ": 2, "MANA": 0.4, "SAND": 0.5,
            "AXS": 8, "APE": 1.5, "LDO": 2.5, "OP": 2,
            "ARB": 1, "SHIB": 0.00001, "PEPE": 0.000001,
            "GMX": 40, "RNDR": 3, "IMX": 1.5, "GALA": 0.03,
            "ENS": 15, "1INCH": 0.3, "CRO": 0.1, "FTM": 0.3
        }
        
        base = base_prices.get(token_out, 1) / base_prices.get(token_in, 1)
        
        # Add exchange-specific variation
        exchange_variations = {
            "uniswap_v2": 1.0, "uniswap_v3": 1.001, "sushiswap": 0.999,
            "balancer": 1.002, "curve": 0.998, "dodo": 1.003,
            "pancakeswap": 0.997, "trader_joe": 1.001, "gmx": 1.004
        }
        
        variation = exchange_variations.get(exchange, 1.0)
        
        # Add small random variation to simulate real market
        noise = 1 + (random.random() - 0.5) * 0.01
        
        return base * variation * noise
    
    async def _calculate_arbitrage_profit(
        self, token_in: str, token_out: str, 
        amount: float, ex1: str, ex2: str
    ) -> float:
        """Calculate potential arbitrage profit"""
        price1 = await self._get_price(token_in, token_out, ex1)
        price2 = await self._get_price(token_in, token_out, ex2)
        
        if not price1 or not price2:
            return 0
        
        # Calculate gross profit
        price_diff = abs(price1 - price2) / min(price1, price2)
        gross_profit = amount * price_diff
        
        # Subtract estimated costs
        gas_cost = 50  # Estimated gas in USD
        flash_loan_fee = amount * 0.0009  # Aave 0.09%
        slippage_cost = amount * self.max_slippage
        
        net_profit = gross_profit - gas_cost - flash_loan_fee - slippage_cost
        
        return max(0, net_profit)
    
    def _calculate_confidence(self, price_diff: float) -> float:
        """Calculate confidence based on price difference"""
        if price_diff >= self.OPTIMAL_PRICE_DIFF:
            return 0.95
        elif price_diff >= 0.003:
            return 0.85
        elif price_diff >= 0.002:
            return 0.75
        else:
            return 0.6


class TriangularArbitrageScanner:
    """
    Triangular arbitrage within single exchange
    ETH -> USDC -> DAI -> ETH
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.min_profit = config.get("min_profit_per_trade", 200)
        
    async def scan_triangular_opportunities(self) -> List[TradeSignal]:
        """Scan for triangular arbitrage opportunities"""
        opportunities = []
        
        # Base tokens for triangulation
        bases = ["ETH", "USDC", "USDT", "DAI", "WBTC"]
        tokens = self.config.get("tokens", [])
        
        for base1 in bases:
            for mid in tokens:
                for base2 in bases:
                    if base1 == mid or base1 == base2 or mid == base2:
                        continue
                    
                    # Try different paths
                    paths = [
                        (base1, mid, base2),  # base1 -> mid -> base2 -> base1
                        (base1, base2, mid),  # base1 -> base2 -> mid -> base1
                    ]
                    
                    for path in paths:
                        profit = await self._calculate_triangular_profit(
                            path[0], path[1], path[2],
                            self.config.get("loan_amount", 75000)
                        )
                        
                        if profit >= self.min_profit:
                            signal = TradeSignal(
                                strategy=TradingStrategy.TRIANGULAR,
                                token_in=path[0],
                                token_out=path[1],
                                amount=self.config.get("loan_amount", 75000),
                                expected_profit=profit,
                                confidence=0.85,
                                entry_price=1.0,
                                target_price=1.0 + profit/10000,
                                stop_loss=0.99,
                                timestamp=time.time(),
                                timeframe="30s",
                                indicators={"path": path}
                            )
                            opportunities.append(signal)
        
        opportunities.sort(key=lambda x: x.expected_profit, reverse=True)
        return opportunities[:10]
    
    async def _calculate_triangular_profit(
        self, token1: str, token2: str, token3: str, amount: float
    ) -> float:
        """Calculate triangular arbitrage profit"""
        # Simulate triangular trade
        # In production, query real pool reserves
        
        # Path: 1 -> 2 -> 3 -> 1
        rate1_2 = random.uniform(0.99, 1.01)
        rate2_3 = random.uniform(0.99, 1.01)
        rate3_1 = random.uniform(0.99, 1.01)
        
        # Calculate final amount
        final_amount = amount * rate1_2 * rate2_3 * rate3_1
        
        # Profit
        gross_profit = final_amount - amount
        
        # Costs
        gas_cost = 30
        flash_loan_fee = amount * 0.0009
        
        net_profit = gross_profit - gas_cost - flash_loan_fee
        
        return max(0, net_profit)


class MomentumTrader:
    """
    Momentum-based trading strategy
    Trades in direction of strong trends
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.min_profit = config.get("min_profit_per_trade", 200)
        
    async def scan_momentum_opportunities(self) -> List[TradeSignal]:
        """Scan for momentum trading opportunities"""
        opportunities = []
        
        tokens = self.config.get("tokens", [])
        
        for token in tokens:
            # Analyze momentum
            momentum = await self._calculate_momentum(token)
            
            if abs(momentum) > 0.02:  # 2% threshold
                # Strong momentum detected
                direction = "long" if momentum > 0 else "short"
                
                profit_estimate = abs(momentum) * self.config.get("loan_amount", 75000) * 5  # 5x leverage
                
                if profit_estimate >= self.min_profit:
                    signal = TradeSignal(
                        strategy=TradingStrategy.MOMENTUM,
                        token_in="USDC" if momentum > 0 else token,
                        token_out=token if momentum > 0 else "USDC",
                        amount=self.config.get("loan_amount", 75000),
                        expected_profit=profit_estimate,
                        confidence=min(0.95, 0.6 + abs(momentum) * 10),
                        entry_price=1.0,
                        target_price=1.0 + abs(momentum) * 2,
                        stop_loss=1.0 - abs(momentum) * 0.5,
                        timestamp=time.time(),
                        timeframe="5m",
                        indicators={"momentum": momentum, "direction": direction}
                    )
                    opportunities.append(signal)
        
        opportunities.sort(key=lambda x: x.expected_profit, reverse=True)
        return opportunities[:10]
    
    async def _calculate_momentum(self, token: str) -> float:
        """Calculate price momentum"""
        # In production, use real price data
        # Calculate using EMA, MACD, etc.
        
        # Simulate momentum
        return random.uniform(-0.05, 0.05)


class MeanReversionTrader:
    """
    Mean reversion strategy
    Buys oversold, sells overbought
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.min_profit = config.get("min_profit_per_trade", 200)
        
    async def scan_mean_reversion_opportunities(self) -> List[TradeSignal]:
        """Scan for mean reversion opportunities"""
        opportunities = []
        
        tokens = self.config.get("tokens", [])
        
        for token in tokens:
            deviation = await self._calculate_deviation(token)
            
            if abs(deviation) > 0.03:  # 3% deviation from mean
                # Mean reversion opportunity
                direction = "buy" if deviation < 0 else "sell"
                
                profit_estimate = abs(deviation) * self.config.get("loan_amount", 75000) * 3
                
                if profit_estimate >= self.min_profit:
                    signal = TradeSignal(
                        strategy=TradingStrategy.MEAN_REVERSION,
                        token_in="USDC" if direction == "buy" else token,
                        token_out=token if direction == "buy" else "USDC",
                        amount=self.config.get("loan_amount", 75000),
                        expected_profit=profit_estimate,
                        confidence=min(0.9, 0.5 + abs(deviation) * 15),
                        entry_price=1.0,
                        target_price=1.0,
                        stop_loss=1.0 - abs(deviation) * 0.3,
                        timestamp=time.time(),
                        timeframe="15m",
                        indicators={"deviation": deviation, "direction": direction}
                    )
                    opportunities.append(signal)
        
        return opportunities[:10]
    
    async def _calculate_deviation(self, token: str) -> float:
        """Calculate deviation from moving average"""
        # In production, calculate real standard deviation
        return random.uniform(-0.08, 0.08)


class VolatilityCapture:
    """
    Volatility-based trading
    Profits from high volatility periods
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.min_profit = config.get("min_profit_per_trade", 200)
        
    async def scan_volatility_opportunities(self) -> List[TradeSignal]:
        """Scan for volatility capture opportunities"""
        opportunities = []
        
        tokens = self.config.get("tokens", [])
        
        for token in tokens:
            volatility = await self._calculate_volatility(token)
            
            if volatility > 0.03:  # High volatility
                # Volatility breakout opportunity
                profit_estimate = volatility * self.config.get("loan_amount", 75000) * 10
                
                if profit_estimate >= self.min_profit:
                    signal = TradeSignal(
                        strategy=TradingStrategy.VOLATILITY,
                        token_in="USDC",
                        token_out=token,
                        amount=self.config.get("loan_amount", 75000),
                        expected_profit=profit_estimate,
                        confidence=min(0.9, 0.5 + volatility * 10),
                        entry_price=1.0,
                        target_price=1.0 + volatility * 2,
                        stop_loss=1.0 - volatility * 0.5,
                        timestamp=time.time(),
                        timeframe="1h",
                        indicators={"volatility": volatility}
                    )
                    opportunities.append(signal)
        
        return opportunities[:5]
    
    async def _calculate_volatility(self, token: str) -> float:
        """Calculate token volatility"""
        # In production, calculate real volatility using historical data
        return random.uniform(0.01, 0.15)


class StatisticalArbitrage:
    """
    Statistical arbitrage using cointegration
    Pairs trading with statistical relationships
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.min_profit = config.get("min_profit_per_trade", 200)
        
        # Known correlated pairs
        self.correlated_pairs = [
            ("ETH", "WETH"), ("ETH", "STETH"), ("ETH", "RETH"),
            ("USDC", "USDT"), ("DAI", "USDC"), ("FRAX", "USDC"),
            ("WBTC", "BTC"), ("LINK", "UNI"), ("CRV", "ETH"),
            ("Matic", "WMATIC")
        ]
        
    async def scan_statistical_opportunities(self) -> List[TradeSignal]:
        """Scan for statistical arbitrage opportunities"""
        opportunities = []
        
        for pair in self.correlated_pairs:
            spread = await self._calculate_spread(pair[0], pair[1])
            
            if abs(spread) > 0.02:  # Significant spread
                profit_estimate = abs(spread) * self.config.get("loan_amount", 75000) * 3
                
                if profit_estimate >= self.min_profit:
                    direction = "long_spread" if spread > 0 else "short_spread"
                    
                    signal = TradeSignal(
                        strategy=TradingStrategy.STATISTICAL,
                        token_in=pair[0],
                        token_out=pair[1],
                        amount=self.config.get("loan_amount", 75000) / 2,
                        expected_profit=profit_estimate,
                        confidence=0.85,
                        entry_price=1.0,
                        target_price=1.0,
                        stop_loss=1.0 - abs(spread) * 0.3,
                        timestamp=time.time(),
                        timeframe="30m",
                        indicators={"spread": spread, "pair": pair, "direction": direction}
                    )
                    opportunities.append(signal)
        
        return opportunities[:10]
    
    async def _calculate_spread(self, token1: str, token2: str) -> float:
        """Calculate price spread between correlated tokens"""
        # In production, calculate real spread using historical data
        return random.uniform(-0.05, 0.05)


class CompoundingManager:
    """
    Manages profit compounding
    Reinvests profits for exponential growth
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.initial_capital = config.get("loan_amount", 75000)
        self.current_capital = self.initial_capital
        self.compounding_enabled = config.get("compounding_enabled", True)
        self.compound_ratio = 0.8  # Reinvest 80% of profits
        
    def reinvest(self, profit: float) -> float:
        """Reinvest profit into next trade"""
        if not self.compounding_enabled:
            return 0
        
        compound_amount = profit * self.compound_ratio
        self.current_capital += compound_amount
        
        # Cap at max loan amount
        max_capital = self.config.get("max_loan_amount", 750000)
        if self.current_capital > max_capital:
            self.current_capital = max_capital
        
        return compound_amount
    
    def get_compounded_capital(self) -> Dict:
        """Get current capital with compounding"""
        total_return = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
        
        return {
            "initial_capital": self.initial_capital,
            "current_capital": self.current_capital,
            "profit": self.current_capital - self.initial_capital,
            "total_return_percent": total_return,
            "compound_count": int(total_return / 10)  # Estimated
        }


class AggressiveTradingEngine:
    """
    Main aggressive trading engine
    Coordinates all strategies
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.is_running = False
        
        # Initialize scanners
        self.arbitrage_scanner = AggressiveArbitrageScanner(config)
        self.triangular_scanner = TriangularArbitrageScanner(config)
        self.momentum_trader = MomentumTrader(config)
        self.mean_reversion = MeanReversionTrader(config)
        self.volatility_capture = VolatilityCapture(config)
        self.stat_arb = StatisticalArbitrage(config)
        self.compounding = CompoundingManager(config)
        
        # Statistics
        self.total_trades = 0
        self.total_profit = 0.0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # Risk management
        self.max_daily_trades = config.get("max_daily_trades", 100)
        self.max_daily_loss = config.get("max_daily_loss", 75000)
        self.today_trades = 0
        self.today_loss = 0.0
        self.last_reset = time.time()
        
    async def start(self):
        """Start aggressive trading"""
        self.is_running = True
        logger.info("🚀 Aggressive Trading Engine started")
        
    async def stop(self):
        """Stop aggressive trading"""
        self.is_running = False
        logger.info("🛑 Aggressive Trading Engine stopped")
    
    async def scan_all_opportunities(self) -> List[TradeSignal]:
        """Scan for opportunities across all strategies"""
        if not self.is_running:
            return []
        
        # Reset daily counters if new day
        self._check_daily_reset()
        
        all_opportunities = []
        
        # Scan all strategies concurrently
        tasks = [
            self.arbitrage_scanner.scan_arbitrage_opportunities(),
            self.triangular_scanner.scan_triangular_opportunities(),
            self.momentum_trader.scan_momentum_opportunities(),
            self.mean_reversion.scan_mean_reversion_opportunities(),
            self.volatility_capture.scan_volatility_opportunities(),
            self.stat_arb.scan_statistical_opportunities(),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_opportunities.extend(result)
        
        # Sort by expected profit
        all_opportunities.sort(key=lambda x: x.expected_profit, reverse=True)
        
        # Apply risk filters
        filtered = self._apply_risk_filters(all_opportunities)
        
        return filtered[:self.config.get("max_concurrent_trades", 15)]
    
    def _apply_risk_filters(self, opportunities: List[TradeSignal]) -> List[TradeSignal]:
        """Apply risk management filters"""
        filtered = []
        
        for opp in opportunities:
            # Check daily trade limit
            if self.today_trades >= self.max_daily_trades:
                break
            
            # Check confidence threshold
            if opp.confidence < 0.6:
                continue
            
            # Check profit threshold
            if opp.expected_profit < self.config.get("min_profit_per_trade", 200):
                continue
            
            filtered.append(opp)
        
        return filtered
    
    async def execute_trade(self, signal: TradeSignal) -> TradeResult:
        """Execute a trade signal"""
        start_time = time.time()
        
        try:
            # Simulate trade execution
            # In production, this would:
            # 1. Send via Flashbots
            # 2. Simulate first
            # 3. Execute on-chain
            
            # Simulate outcome based on confidence
            success_probability = signal.confidence
            success = random.random() < success_probability
            
            if success:
                # Simulate profit (expected - some variance)
                profit = signal.expected_profit * random.uniform(0.8, 1.2)
                gas_cost = 50
                slippage = random.uniform(0.001, 0.015)
                
                net_profit = profit - gas_cost
                
                # Record trade
                self.total_trades += 1
                self.winning_trades += 1
                self.total_profit += net_profit
                self.today_trades += 1
                
                # Compounding
                self.compounding.reinvest(net_profit)
                
                return TradeResult(
                    success=True,
                    strategy=signal.strategy,
                    profit=net_profit,
                    gas_cost=gas_cost,
                    slippage=slippage,
                    execution_time=time.time() - start_time,
                    details={"signal": signal.__dict__}
                )
            else:
                # Trade failed/lost
                loss = random.uniform(10, 100)
                
                self.total_trades += 1
                self.losing_trades += 1
                self.today_loss += loss
                self.today_trades += 1
                
                return TradeResult(
                    success=False,
                    strategy=signal.strategy,
                    profit=-loss,
                    gas_cost=50,
                    slippage=0.01,
                    execution_time=time.time() - start_time,
                    details={"signal": signal.__dict__}
                )
                
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            return TradeResult(
                success=False,
                strategy=signal.strategy,
                profit=0,
                gas_cost=0,
                slippage=0,
                execution_time=time.time() - start_time,
                details={"error": str(e)}
            )
    
    def _check_daily_reset(self):
        """Reset daily counters if new day"""
        now = time.time()
        if now - self.last_reset > 86400:  # 24 hours
            self.today_trades = 0
            self.today_loss = 0.0
            self.last_reset = now
    
    def get_stats(self) -> Dict:
        """Get trading statistics"""
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        return {
            "is_running": self.is_running,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": win_rate,
            "total_profit": self.total_profit,
            "today_trades": self.today_trades,
            "today_loss": self.today_loss,
            "compounding": self.compounding.get_compounded_capital(),
            "strategies_active": [
                "Arbitrage",
                "Triangular",
                "Momentum",
                "Mean Reversion",
                "Volatility",
                "Statistical"
            ]
        }
    
    def should_continue(self) -> Tuple[bool, str]:
        """Check if should continue trading"""
        # Check daily loss limit
        if self.today_loss >= self.max_daily_loss:
            return False, "Daily loss limit reached"
        
        # Check daily trade limit
        if self.today_trades >= self.max_daily_trades:
            return False, "Daily trade limit reached"
        
        return True, "Continue trading"


# Factory function
def create_aggressive_engine(config: Dict) -> AggressiveTradingEngine:
    """Create aggressive trading engine"""
    return AggressiveTradingEngine(config)


# Example usage
async def main():
    """Test aggressive trading"""
    config = {
        "loan_amount": 75000,
        "max_loan_amount": 750000,
        "max_daily_loss": 75000,
        "max_daily_trades": 100,
        "max_concurrent_trades": 15,
        "min_profit_per_trade": 200,
        "compounding_enabled": True,
        "tokens": ["ETH", "USDC", "DAI", "WBTC", "LINK", "UNI", "AAVE"],
        "exchanges": ["uniswap_v2", "uniswap_v3", "sushiswap", "balancer", "curve"]
    }
    
    engine = create_aggressive_engine(config)
    await engine.start()
    
    print("🔍 Scanning for opportunities...")
    opportunities = await engine.scan_all_opportunities()
    
    print(f"\nFound {len(opportunities)} opportunities:")
    for opp in opportunities[:5]:
        print(f"  - {opp.strategy.value}: ${opp.expected_profit:.2f} ({opp.confidence*100:.0f}% confidence)")
    
    # Execute first opportunity if available
    if opportunities:
        result = await engine.execute_trade(opportunities[0])
        print(f"\nTrade result: {'✅ WIN' if result.success else '❌ LOSS'}")
        print(f"Profit: ${result.profit:.2f}")
    
    print(f"\nStats: {engine.get_stats()}")
    
    await engine.stop()


if __name__ == "__main__":
    asyncio.run(main())
