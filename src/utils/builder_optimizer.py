"""
Builder Acceptance Optimizer
Multi-relay routing, reputation system, timing heuristics
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


class BuilderStatus(Enum):
    """Builder operational status"""
    UNKNOWN = "unknown"
    ACTIVE = "active"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass
class BuilderMetrics:
    """Per-builder metrics"""
    name: str
    endpoint: str
    acceptance_rate: float
    avg_latency_ms: float
    total_submissions: int
    successful_submissions: int
    last_success: float
    last_failure: float
    reputation_score: float  # 0-1
    is_preferred: bool


class BuilderAcceptanceOptimizer:
    """
    Optimizes builder selection for maximum acceptance
    - Multi-relay routing
    - Reputation system
    - Timing heuristics
    - Adaptive bundle sizing
    """
    
    # Known builders with endpoints
    BUILDERS = {
        "flashbots": {
            "endpoint": "https://relay.flashbots.net",
            "priority": 1,
            "type": "mev-boost"
        },
        "builder0x69": {
            "endpoint": "https://builder0x69.io",
            "priority": 2,
            "type": "mev-boost"
        },
        "eden": {
            "endpoint": "https://api.edennetwork.io/v1/bundle",
            "priority": 3,
            "type": "rpc"
        },
        "blocknative": {
            "endpoint": "https://api.blocknative.com/v1/bundle",
            "priority": 4,
            "type": "rpc"
        },
        "beaver": {
            "endpoint": "https://rpc.beaverbuild.org",
            "priority": 5,
            "type": "mev-boost"
        },
        "titan": {
            "endpoint": "https://rpc.titanbuilder.xyz",
            "priority": 6,
            "type": "mev-boost"
        },
    }
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Builder tracking
        self.builder_metrics: Dict[str, BuilderMetrics] = {}
        
        # Initialize all builders
        for name, info in self.BUILDERS.items():
            self.builder_metrics[name] = BuilderMetrics(
                name=name,
                endpoint=info["endpoint"],
                acceptance_rate=0.0,
                avg_latency_ms=1000.0,
                total_submissions=0,
                successful_submissions=0,
                last_success=0,
                last_failure=0,
                reputation_score=0.5,
                is_preferred=info["priority"] <= 2
            )
        
        # History
        self.submission_history = deque(maxlen=100)
        
        # Timing
        self.block_timing = deque(maxlen=10)  # Track block times
        
        # Adaptive parameters
        self.bundle_value_threshold = config.get("bundle_value_threshold", 10)  # $10 minimum
        self.retry_count = config.get("retry_count", 3)
        
        # State
        self.is_running = False
    
    def start(self):
        """Start optimizer"""
        self.is_running = True
        logger.info("🎯 Builder Acceptance Optimizer started")
    
    def stop(self):
        """Stop optimizer"""
        self.is_running = False
    
    # ============== SUBMISSION ==============
    
    async def submit_bundle(
        self,
        bundle: Dict,
        expected_value: float
    ) -> Optional[str]:
        """
        Submit bundle with optimized builder selection
        Returns bundle hash if accepted
        """
        if not self.is_running:
            return None
        
        # Check minimum value threshold
        if expected_value < self.bundle_value_threshold:
            logger.warning(f"Bundle value ${expected_value} below threshold ${self.bundle_value_threshold}")
            return None
        
        # Get best builders in order
        builders = self._get_best_builders()
        
        # Try each builder
        last_error = None
        for builder_name in builders:
            try:
                result = await self._submit_to_builder(
                    builder_name,
                    bundle,
                    expected_value
                )
                
                if result:
                    self._record_success(builder_name, result)
                    logger.info(f"✅ Bundle accepted by {builder_name}")
                    return result
                else:
                    self._record_failure(builder_name)
                    
            except Exception as e:
                logger.warning(f"Builder {builder_name} error: {e}")
                last_error = e
                continue
        
        logger.error(f"All builders failed: {last_error}")
        return None
    
    async def _submit_to_builder(
        self,
        builder_name: str,
        bundle: Dict,
        expected_value: float
    ) -> Optional[str]:
        """Submit to specific builder"""
        import aiohttp
        
        metrics = self.builder_metrics[builder_name]
        
        # Calculate optimal gas based on builder history
        gas_multiplier = self._calculate_gas_multiplier(metrics)
        
        # Build payload with optimization hints
        payload = self._build_optimized_payload(bundle, expected_value, gas_multiplier)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    metrics.endpoint,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("result", {}).get("bundleHash")
                    else:
                        return None
                        
        except Exception as e:
            logger.debug(f"Submit to {builder_name} failed: {e}")
            return None
    
    def _build_optimized_payload(
        self,
        bundle: Dict,
        expected_value: float,
        gas_multiplier: float
    ) -> Dict:
        """Build optimized bundle payload"""
        # Add metadata for builder
        payload = {
            **bundle,
            "_meta": {
                "expected_value": expected_value,
                "gas_multiplier": gas_multiplier,
                "submitted_at": time.time(),
                "optimizer_version": "1.0"
            }
        }
        
        # Builder-specific optimizations
        # Flashbots prefers full packets
        # Others prefer simpler bundles
        
        return payload
    
    def _calculate_gas_multiplier(self, metrics: BuilderMetrics) -> float:
        """Calculate gas multiplier based on builder history"""
        # Higher gas for lower reputation builders
        base = 1.0
        
        # Adjust based on acceptance rate
        if metrics.acceptance_rate < 0.3:
            return base * 1.5
        elif metrics.acceptance_rate < 0.5:
            return base * 1.2
        
        return base
    
    # ============== BUILDER SELECTION ==============
    
    def _get_best_builders(self) -> List[str]:
        """Get builders in priority order based on reputation"""
        # Sort by reputation score
        sorted_builders = sorted(
            self.builder_metrics.values(),
            key=lambda b: (
                b.is_preferred,  # Prefer preferred first
                -b.avg_latency_ms,  # Lower latency better
                -b.acceptance_rate,  # Higher acceptance better
                -b.reputation_score  # Higher reputation better
            ),
            reverse=True
        )
        
        return [b.name for b in sorted_builders]
    
    def _get_preferred_builder(self) -> Optional[str]:
        """Get the currently preferred builder"""
        best = max(
            self.builder_metrics.values(),
            key=lambda b: b.reputation_score * (1 / max(b.avg_latency_ms, 1))
        )
        
        return best.name if best.reputation_score > 0.1 else None
    
    # ============== RECORDING ==============
    
    def _record_success(self, builder_name: str, result: str):
        """Record successful submission"""
        metrics = self.builder_metrics[builder_name]
        
        metrics.total_submissions += 1
        metrics.successful_submissions += 1
        metrics.last_success = time.time()
        
        # Update acceptance rate
        metrics.acceptance_rate = (
            metrics.successful_submissions / metrics.total_submissions
        )
        
        # Update reputation (exponential moving average)
        metrics.reputation_score = (
            0.9 * metrics.reputation_score + 0.1 * 1.0
        )
        
        self.submission_history.append({
            "builder": builder_name,
            "success": True,
            "timestamp": time.time()
        })
    
    def _record_failure(self, builder_name: str):
        """Record failed submission"""
        metrics = self.builder_metrics[builder_name]
        
        metrics.total_submissions += 1
        metrics.last_failure = time.time()
        
        # Update acceptance rate
        metrics.acceptance_rate = (
            metrics.successful_submissions / metrics.total_submissions
        )
        
        # Update reputation penalty
        metrics.reputation_score = max(0, metrics.reputation_score - 0.1)
        
        self.submission_history.append({
            "builder": builder_name,
            "success": False,
            "timestamp": time.time()
        })
    
    # ============== TIMING HEURISTICS ==============
    
    def record_block_time(self, block_time_ms: float):
        """Record time between blocks"""
        self.block_timing.append(block_time_ms)
    
    def get_optimal_submission_time(self) -> float:
        """Get optimal time to submit (ms into block)"""
        if not self.block_timing:
            return 5000  # Default: 5 seconds into block
        
        avg_block_time = sum(self.block_timing) / len(self.block_timing)
        
        # Submit in first third of block for best inclusion
        return avg_block_time / 3
    
    def should_retry(self, attempt: int, last_success: float) -> bool:
        """Decide if should retry based on timing"""
        if attempt >= self.retry_count:
            return False
        
        # Don't retry if last success was too recent (builder may be busy)
        time_since_success = time.time() - last_success
        if time_since_success < 1.0:  # Less than 1 second
            return False
        
        return True
    
    # ============== METRICS ==============
    
    def get_metrics(self) -> Dict:
        """Get current optimizer metrics"""
        return {
            builder_name: {
                "acceptance_rate": m.acceptance_rate,
                "avg_latency_ms": m.avg_latency_ms,
                "reputation_score": m.reputation_score,
                "total_submissions": m.total_submissions,
                "is_preferred": m.is_preferred
            }
            for builder_name, m in self.builder_metrics.items()
        }
    
    def get_best_builder(self) -> Optional[str]:
        """Get currently best performing builder"""
        if not self.builder_metrics:
            return None
        
        return max(
            self.builder_metrics.values(),
            key=lambda b: b.reputation_score * b.acceptance_rate
        ).name


# Factory
def create_builder_optimizer(config: Dict = None) -> BuilderAcceptanceOptimizer:
    """Create builder optimizer instance"""
    return BuilderAcceptanceOptimizer(config or {})
