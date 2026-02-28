"""
Health Check API Endpoint
Provides HTTP endpoint for Docker health checks and monitoring
"""

import asyncio
import logging
from typing import Dict, Any
from dataclasses import dataclass
import time

from aiohttp import web

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Health status response"""
    status: str  # healthy, degraded, unhealthy
    timestamp: float
    uptime_seconds: float
    checks: Dict[str, Any]


class HealthCheckEndpoint:
    """HTTP health check endpoint"""
    
    def __init__(self, trading_engine=None, reliability_manager=None, blockchain_data=None):
        self.trading_engine = trading_engine
        self.reliability_manager = reliability_manager
        self.blockchain_data = blockchain_data
        self.start_time = time.time()
        self.app = None
    
    def setup(self) -> web.Application:
        """Setup aiohttp application with health endpoints"""
        self.app = web.Application()
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/health/ready', self.readiness_check)
        self.app.router.add_get('/health/live', self.liveness_check)
        self.app.router.add_get('/status', self.get_status)
        self.app.router.add_get('/metrics', self.get_metrics)
        return self.app
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Main health check endpoint"""
        try:
            checks = await self._run_checks()
            
            # Determine overall status
            statuses = [check.get("status") for check in checks.values()]
            if "unhealthy" in statuses:
                status = "unhealthy"
            elif "degraded" in statuses:
                status = "degraded"
            else:
                status = "healthy"
            
            response = {
                "status": status,
                "timestamp": time.time(),
                "uptime_seconds": time.time() - self.start_time,
                "checks": checks
            }
            
            return web.json_response(response, status=200 if status == "healthy" else 503)
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return web.json_response({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }, status=503)
    
    async def readiness_check(self, request: web.Request) -> web.Response:
        """Kubernetes readiness probe"""
        try:
            # Check if system is ready to accept traffic
            is_ready = True
            reasons = []
            
            # Check if trading engine is initialized
            if not self.trading_engine:
                is_ready = False
                reasons.append("Trading engine not initialized")
            
            # Check blockchain connection
            if self.blockchain_data and not self.blockchain_data.is_connected():
                is_ready = False
                reasons.append("Blockchain not connected")
            
            if is_ready:
                return web.json_response({"status": "ready"})
            else:
                return web.json_response({
                    "status": "not_ready",
                    "reasons": reasons
                }, status=503)
                
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return web.json_response({
                "status": "not_ready",
                "error": str(e)
            }, status=503)
    
    async def liveness_check(self, request: web.Request) -> web.Response:
        """Kubernetes liveness probe"""
        # Simply check if the service is running
        return web.json_response({
            "status": "alive",
            "timestamp": time.time()
        })
    
    async def get_status(self, request: web.Request) -> web.Response:
        """Get detailed system status"""
        try:
            status = {
                "timestamp": time.time(),
                "uptime_seconds": time.time() - self.start_time,
                "uptime_formatted": self._format_uptime(time.time() - self.start_time)
            }
            
            if self.trading_engine:
                stats = self.trading_engine.get_stats()
                status["trading"] = {
                    "is_running": stats.get("is_running", False),
                    "total_profit": stats.get("total_profit", 0),
                    "trades_executed": stats.get("trades_executed", 0),
                    "win_rate": stats.get("win_rate", 0),
                    "active_strategy": stats.get("active_strategy", "unknown")
                }
            
            if self.reliability_manager:
                status["reliability"] = self.reliability_manager.get_status()
            
            if self.blockchain_data:
                status["blockchain"] = {
                    "connected": self.blockchain_data.is_connected(),
                    "block_number": self.blockchain_data.get_block_number() if self.blockchain_data.is_connected() else 0
                }
            
            return web.json_response(status)
            
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return web.json_response({
                "error": str(e)
            }, status=500)
    
    async def get_metrics(self, request: web.Request) -> web.Response:
        """Get Prometheus-compatible metrics"""
        try:
            metrics_lines = []
            
            # Uptime
            uptime = time.time() - self.start_time
            metrics_lines.append(f"# HELP system_uptime_seconds System uptime in seconds")
            metrics_lines.append(f"# TYPE system_uptime_seconds gauge")
            metrics_lines.append(f"system_uptime_seconds {uptime}")
            
            if self.trading_engine:
                stats = self.trading_engine.get_stats()
                
                # Trading metrics
                metrics_lines.append(f"# HELP trading_total_profit Total profit in USD")
                metrics_lines.append(f"# TYPE trading_total_profit gauge")
                metrics_lines.append(f"trading_total_profit {stats.get('total_profit', 0)}")
                
                metrics_lines.append(f"# HELP trading_trades_executed Total number of trades executed")
                metrics_lines.append(f"# TYPE trading_trades_executed counter")
                metrics_lines.append(f"trading_trades_executed {stats.get('trades_executed', 0)}")
                
                metrics_lines.append(f"# HELP trading_trades_skipped Total number of trades skipped")
                metrics_lines.append(f"# TYPE trading_trades_skipped counter")
                metrics_lines.append(f"trading_trades_skipped {stats.get('trades_skipped', 0)}")
                
                metrics_lines.append(f"# HELP trading_win_rate Win rate percentage")
                metrics_lines.append(f"# TYPE trading_win_rate gauge")
                metrics_lines.append(f"trading_win_rate {stats.get('win_rate', 0)}")
            
            return web.Response(text="\n".join(metrics_lines) + "\n", content_type="text/plain")
            
        except Exception as e:
            logger.error(f"Metrics check failed: {e}")
            return web.Response(text=f"# Error: {e}\n", status=500)
    
    async def _run_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        checks = {}
        
        # Check 1: Basic system
        checks["system"] = {
            "status": "healthy",
            "message": "System operational",
            "timestamp": time.time()
        }
        
        # Check 2: Trading engine
        if self.trading_engine:
            if self.trading_engine.is_running:
                checks["trading_engine"] = {
                    "status": "healthy",
                    "message": "Trading engine running"
                }
            else:
                checks["trading_engine"] = {
                    "status": "degraded",
                    "message": "Trading engine not running"
                }
        else:
            checks["trading_engine"] = {
                "status": "degraded",
                "message": "Trading engine not initialized"
            }
        
        # Check 3: Blockchain connection
        if self.blockchain_data:
            if self.blockchain_data.is_connected():
                checks["blockchain"] = {
                    "status": "healthy",
                    "message": f"Connected (block {self.blockchain_data.get_block_number()})"
                }
            else:
                checks["blockchain"] = {
                    "status": "unhealthy",
                    "message": "Not connected to blockchain"
                }
        else:
            checks["blockchain"] = {
                "status": "degraded",
                "message": "Blockchain data manager not initialized"
            }
        
        # Check 4: Reliability manager
        if self.reliability_manager:
            health = self.reliability_manager.get_health()
            checks["reliability"] = {
                "status": "healthy" if health == "healthy" else "degraded",
                "message": f"Health: {health}"
            }
        else:
            checks["reliability"] = {
                "status": "degraded",
                "message": "Reliability manager not initialized"
            }
        
        return checks
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        elif seconds < 86400:
            return f"{seconds/3600:.1f}h"
        else:
            return f"{seconds/86400:.1f}d"
    
    async def start_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Start health check server"""
        app = self.setup()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        logger.info(f"Health check server started on {host}:{port}")


async def create_health_server(
    trading_engine=None,
    reliability_manager=None,
    blockchain_data=None,
    host: str = "0.0.0.0",
    port: int = 8000
) -> HealthCheckEndpoint:
    """Create and start health check server"""
    health_endpoint = HealthCheckEndpoint(
        trading_engine=trading_engine,
        reliability_manager=reliability_manager,
        blockchain_data=blockchain_data
    )
    
    await health_endpoint.start_server(host, port)
    return health_endpoint
