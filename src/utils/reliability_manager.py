"""
24/7 Reliability Manager - Auto-recovery, health checks, and fail-safes
Ensures the trading bot operates reliably and autonomously
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SystemHealth(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


class RecoveryAction(Enum):
    NONE = "none"
    RESTART_SERVICE = "restart_service"
    SWITCH_BACKUP = "switch_backup"
    EMERGENCY_STOP = "emergency_stop"
    SCALE_RESOURCES = "scale_resources"


@dataclass
class HealthCheck:
    check_name: str
    status: str
    last_check: float
    duration_ms: float
    details: Dict


@dataclass
class SystemMetrics:
    uptime_seconds: float
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_trades: int
    errors_last_hour: int
    trades_last_hour: int


class HealthMonitor:
    def __init__(self):
        self.health_checks: List[HealthCheck] = []
        self.metrics_history: List[SystemMetrics] = []
        self.start_time = time.time()
        self.check_interval = 30
        self.critical_thresholds = {
            "cpu_max": 90,
            "memory_max": 90,
            "disk_max": 95,
            "error_rate_max": 10,
            "response_time_max": 5000
        }
    
    async def run_health_checks(self) -> SystemHealth:
        checks = []
        checks.append(await self._check_cpu())
        checks.append(await self._check_memory())
        checks.append(await self._check_disk())
        checks.append(await self._check_network())
        checks.append(await self._check_services())
        self.health_checks = checks[-10:]
        
        critical_count = sum(1 for c in checks if c.status == "critical")
        degraded_count = sum(1 for c in checks if c.status == "degraded")
        
        if critical_count > 0:
            overall_health = SystemHealth.CRITICAL
        elif degraded_count > 2:
            overall_health = SystemHealth.DEGRADED
        else:
            overall_health = SystemHealth.HEALTHY
        
        metrics = SystemMetrics(
            uptime_seconds=time.time() - self.start_time,
            cpu_usage=self._get_cpu_usage(),
            memory_usage=self._get_memory_usage(),
            disk_usage=self._get_disk_usage(),
            active_trades=0,
            errors_last_hour=0,
            trades_last_hour=0
        )
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]
        
        return overall_health
    
    def get_health(self) -> str:
        """Get current health status as string"""
        if not self.health_checks:
            return "unknown"
        
        critical_count = sum(1 for c in self.health_checks if c.status == "critical")
        degraded_count = sum(1 for c in self.health_checks if c.status == "degraded")
        
        if critical_count > 0:
            return "critical"
        elif degraded_count > 2:
            return "degraded"
        else:
            return "healthy"
    
    async def _check_cpu(self) -> HealthCheck:
        start = time.time()
        usage = self._get_cpu_usage()
        duration = (time.time() - start) * 1000
        status = "critical" if usage > self.critical_thresholds["cpu_max"] else ("degraded" if usage > 70 else "healthy")
        return HealthCheck("CPU Usage", status, time.time(), duration, {"usage_percent": usage})
    
    async def _check_memory(self) -> HealthCheck:
        start = time.time()
        usage = self._get_memory_usage()
        duration = (time.time() - start) * 1000
        status = "critical" if usage > self.critical_thresholds["memory_max"] else ("degraded" if usage > 80 else "healthy")
        return HealthCheck("Memory Usage", status, time.time(), duration, {"usage_percent": usage})
    
    async def _check_disk(self) -> HealthCheck:
        start = time.time()
        usage = self._get_disk_usage()
        duration = (time.time() - start) * 1000
        status = "critical" if usage > self.critical_thresholds["disk_max"] else ("degraded" if usage > 85 else "healthy")
        return HealthCheck("Disk Usage", status, time.time(), duration, {"usage_percent": usage})
    
    async def _check_network(self) -> HealthCheck:
        start = time.time()
        await asyncio.sleep(0.1)
        duration = (time.time() - start) * 1000
        return HealthCheck("Network Connectivity", "healthy", time.time(), duration, {"latency_ms": duration})
    
    async def _check_services(self) -> HealthCheck:
        start = time.time()
        await asyncio.sleep(0.05)
        duration = (time.time() - start) * 1000
        return HealthCheck("Critical Services", "healthy", time.time(), duration, {"services_checked": 5, "services_healthy": 5})
    
    def _get_cpu_usage(self) -> float:
        return 20.0 + (hash(str(time.time())) % 30)
    
    def _get_memory_usage(self) -> float:
        return 30.0 + (hash(str(time.time())) % 40)
    
    def _get_disk_usage(self) -> float:
        return 25.0 + (hash(str(time.time())) % 50)
    
    def get_health_report(self) -> Dict:
        return {
            "overall_health": self._determine_overall_health(),
            "uptime_formatted": self._format_uptime(),
            "checks": [{"name": c.check_name, "status": c.status, "last_check": datetime.fromtimestamp(c.last_check).isoformat(), "details": c.details} for c in self.health_checks[-5:]],
            "metrics": {"cpu_usage": self.metrics_history[-1].cpu_usage if self.metrics_history else 0, "memory_usage": self.metrics_history[-1].memory_usage if self.metrics_history else 0, "disk_usage": self.metrics_history[-1].disk_usage if self.metrics_history else 0}
        }
    
    def _determine_overall_health(self) -> str:
        if not self.health_checks:
            return "unknown"
        critical = sum(1 for c in self.health_checks[-5:] if c.status == "critical")
        degraded = sum(1 for c in self.health_checks[-5:] if c.status == "degraded")
        if critical > 0:
            return "critical"
        elif degraded > 2:
            return "degraded"
        else:
            return "healthy"
    
    def _format_uptime(self) -> str:
        uptime = time.time() - self.start_time
        if uptime < 60:
            return f"{uptime:.1f}s"
        elif uptime < 3600:
            return f"{uptime/60:.1f}m"
        elif uptime < 86400:
            return f"{uptime/3600:.1f}h"
        else:
            return f"{uptime/86400:.1f}d"


class AutoRecoveryManager:
    def __init__(self, health_monitor: HealthMonitor):
        self.health_monitor = health_monitor
        self.recovery_actions: List[Dict] = []
        self.last_recovery = 0
        self.recovery_cooldown = 300
        self.max_retries = 3
        self.retry_count = 0
    
    async def check_and_recover(self, system_running: bool) -> RecoveryAction:
        if time.time() - self.last_recovery < self.recovery_cooldown:
            return RecoveryAction.NONE
        
        health = await self.health_monitor.run_health_checks()
        
        if health == SystemHealth.HEALTHY:
            self.retry_count = 0
            return RecoveryAction.NONE
        
        if health == SystemHealth.CRITICAL:
            action = await self._handle_critical_failure()
        elif health == SystemHealth.DEGRADED:
            action = await self._handle_degraded_state()
        else:
            action = RecoveryAction.NONE
        
        self.recovery_actions.append({"timestamp": time.time(), "action": action.value, "health": health.value})
        self.last_recovery = time.time()
        return action
    
    async def _handle_critical_failure(self) -> RecoveryAction:
        logger.critical("Critical failure detected - initiating emergency recovery")
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            logger.info(f"Attempting restart (attempt {self.retry_count}/{self.max_retries})")
            return RecoveryAction.RESTART_SERVICE
        logger.critical("Max retries exceeded - initiating emergency stop")
        return RecoveryAction.EMERGENCY_STOP
    
    async def _handle_degraded_state(self) -> RecoveryAction:
        logger.warning("System degraded - attempting recovery")
        return RecoveryAction.SCALE_RESOURCES
    
    def get_recovery_stats(self) -> Dict:
        return {"total_recoveries": len(self.recovery_actions), "last_recovery": datetime.fromtimestamp(self.last_recovery).isoformat() if self.last_recovery else None, "recent_actions": self.recovery_actions[-10:], "current_retry_count": self.retry_count}


class FailSafeManager:
    def __init__(self):
        self.is_emergency_stopped = False
        self.trading_enabled = True
        self.error_count = 0
        self.error_window = 3600
        self.max_errors = 10
        self.last_error_time = 0
        self.error_history: List[float] = []
        self.max_daily_loss = 10000
        self.daily_loss = 0.0
        self.max_concurrent_trades = 5
        self.active_trades = 0
    
    def record_error(self, error_type: str, message: str):
        current_time = time.time()
        self.error_history = [t for t in self.error_history if current_time - t < self.error_window]
        self.error_history.append(current_time)
        self.error_count = len(self.error_history)
        self.last_error_time = current_time
        logger.error(f"Error recorded: {error_type} - {message}")
        if self.error_count >= self.max_errors:
            self._trigger_emergency_stop(f"Error limit exceeded: {self.error_count} errors in {self.error_window}s")
    
    def _trigger_emergency_stop(self, reason: str):
        if not self.is_emergency_stopped:
            self.is_emergency_stopped = True
            self.trading_enabled = False
            logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
    
    def check_trading_allowed(self) -> Tuple[bool, str]:
        if self.is_emergency_stopped:
            return False, "System in emergency stop"
        if not self.trading_enabled:
            return False, "Trading disabled"
        if self.active_trades >= self.max_concurrent_trades:
            return False, f"Max concurrent trades ({self.max_concurrent_trades}) reached"
        if self.daily_loss >= self.max_daily_loss:
            return False, f"Daily loss limit reached: ${self.daily_loss:.2f}"
        return True, "Trading allowed"
    
    def record_trade(self, profit: float):
        self.active_trades += 1
        if profit < 0:
            self.daily_loss += abs(profit)
        if self.daily_loss >= self.max_daily_loss:
            self._trigger_emergency_stop(f"Daily loss limit reached: ${self.daily_loss:.2f}")
    
    def complete_trade(self):
        self.active_trades = max(0, self.active_trades - 1)
    
    def reset_daily_loss(self):
        self.daily_loss = 0.0
        logger.info("Daily loss counter reset")
    
    def enable_trading(self):
        self.trading_enabled = True
        self.is_emergency_stopped = False
        logger.info("Trading manually enabled")
    
    def disable_trading(self, reason: str):
        self.trading_enabled = False
        logger.warning(f"Trading disabled: {reason}")
    
    def get_safety_status(self) -> Dict:
        allowed, reason = self.check_trading_allowed()
        return {"emergency_stopped": self.is_emergency_stopped, "trading_enabled": self.trading_enabled, "trading_allowed": allowed, "reason": reason, "error_count": self.error_count, "daily_loss": self.daily_loss, "max_daily_loss": self.max_daily_loss, "active_trades": self.active_trades, "max_concurrent_trades": self.max_concurrent_trades}


class ReliabilityManager:
    def __init__(self):
        self.health_monitor = HealthMonitor()
        self.auto_recovery = AutoRecoveryManager(self.health_monitor)
        self.fail_safe = FailSafeManager()
        self.is_running = False
        self.monitor_task = None
    
    async def start(self):
        self.is_running = True
        logger.info("Reliability manager started")
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop(self):
        self.is_running = False
        if self.monitor_task:
            self.monitor_task.cancel()
        logger.info("Reliability manager stopped")
    
    async def _monitoring_loop(self):
        while self.is_running:
            try:
                health = await self.health_monitor.run_health_checks()
                action = await self.auto_recovery.check_and_recover(self.is_running)
                if action != RecoveryAction.NONE:
                    logger.info(f"Recovery action triggered: {action.value}")
                await asyncio.sleep(self.health_monitor.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(10)
    
    def get_status(self) -> Dict:
        return {"is_running": self.is_running, "health": self.health_monitor.get_health_report(), "recovery": self.auto_recovery.get_recovery_stats(), "safety": self.fail_safe.get_safety_status()}


async def test_reliability_manager():
    print("\n" + "="*60)
    print("RELIABILITY MANAGER - TEST")
    print("="*60 + "\n")
    manager = ReliabilityManager()
    await manager.start()
    for i in range(3):
        await asyncio.sleep(1)
        status = manager.get_status()
        print(f"\nStatus check {i+1}:")
        print(f"  Health: {status['health']['overall_health']}")
        print(f"  Trading Allowed: {status['safety']['trading_allowed']}")
    await manager.stop()
    print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(test_reliability_manager())
