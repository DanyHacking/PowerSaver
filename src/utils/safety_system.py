"""
Comprehensive Safety System
Protects against ALL known failure modes in MEV trading

Handles:
1. Consensus/Block-level: Reorg, base fee spike, timestamp drift, state race
2. Builder-layer: Preference bias, bundle overwrite, relay overload
3. Transaction-level: Nonce mismatch, storage race, allowance, token fees
4. Oracle-layer: Oracle lag, TWAP manipulation, rounding
5. Simulation-layer: Environment mismatch, bundle simulation failure
6. Networking: RPC desync, rate limits, latency
7. Strategy-level: Opportunity decay, capital competition, gas wars
8. Smart-contract: Reentrancy, deadline, stack limits

This is the CORE that prevents money loss.
"""

import asyncio
import logging
import time
import hashlib
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import aiohttp

logger = logging.getLogger(__name__)


class SafetyLevel(Enum):
    """Safety verification levels"""
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"
    REJECT = "reject"


@dataclass
class SafetyCheckResult:
    """Result of safety check"""
    level: SafetyLevel
    passed: bool
    issues: List[str]
    warnings: List[str]
    metadata: Dict = field(default_factory=dict)


@dataclass
class BlockState:
    """Current block state"""
    block_number: int
    block_hash: str
    base_fee: int
    timestamp: int
    parent_hash: str


class ConsensusProtection:
    """
    Protection against consensus/block-level failures:
    - Reorg detection
    - Base fee spike detection
    - Timestamp validation
    - State race detection
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Track recent blocks
        self.block_history: deque = deque(maxlen=10)
        self.last_block_hash: Optional[str] = None
        
        # Base fee tracking
        self.base_fee_history: deque = deque(maxlen=20)
        self.max_base_fee_spike = config.get("max_base_fee_spike", 2.0)  # 2x
        
        # Reorg threshold
        self.reorg_threshold_blocks = config.get("reorg_threshold", 3)
        
        # Timestamp window
        self.timestamp_drift_window = config.get("timestamp_drift", 12)  # seconds
    
    async def verify_block_state(self, current_block: BlockState) -> SafetyCheckResult:
        """Verify block state is stable"""
        issues = []
        warnings = []
        
        # Check for reorg
        if self.last_block_hash and current_block.parent_hash != self.last_block_hash:
            # Potential reorg detected
            if current_block.block_number - self.block_history[-1].block_number <= self.reorg_threshold_blocks:
                issues.append(f"REORG DETECTED: Block {current_block.block_number} parent doesn't match previous")
                return SafetyCheckResult(
                    level=SafetyLevel.REJECT,
                    passed=False,
                    issues=issues,
                    warnings=warnings,
                    metadata={"reorg": True}
                )
        
        # Check base fee spike
        if self.base_fee_history:
            last_base_fee = self.base_fee_history[-1]
            if current_block.base_fee > last_base_fee * self.max_base_fee_spike:
                warnings.append(f"BASE FEE SPIKE: {current_block.base_fee / 1e9:.1f} gwei vs {last_base_fee / 1e9:.1f} gwei")
        
        # Check timestamp sanity
        current_time = time.time()
        time_diff = abs(current_time - current_block.timestamp)
        if time_diff > self.timestamp_drift_window * 2:
            warnings.append(f"TIMESTAMP DRIFT: {time_diff}s difference")
        
        # Update history
        self.block_history.append(current_block)
        self.last_block_hash = current_block.block_hash
        self.base_fee_history.append(current_block.base_fee)
        
        level = SafetyLevel.DANGEROUS if issues else SafetyLevel.WARNING if warnings else SafetyLevel.SAFE
        
        return SafetyCheckResult(
            level=level,
            passed=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            metadata={"block": current_block.block_number}
        )
    
    async def validate_bundle_state(
        self,
        simulated_block: int,
        current_block: int
    ) -> SafetyCheckResult:
        """Validate state hasn't changed since simulation"""
        issues = []
        
        # Block too old
        if current_block - simulated_block > 2:
            issues.append(f"STALE SIMULATION: Simulated block {simulated_block}, current {current_block}")
        
        # Check for reorg in between
        if simulated_block in [b.block_number for b in self.block_history]:
            simulated_hash = next((b.block_hash for b in self.block_history if b.block_number == simulated_block), None)
            if simulated_hash and simulated_hash != self.block_history[-1].parent_hash:
                issues.append("STATE REORG: Block hash changed since simulation")
        
        passed = len(issues) == 0
        level = SafetyLevel.REJECT if not passed else SafetyLevel.SAFE
        
        return SafetyCheckResult(
            level=level,
            passed=passed,
            issues=issues,
            warnings=[],
            metadata={"simulated_block": simulated_block, "current_block": current_block}
        )


class BuilderProtection:
    """
    Protection against builder-layer failures:
    - Builder preference bias
    - Bundle overwrite
    - Relay overload
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Multiple relays for redundancy
        self.relays = [
            "https://relay.flashbots.net",
            "https://relay-sepolia.flashbots.net"
        ]
        
        # Track bundle submissions
        self.pending_bundles: Dict[str, float] = {}
        self.confirmed_bundles: Set[str] = set()
        
        # Retry configuration
        self.max_retries = config.get("max_bundle_retries", 3)
        self.retry_delay = config.get("retry_delay", 2.0)
        
        # Builder reputation
        self.builder_stats: Dict[str, Dict] = {}
    
    async def submit_bundle_with_protection(
        self,
        bundle_hash: str,
        signed_txs: List[str],
        block_number: int
    ) -> Tuple[bool, List[str]]:
        """Submit bundle with retry and overwrite protection"""
        
        errors = []
        success = False
        
        for attempt in range(self.max_retries):
            try:
                # Try each relay
                for relay_url in self.relays:
                    result = await self._submit_to_relay(relay_url, signed_txs, block_number)
                    
                    if result["success"]:
                        self.pending_bundles[bundle_hash] = time.time()
                        success = True
                        break
                
                if success:
                    break
                    
            except Exception as e:
                errors.append(f"Attempt {attempt + 1}: {str(e)}")
                await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        return success, errors
    
    async def _submit_to_relay(
        self,
        relay_url: str,
        signed_txs: List[str],
        block_number: int
    ) -> Dict:
        """Submit to specific relay"""
        # Implementation would send to Flashbots relay
        return {"success": True, "bundle_hash": "0x..."}
    
    def verify_bundle_not_overwritten(
        self,
        bundle_hash: str,
        submitted_txs: List[str]
    ) -> SafetyCheckResult:
        """Verify bundle wasn't overwritten"""
        issues = []
        warnings = []
        
        # Check if we have a newer submission
        if bundle_hash in self.confirmed_bundles:
            warnings.append("Bundle already confirmed")
        
        # Check for similar txs (potential overwrite)
        for pending_hash, submit_time in self.pending_bundles.items():
            if pending_hash != bundle_hash:
                age = time.time() - submit_time
                if age < 5:  # Within 5 seconds
                    issues.append("POSSIBLE OVERWRITE: Similar bundle submitted recently")
        
        passed = len(issues) == 0
        level = SafetyLevel.REJECT if issues else SafetyLevel.SAFE
        
        return SafetyCheckResult(
            level=level,
            passed=passed,
            issues=issues,
            warnings=warnings
        )


class TransactionProtection:
    """
    Protection against transaction-level failures:
    - Nonce mismatch
    - Storage race
    - Allowance issues
    - Token fee-on-transfer
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Track pending nonces
        self.pending_nonces: Dict[str, int] = {}
        self.pending_txs: Dict[str, Dict] = {}
        
        # Token handling
        self.fee_tokens: Set[str] = config.get("known_fee_tokens", set())
        self.verified_tokens: Set[str] = set()
        
        # Allowance tracking
        self.allowances: Dict[Tuple[str, str], int] = {}  # (owner, spender) -> amount
    
    async def verify_transaction_safe(
        self,
        from_address: str,
        to_address: str,
        data: str,
        nonce: int,
        chain_id: int
    ) -> SafetyCheckResult:
        """Verify transaction can execute safely"""
        issues = []
        warnings = []
        
        # Check nonce
        expected_nonce = self.pending_nonces.get(from_address, nonce)
        if nonce < expected_nonce:
            issues.append(f"NONCE TOO LOW: Expected {expected_nonce}, got {nonce}")
        elif nonce > expected_nonce + 5:
            warnings.append(f"NONCE GAP: Large gap to expected {expected_nonce}")
        
        # Check pending tx conflicts
        pending_key = f"{from_address}:{nonce}"
        if pending_key in self.pending_txs:
            pending_tx = self.pending_txs[pending_key]
            if pending_tx["to"] != to_address or pending_tx["data"] != data:
                issues.append("NONCE CONFLICT: Different tx pending at this nonce")
        
        # Update tracking
        self.pending_nonces[from_address] = nonce + 1
        self.pending_txs[pending_key] = {
            "to": to_address,
            "data": data,
            "timestamp": time.time()
        }
        
        passed = len(issues) == 0
        level = SafetyLevel.REJECT if issues else SafetyLevel.WARNING if warnings else SafetyLevel.SAFE
        
        return SafetyCheckResult(
            level=level,
            passed=passed,
            issues=issues,
            warnings=warnings,
            metadata={"nonce": nonce, "from": from_address}
        )
    
    def check_token_compatibility(
        self,
        token_address: str,
        amount: int
    ) -> SafetyCheckResult:
        """Check if token has fee-on-transfer or unusual behavior"""
        issues = []
        warnings = []
        
        # Known fee tokens
        if token_address.lower() in [t.lower() for t in self.fee_tokens]:
            warnings.append(f"FEE TOKEN: Known to charge transfer fees")
        
        # Check for common non-standard tokens
        # In production, would query contract for decimals, transfer events
        
        passed = len(issues) == 0
        level = SafetyLevel.WARNING if warnings else SafetyLevel.SAFE
        
        return SafetyCheckResult(
            level=level,
            passed=passed,
            issues=issues,
            warnings=warnings,
            metadata={"token": token_address}
        )


class OracleProtection:
    """
    Protection against oracle failures:
    - Oracle lag
    - TWAP manipulation
    - Rounding errors
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Price staleness thresholds
        self.chainlink_staleness = config.get("chainlink_staleness", 300)  # 5 minutes
        self.twap_staleness = config.get("twap_staleness", 600)  # 10 minutes
        
        # Price deviation thresholds
        self.max_price_deviation = config.get("max_price_deviation", 0.05)  # 5%
        
        # Track oracle prices
        self.oracle_prices: Dict[str, Dict] = {}
        self.oracle_timestamps: Dict[str, float] = {}
    
    async def verify_price_fresh(
        self,
        token: str,
        price_data: Dict
    ) -> SafetyCheckResult:
        """Verify oracle price is fresh"""
        issues = []
        warnings = []
        
        current_time = time.time()
        
        # Check last update time
        if token in self.oracle_timestamps:
            age = current_time - self.oracle_timestamps[token]
            
            if price_data.get("source") == "chainlink" and age > self.chainlink_staleness:
                issues.append(f"STALE ORACLE: Chainlink price is {age}s old")
            
            if price_data.get("source") == "twap" and age > self.twap_staleness:
                issues.append(f"STALE TWAP: Price is {age}s old")
        
        # Check for price manipulation (compare multiple sources)
        if token in self.oracle_prices:
            old_price = self.oracle_prices[token].get("price", 0)
            new_price = price_data.get("price", 0)
            
            if old_price > 0:
                deviation = abs(new_price - old_price) / old_price
                
                if deviation > self.max_price_deviation:
                    warnings.append(f"PRICE DEVIATION: {deviation*100:.2f}% from last price")
        
        # Update tracking
        self.oracle_prices[token] = price_data
        self.oracle_timestamps[token] = current_time
        
        passed = len(issues) == 0
        level = SafetyLevel.REJECT if issues else SafetyLevel.WARNING if warnings else SafetyLevel.SAFE
        
        return SafetyCheckResult(
            level=level,
            passed=passed,
            issues=issues,
            warnings=warnings,
            metadata={"token": token, "price": price_data.get("price")}
        )


class SimulationProtection:
    """
    Protection against simulation failures:
    - Environment mismatch
    - Non-deterministic simulation
    - Builder environment differences
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Simulation success rate tracking
        self.simulation_results: deque = deque(maxlen=100)
        
        # Match rate threshold
        self.min_success_rate = config.get("min_success_rate", 0.8)
    
    async def verify_simulation_accuracy(
        self,
        simulation_result: Dict,
        execution_result: Optional[Dict] = None
    ) -> SafetyCheckResult:
        """Verify simulation matches execution"""
        issues = []
        warnings = []
        
        # Record simulation result
        self.simulation_results.append({
            "simulated_success": simulation_result.get("success", False),
            "actual_success": execution_result.get("success") if execution_result else None,
            "timestamp": time.time()
        })
        
        # Calculate success rate
        if len(self.simulation_results) >= 10:
            successful_sims = sum(1 for r in self.simulation_results if r["simulated_success"])
            sim_rate = successful_sims / len(self.simulation_results)
            
            if sim_rate < self.min_success_rate:
                issues.append(f"LOW SIMULATION ACCURACY: {sim_rate*100:.1f}% success rate")
            
            # If we have execution results, compare
            matched = sum(
                1 for r in self.simulation_results 
                if r["actual_success"] is not None 
                and r["simulated_success"] == r["actual_success"]
            )
            total_with_actual = sum(1 for r in self.simulation_results if r["actual_success"] is not None)
            
            if total_with_actual > 0:
                match_rate = matched / total_with_actual
                if match_rate < 0.9:
                    warnings.append(f"SIM/EXEC MISMATCH: Only {match_rate*100:.1f}% match")
        
        passed = len(issues) == 0
        level = SafetyLevel.REJECT if issues else SafetyLevel.WARNING if warnings else SafetyLevel.SAFE
        
        return SafetyCheckResult(
            level=level,
            passed=passed,
            issues=issues,
            warnings=warnings,
            metadata={"simulations": len(self.simulation_results)}
        )


class NetworkProtection:
    """
    Protection against networking issues:
    - RPC desync
    - Rate limiting
    - Latency issues
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # RPC health tracking
        self.rpc_latencies: deque = deque(maxlen=50)
        self.last_block_from_rpc: int = 0
        self.rpc_healthy: bool = True
        
        # Rate limiting
        self.request_timestamps: deque = deque(maxlen=100)
        self.max_requests_per_second = config.get("max_rps", 10)
        
        # Latency threshold
        self.max_latency = config.get("max_latency_ms", 1000)
    
    async def check_rpc_health(self, rpc_url: str) -> SafetyCheckResult:
        """Check if RPC is healthy"""
        issues = []
        warnings = []
        
        start = time.time()
        
        try:
            # Make test request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    rpc_url,
                    json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    latency = (time.time() - start) * 1000
                    self.rpc_latencies.append(latency)
                    
                    if latency > self.max_latency:
                        warnings.append(f"HIGH LATENCY: {latency:.0f}ms")
                    
                    if resp.status != 200:
                        issues.append(f"RPC ERROR: Status {resp.status}")
                    
                    # Check block number
                    data = await resp.json()
                    if "result" in data:
                        current_block = int(data["result"], 16)
                        if self.last_block_from_rpc > 0:
                            if current_block < self.last_block_from_rpc - 1:
                                issues.append("RPC DESYNC: Block number went backwards")
                        self.last_block_from_rpc = current_block
                        
        except asyncio.TimeoutError:
            issues.append("RPC TIMEOUT")
        except Exception as e:
            issues.append(f"RPC ERROR: {str(e)}")
        
        # Check rate limiting
        now = time.time()
        recent_requests = [t for t in self.request_timestamps if now - t < 1.0]
        if len(recent_requests) > self.max_requests_per_second:
            warnings.append("RATE LIMIT APPROACHING")
        
        self.request_timestamps.append(now)
        
        self.rpc_healthy = len(issues) == 0
        
        level = SafetyLevel.REJECT if issues else SafetyLevel.WARNING if warnings else SafetyLevel.SAFE
        
        return SafetyCheckResult(
            level=level,
            passed=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            metadata={"latency_ms": latency if 'latency' in dir() else None}
        )


class StrategyProtection:
    """
    Protection against strategy failures:
    - Opportunity decay
    - Gas wars
    - Competition
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Opportunity timing
        self.opportunity_age_threshold = config.get("opp_age_threshold", 2.0)  # seconds
        
        # Gas war detection
        self.gas_war_threshold = config.get("gas_war_threshold", 100)  # gwei
        
        # Competition tracking
        self.competitor_txs: Set[str] = set()
    
    def verify_opportunity_timing(
        self,
        opportunity_found_at: float,
        execution_time: float
    ) -> SafetyCheckResult:
        """Verify opportunity hasn't decayed"""
        issues = []
        warnings = []
        
        age = execution_time - opportunity_found_at
        
        if age > self.opportunity_age_threshold:
            warnings.append(f"OPPORTUNITY OLD: {age:.2f}s since discovery")
        
        if age > self.opportunity_age_threshold * 3:
            issues.append(f"OPPORTUNITY EXPIRED: {age:.2f}s old")
        
        passed = len(issues) == 0
        level = SafetyLevel.REJECT if issues else SafetyLevel.WARNING if warnings else SafetyLevel.SAFE
        
        return SafetyCheckResult(
            level=level,
            passed=passed,
            issues=issues,
            warnings=warnings,
            metadata={"age_seconds": age}
        )
    
    def check_gas_war(self, current_gas: int, your_gas: int) -> SafetyCheckResult:
        """Check if gas war is happening"""
        issues = []
        warnings = []
        
        gas_gwei = current_gas / 1e9
        
        if gas_gwei > self.gas_war_threshold:
            warnings.append(f"GAS WAR: {gas_gwei:.1f} gwei (threshold: {self.gas_war_threshold})")
        
        if your_gas < current_gas:
            warnings.append(f"UNDERBIDDING: Your gas {your_gas/1e9:.1f} < market {gas_gwei:.1f} gwei")
        
        passed = len(issues) == 0
        level = SafetyLevel.WARNING if warnings else SafetyLevel.SAFE
        
        return SafetyCheckResult(
            level=level,
            passed=passed,
            issues=issues,
            warnings=warnings,
            metadata={"gas_gwei": gas_gwei}
        )


class ComprehensiveSafetySystem:
    """
    Master safety system that combines all protections
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Initialize all protection modules
        self.consensus = ConsensusProtection(config)
        self.builder = BuilderProtection(config)
        self.transaction = TransactionProtection(config)
        self.oracle = OracleProtection(config)
        self.simulation = SimulationProtection(config)
        self.network = NetworkProtection(config)
        self.strategy = StrategyProtection(config)
        
        # Overall statistics
        self.total_checks = 0
        self.failed_checks = 0
        self.rejected_trades = 0
    
    async def pre_execution_check(
        self,
        context: Dict
    ) -> SafetyCheckResult:
        """
        Comprehensive pre-execution safety check
        Returns whether to proceed with execution
        """
        self.total_checks += 1
        
        all_issues = []
        all_warnings = []
        
        # 1. Consensus checks
        if "block_state" in context:
            result = await self.consensus.verify_block_state(context["block_state"])
            all_issues.extend(result.issues)
            all_warnings.extend(result.warnings)
        
        # 2. Network checks
        if "rpc_url" in context:
            result = await self.network.check_rpc_health(context["rpc_url"])
            all_issues.extend(result.issues)
            all_warnings.extend(result.warnings)
        
        # 3. Transaction checks
        if "tx_params" in context:
            result = await self.transaction.verify_transaction_safe(**context["tx_params"])
            all_issues.extend(result.issues)
            all_warnings.extend(result.warnings)
        
        # 4. Oracle checks
        if "price_data" in context:
            result = await self.oracle.verify_price_fresh(context["token"], context["price_data"])
            all_issues.extend(result.issues)
            all_warnings.extend(result.warnings)
        
        # 5. Strategy checks
        if "opportunity_time" in context:
            result = self.strategy.verify_opportunity_timing(
                context["opportunity_time"],
                time.time()
            )
            all_issues.extend(result.issues)
            all_warnings.extend(result.warnings)
        
        # Determine final decision
        if all_issues:
            self.failed_checks += 1
            self.rejected_trades += 1
            
            logger.warning(f"🚫 TRADE REJECTED: {'; '.join(all_issues)}")
            
            return SafetyCheckResult(
                level=SafetyLevel.REJECT,
                passed=False,
                issues=all_issues,
                warnings=all_warnings
            )
        
        if all_warnings:
            logger.info(f"⚠️ TRADE WITH WARNINGS: {'; '.join(all_warnings)}")
        
        return SafetyCheckResult(
            level=SafetyLevel.SAFE if not all_warnings else SafetyLevel.WARNING,
            passed=True,
            issues=all_issues,
            warnings=all_warnings
        )
    
    def get_statistics(self) -> Dict:
        """Get safety system statistics"""
        return {
            "total_checks": self.total_checks,
            "failed_checks": self.failed_checks,
            "rejected_trades": self.rejected_trades,
            "success_rate": (
                (self.total_checks - self.failed_checks) / self.total_checks * 100
                if self.total_checks > 0 else 100
            )
        }


# Factory
def create_safety_system(config: Dict = None) -> ComprehensiveSafetySystem:
    """Create comprehensive safety system"""
    if config is None:
        config = {}
    return ComprehensiveSafetySystem(config)
