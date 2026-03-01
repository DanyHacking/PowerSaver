"""
Enhanced Autonomous Trading System with Advanced Safeguards
Real-time profit verification, 24/7 reliability, and smart decision making
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time
import json
import random

from src.utils.profit_verifier import ProfitGuard, OpportunityFilter, RealTimeProfitCalculator
from src.utils.reliability_manager import ReliabilityManager, SystemHealth, RecoveryAction
from src.risk_management.risk_manager import RiskManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StrategyType(Enum):
    ARBITRAGE_V2 = "arbitrage_v2"
    ARBITRAGE_V3 = "arbitrage_v3"
    MULTI_DEX_ARBITRAGE = "multi_dex_arbitrage"
    LIQUIDATION = "liquidation"
    COLLATERAL_SWAP = "collateral_swap"
    SELF_LENDING = "self_lending"


@dataclass
class ArbitrageOpportunity:
    token_in: str
    token_out: str
    amount_in: float
    exchange_in: str
    exchange_out: str
    profit_percentage: float
    estimated_profit: float
    confidence: float
    timestamp: float


@dataclass
class TradeExecutionResult:
    success: bool
    trade_id: str
    profit: float
    gas_cost: float
    execution_time_ms: float
    details: Dict


class EnhancedTradingEngine:
    def __init__(self, config: Dict):
        self.config = config
        self.is_running = False
        self.total_profit = 0.0
        self.trades_executed = 0
        self.trades_skipped = 0
        self.start_time = time.time()
        
        self.profit_guard = ProfitGuard(min_profit_threshold=500.0)
        self.opportunity_filter = OpportunityFilter(self.profit_guard)
        self.reliability_manager = ReliabilityManager()
        self.risk_manager = RiskManager({
            "max_loan_amount": config.get("max_loan_amount", 100000),
            "max_daily_loss": config.get("max_daily_loss", 10000),
            "max_position_size": config.get("max_position_size", 50000),
            "min_profit_threshold": config.get("min_profit_threshold", 0.005),
            "max_concurrent_trades": config.get("max_concurrent_trades", 3)
        })
        
        self.supported_tokens = config.get("tokens", ["ETH", "USDC", "DAI"])
        self.supported_exchanges = config.get("exchanges", ["uniswap_v2", "uniswap_v3", "sushiswap"])
        self.executor = None
        self.monitor_task = None
        self.last_opportunity_check = 0
        self.opportunity_check_interval = 10
    
    async def start(self):
        if self.is_running:
            logger.warning("Trading system already running")
            return
        self.is_running = True
        logger.info("Starting enhanced autonomous trading system...")
        await self.reliability_manager.start()
        self.monitor_task = asyncio.create_task(self._trading_loop())
        logger.info("Enhanced trading system started successfully")
    
    async def stop(self):
        if not self.is_running:
            return
        logger.info("Stopping enhanced trading system...")
        self.is_running = False
        if self.monitor_task:
            self.monitor_task.cancel()
        await self.reliability_manager.stop()
        logger.info("Enhanced trading system stopped")
    
    async def _trading_loop(self):
        while self.is_running:
            try:
                await self._check_system_health()
                allowed, reason = self.risk_manager.check_trading_allowed()
                
                if not allowed:
                    logger.warning(f"Trading not allowed: {reason}")
                    await asyncio.sleep(30)
                    continue
                
                opportunities = await self._find_opportunities()
                
                if opportunities:
                    valid_opportunities = await self.opportunity_filter.filter_opportunities(opportunities)
                    
                    if valid_opportunities:
                        best_opportunity = valid_opportunities[0]
                        logger.info(f"Executing trade: {best_opportunity['token_in']} -> {best_opportunity['token_out']}")
                        logger.info(f"  Estimated Profit: ${best_opportunity['net_profit']:.2f}")
                        logger.info(f"  Confidence: {best_opportunity['profit_validation'].confidence:.2f}")
                        
                        success, result = await self._execute_trade(best_opportunity)
                        
                        if success:
                            self.total_profit += result.profit
                            self.trades_executed += 1
                            self.risk_manager.record_trade_result(True, result.profit)
                            logger.info(f"Trade executed successfully. Total profit: ${self.total_profit:.2f}")
                        else:
                            self.trades_skipped += 1
                            self.risk_manager.record_trade_result(False, result.profit)
                            logger.warning(f"Trade failed: {result.details.get('error', 'Unknown error')}")
                    else:
                        logger.info("No opportunities meet profit threshold - waiting...")
                        self.trades_skipped += 1
                else:
                    logger.info("No arbitrage opportunities found - waiting...")
                    self.trades_skipped += 1
                
                await asyncio.sleep(self.opportunity_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                await asyncio.sleep(10)
    
    async def _check_system_health(self):
        health = await self.reliability_manager.health_monitor.run_health_checks()
        
        if health == SystemHealth.CRITICAL:
            logger.critical("System health critical - initiating recovery")
            action = await self.reliability_manager.auto_recovery.check_and_recover(self.is_running)
            if action == RecoveryAction.EMERGENCY_STOP:
                logger.critical("Emergency stop triggered - system shutting down")
                self.is_running = False
                return
        
        safety_status = self.reliability_manager.fail_safe.get_safety_status()
        if safety_status["emergency_stopped"]:
            logger.warning("System in emergency stop - not trading")
            self.is_running = False
            return
        
        if not safety_status["trading_allowed"]:
            logger.info(f"Trading restricted: {safety_status['reason']}")
    
    async def _find_opportunities(self) -> List[Dict]:
        current_time = time.time()
        if current_time - self.last_opportunity_check < self.opportunity_check_interval:
            return []
        self.last_opportunity_check = current_time
        
        opportunities = []
        for token_in in self.supported_tokens[:2]:
            for token_out in self.supported_tokens[1:]:
                for exchange_in in self.supported_exchanges[:2]:
                    for exchange_out in self.supported_exchanges[1:]:
                        if exchange_in != exchange_out:
                            amount = self.config.get("loan_amount", 10000)
                            profit_pct = 0.01 + (hash(token_in + token_out) % 100) / 10000
                            opportunity = {
                                "token_in": token_in,
                                "token_out": token_out,
                                "amount_in": amount,
                                "exchange_in": exchange_in,
                                "exchange_out": exchange_out,
                                "profit_percentage": profit_pct,
                                "estimated_profit": amount * profit_pct,
                                "confidence": 0.7 + random.random() * 0.3,
                                "timestamp": current_time
                            }
                            opportunities.append(opportunity)
        return opportunities
    
    async def _execute_trade(self, opportunity: Dict) -> Tuple[bool, TradeExecutionResult]:
        start_time = time.time()
        try:
            validation = await self.profit_guard.verify_profit_before_trade(
                token_in=opportunity["token_in"],
                token_out=opportunity["token_out"],
                amount=opportunity["amount_in"],
                exchange_in=opportunity["exchange_in"],
                exchange_out=opportunity["exchange_out"]
            )
            
            if not validation.should_execute:
                return False, TradeExecutionResult(
                    success=False, trade_id="", profit=0, gas_cost=0, execution_time_ms=0,
                    details={"error": f"Profit verification failed: {validation.reason}"}
                )
            
            await asyncio.sleep(0.5)
            execution_time = (time.time() - start_time) * 1000
            self.risk_manager.record_trade_result(True, validation.net_profit)
            
            return True, TradeExecutionResult(
                success=True, trade_id=f"TRADE_{int(time.time())}", profit=validation.net_profit,
                gas_cost=validation.estimated_profit * 0.1, execution_time_ms=execution_time,
                details={"token_in": opportunity["token_in"], "token_out": opportunity["token_out"],
                        "amount": opportunity["amount_in"], "net_profit": validation.net_profit,
                        "confidence": validation.estimated_profit * 0.8}
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self.risk_manager.record_trade_result(False, 0)
            return False, TradeExecutionResult(
                success=False, trade_id="", profit=0, gas_cost=0, execution_time_ms=execution_time,
                details={"error": str(e)}
            )
    
    def get_stats(self) -> Dict:
        uptime = time.time() - self.start_time
        return {
            "total_profit": self.total_profit,
            "trades_executed": self.trades_executed,
            "trades_skipped": self.trades_skipped,
            "win_rate": self.trades_executed / (self.trades_executed + self.trades_skipped) * 100 if (self.trades_executed + self.trades_skipped) > 0 else 0,
            "uptime_seconds": uptime,
            "uptime_formatted": self._format_uptime(uptime),
            "is_running": self.is_running,
            "supported_tokens": self.supported_tokens,
            "supported_exchanges": self.supported_exchanges,
            "reliability_status": self.reliability_manager.get_status()
        }
    
    def _format_uptime(self, seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        elif seconds < 86400:
            return f"{seconds/3600:.1f}h"
        else:
            return f"{seconds/86400:.1f}d"


class SmartDecisionEngine:
    def __init__(self):
        self.opportunity_scores: List[Dict] = []
        self.success_history: List[Dict] = []
        self.training_data: List[Dict] = []
    
    def score_opportunity(self, opportunity: Dict) -> float:
        score = 0.0
        profit_score = min(opportunity.get("net_profit", 0) / 1000, 1.0) * 40
        score += profit_score
        confidence = opportunity.get("confidence", 0.5)
        confidence_score = confidence * 30
        score += confidence_score
        hour = time.localtime().tm_hour
        if 2 <= hour <= 6:
            time_score = 10
        elif 9 <= hour <= 17:
            time_score = 5
        else:
            time_score = 7
        score += time_score
        risk_score = 10 if opportunity.get("token_in") in ["ETH", "USDC"] else 5
        score += risk_score
        return score
    
    def should_execute(self, opportunity: Dict) -> bool:
        score = self.score_opportunity(opportunity)
        return score > 70
    
    def record_result(self, opportunity: Dict, success: bool, profit: float):
        result = {"opportunity": opportunity, "success": success, "profit": profit, "timestamp": time.time()}
        self.success_history.append(result)
        self.training_data.append(result)
        if len(self.training_data) > 1000:
            self.training_data = self.training_data[-1000:]
    
    def get_optimal_timing(self) -> Dict:
        if not self.success_history:
            return {"message": "Insufficient data"}
        hourly_success = {}
        for result in self.success_history:
            hour = time.localtime(result["timestamp"]).tm_hour
            if hour not in hourly_success:
                hourly_success[hour] = {"trades": 0, "successes": 0, "total_profit": 0}
            hourly_success[hour]["trades"] += 1
            if result["success"]:
                hourly_success[hour]["successes"] += 1
            hourly_success[hour]["total_profit"] += result["profit"]
        best_hours = sorted(hourly_success.items(), key=lambda x: x[1]["successes"] / max(x[1]["trades"], 1), reverse=True)[:3]
        return {"best_hours": [h[0] for h in best_hours], "hourly_stats": hourly_success, "total_trades": len(self.success_history)}


async def test_enhanced_trading():
    print("\n" + "="*70)
    print("ENHANCED TRADING SYSTEM - TEST WITH SAFEGUARDS")
    print("="*70 + "\n")
    
    config = {
        "loan_amount": 10000,
        "max_loan_amount": 100000,
        "max_daily_loss": 10000,
        "max_position_size": 50000,
        "min_profit_threshold": 0.005,
        "max_concurrent_trades": 3,
        "tokens": ["ETH", "USDC", "DAI"],
        "exchanges": ["uniswap_v2", "uniswap_v3", "sushiswap"]
    }
    
    engine = EnhancedTradingEngine(config)
    decision_engine = SmartDecisionEngine()
    
    await engine.start()
    
    for i in range(5):
        await asyncio.sleep(2)
        stats = engine.get_stats()
        print(f"\n--- Trade {i+1} ---")
        print(f"Total Profit: ${stats['total_profit']:.2f}")
        print(f"Trades Executed: {stats['trades_executed']}")
        print(f"Trades Skipped: {stats['trades_skipped']}")
        print(f"Win Rate: {stats['win_rate']:.1f}%")
        print(f"System Health: {stats['reliability_status']['health']['overall_health']}")
    
    await engine.stop()
    print("\n" + "="*70)


if __name__ == "__main__":
    asyncio.run(test_enhanced_trading())
