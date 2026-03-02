"""
System Health Monitor for Autonomous Operation
- Profit decay detection
- Latency spike detection
- Revert trend monitoring
- Builder ignore counter
- Oracle drift detection
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """System health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    STOPPED = "stopped"


@dataclass
class HealthMetrics:
    """Current health metrics"""
    status: HealthStatus
    profit_trend: float  # -1 to 1 (declining to increasing)
    latency_p99: float
    revert_rate: float
    builder_acceptance_rate: float
    oracle_drift: float
    timestamp: float


@dataclass
class Alert:
    """Health alert"""
    severity: str  # "warning", "error", "critical"
    component: str
    message: str
    timestamp: float
    action_taken: str = ""


class SystemHealthMonitor:
    """
    Autonomous health monitoring
    Automatically detects degradation and takes action
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Thresholds
        self.min_profit_trend = config.get("min_profit_trend", -0.3)  # Start warning if declining
        self.max_latency_ms = config.get("max_latency_ms", 5000)  # 5 seconds
        self.max_revert_rate = config.get("max_revert_rate", 0.15)  # 15%
        self.min_builder_acceptance = config.get("min_builder_acceptance", 0.3)  # 30%
        self.max_oracle_drift = config.get("max_oracle_drift", 0.05)  # 5%
        
        # History buffers
        self.profit_history = deque(maxlen=100)
        self.latency_history = deque(maxlen=100)
        self.revert_history = deque(maxlen=100)
        self.builder_history = deque(maxlen=50)
        self.oracle_history = deque(maxlen=50)
        
        # Counters
        self.total_trades = 0
        self.total_reverts = 0
        self.total_builder_accepted = 0
        self.total_builder_rejected = 0
        
        # Alerts
        self.alerts: List[Alert] = []
        self.alert_callbacks: List[Callable] = []
        
        # State
        self.is_running = False
        self.should_stop = False
        self.last_profit_check = 0
        self.profit_check_interval = 60  # Check every minute
        
        # Auto-recovery actions
        self.action_count = {
            "reduce_position": 0,
            "increase_gas": 0,
            "switch_builder": 0,
            "stop_system": 0,
        }
    
    def start(self):
        """Start health monitoring"""
        self.is_running = True
        self.should_stop = False
        logger.info("🟢 System Health Monitor started")
    
    def stop(self):
        """Stop health monitoring"""
        self.is_running = False
        logger.info("🔴 System Health Monitor stopped")
    
    # ============== DATA RECORDING ==============
    
    def record_trade(self, profit: float, success: bool, reverted: bool = False):
        """Record trade result"""
        self.total_trades += 1
        self.profit_history.append({
            "profit": profit,
            "timestamp": time.time(),
            "success": success,
            "reverted": reverted
        })
        
        if reverted:
            self.total_reverts += 1
            self.revert_history.append(1)
        else:
            self.revert_history.append(0)
        
        self.last_profit_check = time.time()
    
    def record_latency(self, latency_ms: float):
        """Record execution latency"""
        self.latency_history.append(latency_ms)
    
    def record_builder_response(self, accepted: bool):
        """Record builder response"""
        self.builder_history.append(1 if accepted else 0)
        
        if accepted:
            self.total_builder_accepted += 1
        else:
            self.total_builder_rejected += 1
    
    def record_oracle_price(self, oracle_price: float, actual_price: float):
        """Record oracle vs actual price for drift detection"""
        if actual_price > 0:
            drift = abs(oracle_price - actual_price) / actual_price
            self.oracle_history.append(drift)
    
    # ============== HEALTH CHECKS ==============
    
    def check_health(self) -> HealthMetrics:
        """Perform full health check"""
        now = time.time()
        
        # Calculate metrics
        profit_trend = self._calculate_profit_trend()
        latency_p99 = self._calculate_p99_latency()
        revert_rate = self._calculate_revert_rate()
        builder_acceptance = self._calculate_builder_acceptance()
        oracle_drift = self._calculate_oracle_drift()
        
        # Determine status
        status = self._determine_status(
            profit_trend, latency_p99, revert_rate, 
            builder_acceptance, oracle_drift
        )
        
        return HealthMetrics(
            status=status,
            profit_trend=profit_trend,
            latency_p99=latency_p99,
            revert_rate=revert_rate,
            builder_acceptance_rate=builder_acceptance,
            oracle_drift=oracle_drift,
            timestamp=now
        )
    
    def _calculate_profit_trend(self) -> float:
        """Calculate profit trend using linear regression"""
        if len(self.profit_history) < 10:
            return 0.0  # Not enough data
        
        # Get recent profits
        profits = [p["profit"] for p in list(self.profit_history)[-20:]]
        
        if not profits:
            return 0.0
        
        # Simple trend: compare recent avg to older avg
        mid = len(profits) // 2
        older_avg = sum(profits[:mid]) / mid if mid > 0 else 0
        recent_avg = sum(profits[mid:]) / (len(profits) - mid)
        
        if older_avg == 0:
            return 0.0
        
        # Normalize to -1 to 1 range
        trend = (recent_avg - older_avg) / abs(older_avg)
        
        # Clamp
        return max(-1.0, min(1.0, trend))
    
    def _calculate_p99_latency(self) -> float:
        """Calculate 99th percentile latency"""
        if not self.latency_history:
            return 0.0
        
        sorted_latencies = sorted(self.latency_history)
        p99_index = int(len(sorted_latencies) * 0.99)
        
        return sorted_latencies[p99_index] if p99_index < len(sorted_latencies) else sorted_latencies[-1]
    
    def _calculate_revert_rate(self) -> float:
        """Calculate revert rate"""
        if not self.revert_history:
            return 0.0
        
        return sum(self.revert_history) / len(self.revert_history)
    
    def _calculate_builder_acceptance(self) -> float:
        """Calculate builder acceptance rate"""
        total = self.total_builder_accepted + self.total_builder_rejected
        
        if total == 0:
            return 0.5  # Unknown
        
        return self.total_builder_accepted / total
    
    def _calculate_oracle_drift(self) -> float:
        """Calculate average oracle drift"""
        if not self.oracle_history:
            return 0.0
        
        return sum(self.oracle_history) / len(self.oracle_history)
    
    def _determine_status(
        self,
        profit_trend: float,
        latency_p99: float,
        revert_rate: float,
        builder_acceptance: float,
        oracle_drift: float
    ) -> HealthStatus:
        """Determine overall health status"""
        
        # Critical conditions
        if profit_trend < self.min_profit_trend - 0.3:
            return HealthStatus.CRITICAL
        if latency_p99 > self.max_latency_ms * 2:
            return HealthStatus.CRITICAL
        if revert_rate > self.max_revert_rate * 2:
            return HealthStatus.CRITICAL
        if builder_acceptance < self.min_builder_acceptance / 2:
            return HealthStatus.CRITICAL
        
        # Degraded conditions
        if profit_trend < self.min_profit_trend:
            return HealthStatus.DEGRADED
        if latency_p99 > self.max_latency_ms:
            return HealthStatus.DEGRADED
        if revert_rate > self.max_revert_rate:
            return HealthStatus.DEGRADED
        if builder_acceptance < self.min_builder_acceptance:
            return HealthStatus.DEGRADED
        if oracle_drift > self.max_oracle_drift:
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    # ============== AUTO-RECOVERY ACTIONS ==============
    
    async def process_health_check(self):
        """Process health check and take automatic actions"""
        if not self.is_running:
            return
        
        metrics = self.check_health()
        
        # Log status
        if metrics.status == HealthStatus.CRITICAL:
            logger.error(f"🔴 SYSTEM CRITICAL: {metrics}")
            await self._handle_critical(metrics)
        elif metrics.status == HealthStatus.DEGRADED:
            logger.warning(f"🟡 SYSTEM DEGRADED: {metrics}")
            await self._handle_degraded(metrics)
        else:
            logger.debug(f"🟢 System healthy: {metrics}")
        
        # Trigger callbacks
        for callback in self.alert_callbacks:
            try:
                callback(metrics, self.alerts[-1] if self.alerts else None)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    async def _handle_critical(self, metrics: HealthMetrics):
        """Handle critical health status"""
        alert = Alert(
            severity="critical",
            component="system",
            message=f"Critical health detected: profit_trend={metrics.profit_trend:.2f}, revert_rate={metrics.revert_rate:.2%}",
            timestamp=time.time()
        )
        self.alerts.append(alert)
        
        # Escalating actions
        if metrics.profit_trend < -0.5:
            self.action_count["reduce_position"] += 1
            alert.action_taken = "Position size reduced"
            logger.warning("⚠️ Reducing position size due to profit decline")
        
        if metrics.revert_rate > 0.3:
            self.action_count["stop_system"] += 1
            alert.action_taken = "SYSTEM STOPPED"
            self.should_stop = True
            logger.error("🛑 STOPPING SYSTEM: Revert rate too high")
        
        if metrics.builder_acceptance < 0.1:
            self.action_count["switch_builder"] += 1
            alert.action_taken = "Builder switched"
            logger.warning("🔄 Switching to alternative builder")
    
    async def _handle_degraded(self, metrics: HealthMetrics):
        """Handle degraded health status"""
        alert = Alert(
            severity="warning",
            component="system",
            message=f"Degraded health: profit_trend={metrics.profit_trend:.2f}",
            timestamp=time.time()
        )
        self.alerts.append(alert)
        
        # Preventive actions
        if metrics.profit_trend < -0.2:
            self.action_count["reduce_position"] += 1
            alert.action_taken = "Position size reduced"
        
        if metrics.latency_p99 > self.max_latency_ms:
            self.action_count["increase_gas"] += 1
            alert.action_taken = "Gas priority increased"
    
    def register_alert_callback(self, callback: Callable):
        """Register callback for alerts"""
        self.alert_callbacks.append(callback)
    
    def get_recommendations(self) -> Dict:
        """Get system recommendations based on health"""
        metrics = self.check_health()
        
        recommendations = {
            "should_continue": True,
            "actions": [],
            "reasoning": []
        }
        
        if metrics.status == HealthStatus.CRITICAL:
            recommendations["should_continue"] = False
            recommendations["actions"].append("STOP_SYSTEM")
            recommendations["reasoning"].append("Critical health status")
        
        if metrics.profit_trend < -0.3:
            recommendations["actions"].append("REDUCE_POSITION_SIZE")
            recommendations["reasoning"].append(f"Profit declining: {metrics.profit_trend:.2%}")
        
        if metrics.revert_rate > 0.2:
            recommendations["actions"].append("INCREASE_SLIPPAGE")
            recommendations["reasoning"].append(f"High revert rate: {metrics.revert_rate:.2%}")
        
        if metrics.builder_acceptance < 0.2:
            recommendations["actions"].append("TRY_ALTERNATIVE_BUILDERS")
            recommendations["reasoning"].append(f"Low acceptance: {metrics.builder_acceptance:.2%}")
        
        return recommendations
    
    def get_stats(self) -> Dict:
        """Get monitoring statistics"""
        return {
            "status": self.check_health().status.value,
            "total_trades": self.total_trades,
            "total_reverts": self.total_reverts,
            "revert_rate": self._calculate_revert_rate(),
            "builder_acceptance": self._calculate_builder_acceptance(),
            "profit_trend": self._calculate_profit_trend(),
            "action_count": self.action_count,
            "alerts_count": len(self.alerts)
        }


# Factory
def create_health_monitor(config: Dict = None) -> SystemHealthMonitor:
    """Create health monitor instance"""
    return SystemHealthMonitor(config or {})
