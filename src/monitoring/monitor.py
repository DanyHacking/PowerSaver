"""
Monitoring and Alerting System for Autonomous Trading
Real-time monitoring, alerts, and performance tracking
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import time
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Types of alerts"""
    PROFIT = "profit"
    LOSS = "loss"
    RISK = "risk"
    SYSTEM = "system"
    OPPORTUNITY = "opportunity"


@dataclass
class Alert:
    """Alert data structure"""
    alert_id: str
    alert_type: AlertType
    severity: str
    title: str
    message: str
    timestamp: float
    metadata: Dict


class MetricsCollector:
    """Collect and store trading metrics"""
    
    def __init__(self):
        self.metrics_history: List[Dict] = []
        self.start_time = time.time()
        self.current_metrics = {}
    
    def record_metric(self, name: str, value: float, labels: Dict = None):
        """Record a metric"""
        metric = {
            "name": name,
            "value": value,
            "labels": labels or {},
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat()
        }
        self.metrics_history.append(metric)
        self.current_metrics[name] = value
    
    def get_metrics(self) -> Dict:
        """Get current metrics"""
        uptime = time.time() - self.start_time
        
        return {
            "uptime_seconds": uptime,
            "uptime_formatted": self._format_duration(uptime),
            "current_metrics": self.current_metrics,
            "total_records": len(self.metrics_history)
        }
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        elif seconds < 86400:
            return f"{seconds/3600:.1f}h"
        else:
            return f"{seconds/86400:.1f}d"


class AlertManager:
    """Manage and dispatch alerts"""
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.alert_callbacks: List[Callable] = []
        self.max_alerts = 1000
    
    def register_callback(self, callback: Callable):
        """Register alert callback"""
        self.alert_callbacks.append(callback)
    
    def create_alert(
        self,
        alert_type: AlertType,
        severity: str,
        title: str,
        message: str,
        metadata: Dict = None
    ) -> Alert:
        """Create and dispatch alert"""
        alert = Alert(
            alert_id=f"ALERT_{int(time.time())}_{len(self.alerts) + 1}",
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        
        self.alerts.append(alert)
        
        # Trim old alerts
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        
        # Dispatch to callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
        
        logger.info(f"[{severity.upper()}] {title}: {message}")
        
        return alert
    
    def get_alerts(self, limit: int = 50) -> List[Dict]:
        """Get recent alerts"""
        return [
            {
                "id": alert.alert_id,
                "type": alert.alert_type.value,
                "severity": alert.severity,
                "title": alert.title,
                "message": alert.message,
                "timestamp": alert.timestamp,
                "datetime": datetime.fromtimestamp(alert.timestamp).isoformat()
            }
            for alert in self.alerts[-limit:]
        ]
    
    def get_alerts_by_type(self, alert_type: AlertType) -> List[Alert]:
        """Get alerts by type"""
        return [alert for alert in self.alerts if alert.alert_type == alert_type]


class PerformanceTracker:
    """Track trading performance"""
    
    def __init__(self):
        self.trades: List[Dict] = []
        self.daily_stats: Dict[str, Dict] = {}
    
    def record_trade(self, trade: Dict):
        """Record trade data"""
        trade["timestamp"] = time.time()
        trade["datetime"] = datetime.fromtimestamp(trade["timestamp"]).isoformat()
        self.trades.append(trade)
        
        # Update daily stats
        date = trade["datetime"][:10]
        if date not in self.daily_stats:
            self.daily_stats[date] = {
                "trades": 0,
                "profit": 0,
                "losses": 0
            }
        
        self.daily_stats[date]["trades"] += 1
        self.daily_stats[date]["profit"] += trade.get("profit", 0)
        if trade.get("profit", 0) < 0:
            self.daily_stats[date]["losses"] += 1
    
    def get_performance(self) -> Dict:
        """Get performance analytics"""
        if not self.trades:
            return {"message": "No trades recorded"}
        
        profits = [t.get("profit", 0) for t in self.trades]
        total_profit = sum(profits)
        winning_trades = sum(1 for p in profits if p > 0)
        losing_trades = sum(1 for p in profits if p < 0)
        
        return {
            "total_trades": len(self.trades),
            "total_profit": total_profit,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": winning_trades / len(self.trades) * 100 if self.trades else 0,
            "average_profit": total_profit / len(self.trades),
            "max_profit": max(profits),
            "min_profit": min(profits),
            "daily_stats": self.daily_stats
        }


class SystemMonitor:
    """Monitor system health and performance"""
    
    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager
        self.metrics = MetricsCollector()
        self.performance = PerformanceTracker()
        self.is_running = False
        self.check_interval = 60  # seconds
    
    async def start(self):
        """Start monitoring"""
        self.is_running = True
        logger.info("System monitor started")
        
        while self.is_running:
            try:
                await self._monitor_loop()
            except Exception as e:
                logger.error(f"Monitor error: {e}")
            await asyncio.sleep(self.check_interval)
    
    async def stop(self):
        """Stop monitoring"""
        self.is_running = False
        logger.info("System monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        # Record system metrics
        self.metrics.record_metric("monitoring_active", 1)
        
        # Check system health
        await self._check_system_health()
        
        # Generate periodic reports
        if time.time() % 3600 < 60:  # Every hour
            await self._generate_hourly_report()
    
    async def _check_system_health(self):
        """Check system health"""
        # This would check actual system metrics in production
        # For now, simulate health checks
        
        # Check if system is responsive
        self.metrics.record_metric("system_health", 100)
    
    async def _generate_hourly_report(self):
        """Generate hourly performance report"""
        perf = self.performance.get_performance()
        
        self.alert_manager.create_alert(
            AlertType.SYSTEM,
            "INFO",
            "Hourly Performance Report",
            f"Trades: {perf.get('total_trades', 0)}, Profit: {perf.get('total_profit', 0):.2f}"
        )
    
    def record_trade(self, trade: Dict):
        """Record a trade"""
        self.performance.record_trade(trade)
        self.metrics.record_metric("total_trades", len(self.performance.trades))
    
    def record_profit(self, profit: float):
        """Record profit/loss"""
        self.metrics.record_metric("current_profit", profit)
        
        if profit > 100:
            self.alert_manager.create_alert(
                AlertType.PROFIT,
                "HIGH",
                "Significant Profit",
                f"Profit of {profit:.2f} detected"
            )
        elif profit < -100:
            self.alert_manager.create_alert(
                AlertType.LOSS,
                "HIGH",
                "Significant Loss",
                f"Loss of {abs(profit):.2f} detected"
            )


class Dashboard:
    """Generate dashboard reports"""
    
    def __init__(self, monitor: SystemMonitor):
        self.monitor = monitor
    
    def generate_dashboard(self) -> str:
        """Generate dashboard report"""
        metrics = self.monitor.metrics.get_metrics()
        performance = self.monitor.performance.get_performance()
        alerts = self.monitor.alert_manager.get_alerts(limit=10)
        
        dashboard = f"""
╔══════════════════════════════════════════════════════════╗
║         AUTONOMOUS TRADING SYSTEM DASHBOARD              ║
╠══════════════════════════════════════════════════════════╣
║  UPTIME: {metrics['uptime_formatted']:>15}  ║
║  TOTAL TRADES: {performance.get('total_trades', 0):>18}  ║
║  TOTAL PROFIT: {performance.get('total_profit', 0):>18.2f}  ║
║  WIN RATE: {performance.get('win_rate', 0):>17.1f}%  ║
╠══════════════════════════════════════════════════════════╣
║  RECENT ALERTS:                                          ║
"""
        
        for alert in alerts[:5]:
            dashboard += f"║  [{alert['severity']}] {alert['title']:<42} ║\n"
        
        dashboard += """╚══════════════════════════════════════════════════════════╝
"""
        
        return dashboard


async def main():
    """Test monitoring system"""
    alert_manager = AlertManager()
    monitor = SystemMonitor(alert_manager)
    dashboard = Dashboard(monitor)
    
    # Start monitoring
    await monitor.start()
    
    # Record some trades
    for i in range(10):
        profit = 50 if i % 2 == 0 else -25
        monitor.record_trade({
            "trade_id": f"TRADE_{i+1}",
            "profit": profit,
            "token": "ETH"
        })
        monitor.record_profit(profit)
    
    # Generate dashboard
    print(dashboard.generate_dashboard())
    
    # Stop monitoring
    await monitor.stop()


if __name__ == "__main__":
    asyncio.run(main())
