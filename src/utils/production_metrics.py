"""
Production Metrics System
Real measurable outputs - NOT just logging

This is what safety_system SHOULD produce:
- per_layer_metrics
- simulation_mismatch_rate  
- bundle_inclusion_rate_by_relay
- avg_cost_per_attempt_usd
- revert_reason_histogram
- opportunity_decay_median_ms
- hard_gates
- post_trade_reconciliation_ledger
"""

import asyncio
import time
import json
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import statistics


class MetricType(Enum):
    """Types of metrics we track"""
    SIMULATION = "simulation"
    BUILDER = "builder"
    GAS = "gas"
    TOKEN = "token"
    NONCE = "nonce"
    OPPORTUNITY = "opportunity"


@dataclass
class TradeAttempt:
    """Single trade attempt with full context"""
    attempt_id: str
    opportunity_id: str
    timestamp: float
    
    # Expected (simulation)
    expected_profit: float
    expected_gas: int
    expected_success: bool
    
    # Actual (realized)
    realized_profit: Optional[float] = None
    realized_gas: Optional[int] = None
    realized_success: Optional[bool] = None
    revert_reason: Optional[str] = None
    
    # Timing
    latency_ms: float = 0
    block_number: Optional[int] = None
    
    # Additional
    relay_used: Optional[str] = None
    attempts_count: int = 1


@dataclass 
class LayerMetrics:
    """Metrics for a specific layer"""
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    latency_p50_ms: float = 0
    latency_p99_ms: float = 0
    
    # Layer-specific
    mismatches: int = 0  # simulation != reality
    

class ProductionMetrics:
    """
    REAL metrics system that tracks EVERYTHING
    Outputs are MEASURABLE, not just logs
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # ═══════════════════════════════════════════════════════════
        # 1. SIMULATION LAYER METRICS
        # ═══════════════════════════════════════════════════════════
        self.simulation_metrics = LayerMetrics()
        self.simulation_results: deque = deque(maxlen=1000)  # expected vs realized
        
        # ═══════════════════════════════════════════════════════════
        # 2. BUILDER/RELAY METRICS
        # ═══════════════════════════════════════════════════════════
        self.builder_metrics: Dict[str, LayerMetrics] = defaultdict(LayerMetrics)
        self.bundle_submissions: deque = deque(maxlen=500)
        
        # ═══════════════════════════════════════════════════════════
        # 3. GAS METRICS
        # ═══════════════════════════════════════════════════════════
        self.gas_spent_total: float = 0
        self.gas_spent_hourly: float = 0
        self.hour_start = time.time()
        self.gas_by_opportunity: Dict[str, List[float]] = defaultdict(list)
        
        # ═══════════════════════════════════════════════════════════
        # 4. TOKEN METRICS
        # ═══════════════════════════════════════════════════════════
        self.token_approval_leaks: List[Dict] = []
        self.allowance_stuck: List[Dict] = []
        self.fee_on_transfer_detected: Set[str] = set()
        
        # ═══════════════════════════════════════════════════════════
        # 5. NONCE METRICS  
        # ═══════════════════════════════════════════════════════════
        self.nonce_collisions: int = 0
        self.pending_tx: Dict[str, int] = {}  # address -> nonce
        self.nonce_locks: Dict[str, asyncio.Lock] = {}
        
        # ═══════════════════════════════════════════════════════════
        # 6. OPPORTUNITY METRICS
        # ═══════════════════════════════════════════════════════════
        self.opportunity_decay_ms: deque = deque(maxlen=500)
        self.opportunities_found: int = 0
        self.opportunities_executed: int = 0
        
        # ═══════════════════════════════════════════════════════════
        # 7. REVERT REASONS
        # ═══════════════════════════════════════════════════════════
        self.revert_histogram: Dict[str, int] = defaultdict(int)
        
        # ═══════════════════════════════════════════════════════════
        # 8. TRADE ATTEMPTS (full ledger)
        # ═══════════════════════════════════════════════════════════
        self.trade_attempts: List[TradeAttempt] = []
        self.current_attempts: Dict[str, TradeAttempt] = {}
        
        # ═══════════════════════════════════════════════════════════
        # HARD GATES (configurable limits)
        # ═══════════════════════════════════════════════════════════
        self.hard_gates = {
            "max_attempts_per_opportunity": config.get("max_attempts", 3),
            "max_total_gas_spend_per_hour_usd": config.get("max_gas_hourly", 1000),
            "min_inclusion_probability": config.get("min_inclusion_prob", 0.3),
            "max_simulation_mismatch_rate": config.get("max_sim_mismatch", 0.02),
        }
    
    # ═══════════════════════════════════════════════════════════
    # RECORDING METHODS - These are called during operation
    # ═══════════════════════════════════════════════════════════
    
    def record_simulation(self, opp_id: str, expected: Dict, actual: Dict):
        """Record simulation vs reality comparison"""
        self.simulation_metrics.total_requests += 1
        
        # Check for mismatch
        profit_match = abs(expected.get("profit", 0) - actual.get("profit", 0)) < 0.01
        gas_match = abs(expected.get("gas", 0) - actual.get("gas", 0)) < 1000
        
        if not profit_match or not gas_match:
            self.simulation_metrics.mismatches += 1
        
        # Store result
        self.simulation_results.append({
            "opp_id": opp_id,
            "expected": expected,
            "actual": actual,
            "timestamp": time.time()
        })
        
        if actual.get("success"):
            self.simulation_metrics.successful += 1
        else:
            self.simulation_metrics.failed += 1
            
            # Record revert reason
            reason = actual.get("revert_reason", "unknown")
            self.revert_histogram[reason] += 1
    
    def record_bundle_submission(self, relay: str, bundle_id: str, included: bool, latency_ms: float):
        """Record bundle submission and outcome"""
        if relay not in self.builder_metrics:
            self.builder_metrics[relay] = LayerMetrics()
        
        metrics = self.builder_metrics[relay]
        metrics.total_requests += 1
        
        if included:
            metrics.successful += 1
        else:
            metrics.failed += 1
        
        self.bundle_submissions.append({
            "relay": relay,
            "bundle_id": bundle_id,
            "included": included,
            "latency_ms": latency_ms,
            "timestamp": time.time()
        })
    
    def record_gas_spent(self, opp_id: str, gas_eth: float):
        """Record gas spent"""
        self.gas_spent_total += gas_eth
        self.gas_spent_hourly += gas_eth
        self.gas_by_opportunity[opp_id].append(gas_eth)
        
        # Reset hourly
        if time.time() - self.hour_start > 3600:
            self.gas_spent_hourly = 0
            self.hour_start = time.time()
    
    def record_nonce_collision(self, address: str, expected_nonce: int, actual_nonce: int):
        """Record nonce collision"""
        self.nonce_collisions += 1
    
    def record_opportunity_decay(self, discovered_ms: float, executed_ms: float):
        """Record how fast we executed"""
        decay = executed_ms - discovered_ms
        self.opportunity_decay_ms.append(decay)
        self.opportunities_found += 1
    
    def start_trade_attempt(self, attempt: TradeAttempt):
        """Start tracking a trade attempt"""
        key = f"{attempt.opportunity_id}_{attempt.attempts_count}"
        self.current_attempts[key] = attempt
    
    def end_trade_attempt(self, key: str, realized: Dict):
        """Complete a trade attempt"""
        if key in self.current_attempts:
            attempt = self.current_attempts[key]
            attempt.realized_profit = realized.get("profit")
            attempt.realized_gas = realized.get("gas_used")
            attempt.realized_success = realized.get("success")
            attempt.revert_reason = realized.get("revert_reason")
            
            self.trade_attempts.append(attempt)
            del self.current_attempts[key]
            
            if realized.get("success"):
                self.opportunities_executed += 1
    
    # ═══════════════════════════════════════════════════════════
    # HARD GATE CHECKS - These STOP execution if violated
    # ═══════════════════════════════════════════════════════════
    
    def check_hard_gates(self) -> Tuple[bool, List[str]]:
        """
        Check all hard gates
        Returns: (can_continue, violations)
        """
        violations = []
        
        # 1. Max attempts per opportunity
        for key, attempt in self.current_attempts.items():
            if attempt.attempts_count > self.hard_gates["max_attempts_per_opportunity"]:
                violations.append(f"MAX_ATTEMPTS: {attempt.attempts_count} > {self.hard_gates['max_attempts_per_opportunity']}")
        
        # 2. Max gas per hour
        if self.gas_spent_hourly > self.hard_gates["max_total_gas_spend_per_hour_usd"]:
            violations.append(f"MAX_GAS_HOURLY: ${self.gas_spent_hourly:.2f} > ${self.hard_gates['max_total_gas_spend_per_hour_usd']}")
        
        # 3. Simulation mismatch rate
        if self.simulation_metrics.total_requests > 10:
            mismatch_rate = self.simulation_metrics.mismatches / self.simulation_metrics.total_requests
            if mismatch_rate > self.hard_gates["max_simulation_mismatch_rate"]:
                violations.append(f"SIM_MISMATCH: {mismatch_rate*100:.1f}% > {self.hard_gates['max_simulation_mismatch_rate']*100}%")
        
        # 4. Inclusion probability (if we have data)
        if len(self.bundle_submissions) >= 10:
            recent = list(self.bundle_submissions)[-10:]
            inclusion_rate = sum(1 for b in recent if b["included"]) / len(recent)
            if inclusion_rate < self.hard_gates["min_inclusion_probability"]:
                violations.append(f"INCLUSION_RATE: {inclusion_rate*100:.1f}% < {self.hard_gates['min_inclusion_probability']*100}%")
        
        return len(violations) == 0, violations
    
    # ═══════════════════════════════════════════════════════════
    # OUTPUTS - Real measurable data
    # ═══════════════════════════════════════════════════════════
    
    def get_per_layer_metrics(self) -> Dict:
        """Get metrics for each layer"""
        return {
            "simulation": {
                "total": self.simulation_metrics.total_requests,
                "successful": self.simulation_metrics.successful,
                "failed": self.simulation_metrics.failed,
                "mismatch_rate": (
                    self.simulation_metrics.mismatches / max(1, self.simulation_metrics.total_requests)
                ),
            },
            "builders": {
                relay: {
                    "total": m.total_requests,
                    "included": m.successful,
                    "rate": m.successful / max(1, m.total_requests)
                }
                for relay, m in self.builder_metrics.items()
            },
            "gas": {
                "total_eth": self.gas_spent_total,
                "hourly_eth": self.gas_spent_hourly,
            },
            "nonce": {
                "collisions": self.nonce_collisions,
            },
            "opportunities": {
                "found": self.opportunities_found,
                "executed": self.opportunities_executed,
                "decay_median_ms": statistics.median(self.opportunity_decay_ms) if self.opportunity_decay_ms else 0,
            }
        }
    
    def get_simulation_mismatch_rate(self) -> float:
        """Get simulation vs reality mismatch rate"""
        if self.simulation_metrics.total_requests == 0:
            return 0
        return self.simulation_metrics.mismatches / self.simulation_metrics.total_requests
    
    def get_bundle_inclusion_by_relay(self) -> Dict[str, float]:
        """Get inclusion rate by relay"""
        result = {}
        for relay, metrics in self.builder_metrics.items():
            if metrics.total_requests > 0:
                result[relay] = metrics.successful / metrics.total_requests
        return result
    
    def get_avg_cost_per_attempt_usd(self) -> float:
        """Average gas cost per attempt in USD"""
        all_gas = []
        for gas_list in self.gas_by_opportunity.values():
            all_gas.extend(gas_list)
        
        if not all_gas:
            return 0
        
        # Assume ETH price
        eth_price = 1800  # Would fetch dynamically
        avg_gas_eth = statistics.mean(all_gas)
        
        return avg_gas_eth * eth_price
    
    def get_revert_histogram(self) -> Dict[str, int]:
        """Get histogram of revert reasons"""
        return dict(self.revert_histogram)
    
    def get_opportunity_decay_median_ms(self) -> float:
        """Median opportunity decay in ms"""
        if not self.opportunity_decay_ms:
            return 0
        return statistics.median(self.opportunity_decay_ms)
    
    def get_post_trade_ledger(self) -> List[Dict]:
        """
        Expected vs Realized ledger for EVERY trade
        This is the KEY output for reconciliation
        """
        ledger = []
        
        for attempt in self.trade_attempts:
            ledger.append({
                "attempt_id": attempt.attempt_id,
                "opportunity_id": attempt.opportunity_id,
                "timestamp": attempt.timestamp,
                
                # Expected (from simulation)
                "expected_profit": attempt.expected_profit,
                "expected_gas": attempt.expected_gas,
                "expected_success": attempt.expected_success,
                
                # Realized (actual execution)
                "realized_profit": attempt.realized_profit,
                "realized_gas": attempt.realized_gas,
                "realized_success": attempt.realized_success,
                "revert_reason": attempt.revert_reason,
                
                # Delta
                "profit_delta": (
                    (attempt.realized_profit or 0) - attempt.expected_profit
                    if attempt.realized_profit is not None else None
                ),
                "gas_delta": (
                    (attempt.realized_gas or 0) - attempt.expected_gas
                    if attempt.realized_gas is not None else None
                ),
                
                # Metadata
                "latency_ms": attempt.latency_ms,
                "relay": attempt.relay_used,
                "attempts_count": attempt.attempts_count,
            })
        
        return ledger
    
    def get_full_report(self) -> Dict:
        """
        FULL PRODUCTION REPORT
        This is what a REAL system produces
        """
        can_continue, violations = self.check_hard_gates()
        
        return {
            "timestamp": time.time(),
            
            # Can we continue operating?
            "system_healthy": can_continue,
            "violations": violations,
            
            # Per-layer metrics
            "per_layer_metrics": self.get_per_layer_metrics(),
            
            # Key KPIs
            "kpis": {
                "simulation_mismatch_rate": self.get_simulation_mismatch_rate(),
                "bundle_inclusion_rate_by_relay": self.get_bundle_inclusion_by_relay(),
                "avg_cost_per_attempt_usd": self.get_avg_cost_per_attempt_usd(),
                "revert_histogram": self.get_revert_histogram(),
                "opportunity_decay_median_ms": self.get_opportunity_decay_median_ms(),
            },
            
            # Hard gates status
            "hard_gates": self.hard_gates,
            
            # Full ledger
            "post_trade_ledger": self.get_post_trade_ledger()[-100:],  # Last 100
            
            # Warnings
            "warnings": self._generate_warnings(),
        }
    
    def _generate_warnings(self) -> List[str]:
        """Generate warnings based on metrics"""
        warnings = []
        
        # High revert rate
        if self.simulation_metrics.total_requests > 20:
            revert_rate = self.simulation_metrics.failed / self.simulation_metrics.total_requests
            if revert_rate > 0.05:
                warnings.append(f"HIGH REVERT RATE: {revert_rate*100:.1f}%")
        
        # High nonce collisions
        if self.nonce_collisions > 0:
            warnings.append(f"NONCE COLLISIONS: {self.nonce_collisions}")
        
        # Slow opportunities
        median_decay = self.get_opportunity_decay_median_ms()
        if median_decay > 500:
            warnings.append(f"SLOW OPPORTUNITIES: {median_decay:.0f}ms median")
        
        # Gas issues
        if self.gas_spent_hourly > self.hard_gates["max_total_gas_spend_per_hour_usd"] * 0.8:
            warnings.append(f"GAS HOURLY NEAR LIMIT: ${self.gas_spent_hourly:.2f}")
        
        return warnings


# Helper for type hints
from typing import Tuple


# ═══════════════════════════════════════════════════════════
# EXAMPLE USAGE
# ═══════════════════════════════════════════════════════════

async def example_usage():
    """Example of how to use the metrics system"""
    
    # Initialize
    metrics = ProductionMetrics({
        "max_attempts": 3,
        "max_gas_hourly": 1000,
        "min_inclusion_prob": 0.3,
        "max_sim_mismatch": 0.02,
    })
    
    # 1. Record a simulation
    metrics.record_simulation(
        opp_id="opp_123",
        expected={"profit": 50.0, "gas": 200000, "success": True},
        actual={"profit": 49.50, "gas": 205000, "success": True}
    )
    
    # 2. Record bundle submission
    metrics.record_bundle_submission(
        relay="flashbots",
        bundle_id="bundle_123",
        included=True,
        latency_ms=45
    )
    
    # 3. Record gas spent
    metrics.record_gas_spent("opp_123", 0.05)  # 0.05 ETH
    
    # 4. Check hard gates before next trade
    can_continue, violations = metrics.check_hard_gates()
    if not can_continue:
        print(f"STOPPED: {violations}")
        return
    
    # 5. Get full report
    report = metrics.get_full_report()
    
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(example_usage())
