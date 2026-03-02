"""
Advanced Machine Learning Trading System
Uses historical data patterns to predict profitable opportunities
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import time
import json
import numpy as np
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class MarketSignal:
    """Trading signal from ML model"""
    signal_type: str  # "buy", "sell", "hold"
    confidence: float
    predicted_profit: float
    timeframe: str  # "short", "medium", "long"
    features: Dict


@dataclass
class PriceHistory:
    """Price history for analysis"""
    prices: List[float]
    volumes: List[float]
    timestamps: List[float]


class MLPricePredictor:
    """
    Machine Learning based price prediction
    Uses multiple indicators and pattern recognition
    """
    
    def __init__(self):
        # Price history buffers
        self.price_history = deque(maxlen=1000)
        self.volume_history = deque(maxlen=1000)
        
        # Model parameters (simplified - in production use TensorFlow/PyTorch)
        self.weights = self._initialize_weights()
        
        # Training data
        self.training_data = []
        
    def _initialize_weights(self) -> Dict:
        """Initialize model weights"""
        return {
            "rsi": 0.15,
            "macd": 0.20,
            "bollinger": 0.15,
            "volume": 0.10,
            "momentum": 0.20,
            "volatility": 0.10,
            "pattern": 0.10
        }
    
    async def analyze(self, prices: List[float], volumes: List[float]) -> MarketSignal:
        """Analyze market and generate signal"""
        
        # Add to history
        self.price_history.extend(prices)
        self.volume_history.extend(volumes)
        
        if len(self.price_history) < 50:
            return MarketSignal("hold", 0.0, 0, "short", {})
        
        # Calculate indicators
        rsi = self._calculate_rsi()
        macd = self._calculate_macd()
        bollinger = self._calculate_bollinger()
        momentum = self._calculate_momentum()
        volatility = self._calculate_volatility()
        pattern = self._detect_pattern()
        
        # Weighted score
        score = (
            rsi * self.weights["rsi"] +
            macd * self.weights["macd"] +
            bollinger * self.weights["bollinger"] +
            momentum * self.weights["momentum"] +
            volatility * self.weights["volatility"] +
            pattern * self.weights["pattern"]
        )
        
        # Determine signal
        if score > 0.6:
            signal_type = "buy"
            confidence = min(score, 0.95)
        elif score < -0.6:
            signal_type = "sell"
            confidence = min(abs(score), 0.95)
        else:
            signal_type = "hold"
            confidence = 0.5
        
        # Predict profit potential
        predicted_profit = abs(score) * 100 * (1 + abs(momentum))
        
        return MarketSignal(
            signal_type=signal_type,
            confidence=confidence,
            predicted_profit=predicted_profit,
            timeframe=self._determine_timeframe(volatility),
            features={
                "rsi": rsi,
                "macd": macd,
                "bollinger": bollinger,
                "momentum": momentum,
                "volatility": volatility,
                "pattern": pattern
            }
        )
    
    def _calculate_rsi(self) -> float:
        """Calculate RSI indicator"""
        if len(self.price_history) < 14:
            return 0.0
        
        prices = list(self.price_history)[-14:]
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        
        if avg_loss == 0:
            return 1.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # Normalize to -1 to 1
        return (rsi - 50) / 50
    
    def _calculate_macd(self) -> float:
        """Calculate MACD indicator"""
        if len(self.price_history) < 26:
            return 0.0
        
        prices = list(self.price_history)
        
        # EMA 12
        ema12 = self._ema(prices, 12)
        # EMA 26
        ema26 = self._ema(prices, 26)
        
        macd = ema12 - ema26
        signal = self._ema([macd], 9)
        
        # Normalize
        return max(-1, min(1, macd / (ema26 * 0.02)))
    
    def _ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def _calculate_bollinger(self) -> float:
        """Calculate Bollinger Bands position"""
        if len(self.price_history) < 20:
            return 0.0
        
        prices = list(self.price_history)[-20:]
        sma = sum(prices) / 20
        std = np.std(prices)
        
        if std == 0:
            return 0.0
        
        current = prices[-1]
        upper = sma + 2 * std
        lower = sma - 2 * std
        
        # Position between bands (-1 to 1)
        position = (current - sma) / (2 * std)
        return max(-1, min(1, position))
    
    def _calculate_momentum(self) -> float:
        """Calculate momentum"""
        if len(self.price_history) < 10:
            return 0.0
        
        prices = list(self.price_history)
        
        # Rate of change
        roc = (prices[-1] - prices[-10]) / prices[-10]
        
        # Normalize to -1 to 1
        return max(-1, min(1, roc * 10))
    
    def _calculate_volatility(self) -> float:
        """Calculate volatility"""
        if len(self.price_history) < 20:
            return 0.0
        
        prices = list(self.price_history)[-20:]
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        volatility = np.std(returns) if returns else 0
        
        # Higher volatility = higher risk but more opportunity
        return min(1, volatility * 10)
    
    def _detect_pattern(self) -> float:
        """Detect chart patterns (simplified)"""
        if len(self.price_history) < 30:
            return 0.0
        
        prices = list(self.price_history)[-30:]
        
        # Simple pattern detection
        # Check for trend
        first_half = sum(prices[:15]) / 15
        second_half = sum(prices[15:]) / 15
        
        trend = (second_half - first_half) / first_half
        
        return max(-1, min(1, trend * 5))
    
    def _determine_timeframe(self, volatility: float) -> str:
        """Determine best timeframe based on volatility"""
        if volatility > 0.5:
            return "short"  # High volatility = quick trades
        elif volatility > 0.2:
            return "medium"
        else:
            return "long"


class PatternRecognizer:
    """
    Recognizes profitable trading patterns
    Uses candlestick and chart patterns
    """
    
    def __init__(self):
        self.candle_patterns = {
            "doji": self._is_doji,
            "hammer": self._is_hammer,
            "engulfing": self._is_engulfing,
            "morning_star": self._is_morning_star,
        }
    
    async def analyze_candles(self, candles: List[Dict]) -> List[Dict]:
        """Analyze candlestick patterns"""
        signals = []
        
        # Check each pattern
        for pattern_name, pattern_func in self.candle_patterns.items():
            if pattern_func(candles):
                signals.append({
                    "pattern": pattern_name,
                    "strength": self._calculate_pattern_strength(candles),
                    "direction": self._get_pattern_direction(pattern_name)
                })
        
        return signals
    
    def _is_doji(self, candles: List[Dict]) -> bool:
        """Doji pattern"""
        if len(candles) < 1:
            return False
        
        candle = candles[-1]
        body = abs(candle["close"] - candle["open"])
        wicks = (candle["high"] - candle["low"]) - body
        
        return body < wicks * 0.3
    
    def _is_hammer(self, candles: List[Dict]) -> bool:
        """Hammer pattern"""
        if len(candles) < 1:
            return False
        
        candle = candles[-1]
        body = abs(candle["close"] - candle["open"])
        lower_wick = min(candle["close"], candle["open"]) - candle["low"]
        
        return lower_wick > body * 2 and (candle["high"] - max(candle["close"], candle["open"])) < body * 0.3
    
    def _is_engulfing(self, candles: List[Dict]) -> bool:
        """Engulfing pattern"""
        if len(candles) < 2:
            return False
        
        curr = candles[-1]
        prev = candles[-2]
        
        curr_body = abs(curr["close"] - curr["open"])
        prev_body = abs(prev["close"] - prev["open"])
        
        # Bullish engulfing
        if prev["close"] < prev["open"] and curr["close"] > curr["open"]:
            return curr["open"] < prev["close"] and curr["close"] > prev["open"]
        
        # Bearish engulfing
        if prev["close"] > prev["open"] and curr["close"] < curr["open"]:
            return curr["open"] > prev["close"] and curr["close"] < prev["open"]
        
        return False
    
    def _is_morning_star(self, candles: List[Dict]) -> bool:
        """Morning star pattern"""
        if len(candles) < 3:
            return False
        
        # Simplified - would need more complex logic in production
        return False
    
    def _calculate_pattern_strength(self, candles: List[Dict]) -> float:
        """Calculate pattern strength"""
        # Simplified - would use more factors
        return 0.7
    
    def _get_pattern_direction(self, pattern: str) -> str:
        """Get pattern direction"""
        bullish = ["hammer", "morning_star", "engulfing_bullish"]
        bearish = ["engulfing_bearish", "shooting_star"]
        
        if pattern in bullish:
            return "buy"
        elif pattern in bearish:
            return "sell"
        
        return "hold"


class SentimentAnalyzer:
    """
    Analyzes market sentiment from various sources
    """
    
    def __init__(self):
        self.sentiment_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    async def get_market_sentiment(self) -> Dict:
        """
        Get overall market sentiment
        In production, would analyze:
        - Twitter/X sentiment
        - Reddit discussions
        - News headlines
        - On-chain metrics
        """
        
        # Simplified sentiment based on on-chain data
        # In production: aggregate multiple sources
        
        return {
            "overall": "neutral",  # bullish, bearish, neutral
            "score": 0.0,  # -1 to 1
            "social_volume": 50000,
            "fear_greed_index": 50,  # 0-100
            "dominant_emotion": "neutral"
        }
    
    def _analyze_social(self, data: Dict) -> float:
        """Analyze social media sentiment"""
        # Would use NLP in production
        return 0.0
    
    def _analyze_onchain(self, data: Dict) -> float:
        """Analyze on-chain metrics"""
        # Would analyze exchange flows, whale activity, etc.
        return 0.0


class OptimalEntryExit:
    """
    Calculates optimal entry and exit points
    """
    
    def __init__(self):
        self.entry_strategies = {}
        self.exit_strategies = {}
    
    def calculate_entry(
        self,
        signal: MarketSignal,
        current_price: float,
        volatility: float
    ) -> Dict:
        """Calculate optimal entry point"""
        
        # Entry strategies based on signal type
        if signal.signal_type == "buy":
            # For buy signals, enter at slightly below current price
            entry_price = current_price * (1 - volatility * 0.3)
            size_factor = min(signal.confidence, 0.8)
            
            return {
                "entry_price": entry_price,
                "stop_loss": current_price * (1 - volatility * 2),
                "take_profit": current_price * (1 + volatility * 3),
                "position_size": size_factor,
                "reason": "ML signal buy with volatility adjustment"
            }
        
        elif signal.signal_type == "sell":
            entry_price = current_price * (1 + volatility * 0.3)
            size_factor = min(signal.confidence, 0.8)
            
            return {
                "entry_price": entry_price,
                "stop_loss": current_price * (1 + volatility * 2),
                "take_profit": current_price * (1 - volatility * 3),
                "position_size": size_factor,
                "reason": "ML signal sell with volatility adjustment"
            }
        
        # Hold - don't enter
        return {
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "position_size": 0,
            "reason": "No clear signal"
        }
    
    def calculate_exit(
        self,
        entry_price: float,
        current_price: float,
        time_held: float,
        profit_so_far: float
    ) -> Dict:
        """Calculate optimal exit point"""
        
        # Trailing stop based on profit
        if profit_so_far > 0:
            # Lock in profits with trailing stop
            trailing_stop = entry_price + profit_so_far * 0.5
            
            if current_price <= trailing_stop:
                return {
                    "should_exit": True,
                    "reason": "Trailing stop triggered",
                    "exit_price": current_price
                }
        
        # Time-based exit
        if time_held > 3600:  # 1 hour
            return {
                "should_exit": True,
                "reason": "Time-based exit",
                "exit_price": current_price
            }
        
        return {
            "should_exit": False,
            "reason": "Hold position",
            "exit_price": None
        }


class AdaptiveLearning:
    """
    Continuously learns from trading results to improve strategies
    """
    
    def __init__(self):
        self.trade_history = []
        self.performance_by_feature = {}
        
    def record_trade(self, trade: Dict):
        """Record trade result for learning"""
        self.trade_history.append({
            **trade,
            "timestamp": time.time()
        })
        
        # Update performance metrics
        self._update_performance(trade)
    
    def _update_performance(self, trade: Dict):
        """Update performance metrics"""
        # Group by features and calculate returns
        features = trade.get("features", {})
        
        for feature_name, feature_value in features.items():
            if feature_name not in self.performance_by_feature:
                self.performance_by_feature[feature_name] = {
                    "values": {},
                    "results": []
                }
            
            # Bucket the feature value
            bucket = round(feature_value, 1)
            
            if bucket not in self.performance_by_feature[feature_name]["values"]:
                self.performance_by_feature[feature_name]["values"][bucket] = []
            
            self.performance_by_feature[feature_name]["values"][bucket].append(
                trade.get("profit", 0)
            )
    
    def get_best_parameters(self) -> Dict:
        """Get best performing parameters"""
        best_params = {}
        
        for feature_name, data in self.performance_by_feature.items():
            best_bucket = None
            best_avg = float('-inf')
            
            for bucket, profits in data["values"].items():
                avg_profit = sum(profits) / len(profits)
                if avg_profit > best_avg and len(profits) >= 5:  # Min 5 trades
                    best_avg = avg_profit
                    best_bucket = bucket
            
            if best_bucket is not None:
                best_params[feature_name] = best_bucket
        
        return best_params
    
    def get_performance_stats(self) -> Dict:
        """Get overall performance statistics"""
        if not self.trade_history:
            return {"total_trades": 0}
        
        total_profit = sum(t.get("profit", 0) for t in self.trade_history)
        winning_trades = [t for t in self.trade_history if t.get("profit", 0) > 0]
        
        return {
            "total_trades": len(self.trade_history),
            "winning_trades": len(winning_trades),
            "win_rate": len(winning_trades) / len(self.trade_history),
            "total_profit": total_profit,
            "avg_profit": total_profit / len(self.trade_history),
            "best_params": self.get_best_parameters()
        }


# Factory
def create_ml_system():
    """Create ML trading system"""
    return {
        "predictor": MLPricePredictor(),
        "pattern": PatternRecognizer(),
        "sentiment": SentimentAnalyzer(),
        "entry_exit": OptimalEntryExit(),
        "learning": AdaptiveLearning()
    }
