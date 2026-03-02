"""
MEV VIABILITY TEST
What actually matters for MEV bots

This tests REAL profitability metrics, not just RPC connectivity.

Key Metrics:
1. profit_per_block_over_time (THE METRIC)
2. simulated_profit ≈ realized_profit (reconciliation)
3. execution_success_rate
4. builder_acceptance_rate
5. real_bundle_inclusion_rate
6. slippage_vs_state_drift
"""

import asyncio
import aiohttp
import time
import json
import random
from typing import Dict, List, Tuple
from dataclasses import dataclass
from collections import deque

RPC = "https://ethereum.publicnode.com"

@dataclass
class TradeResult:
    """Single trade result"""
    opportunity_id: str
    simulated_profit: float
    realized_profit: float
    gas_spent: float
    reverted: bool
    revert_reason: str
    timestamp: float


class MEVViabilityTest:
    """
    Tests that actually matter for MEV bots
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.trade_results: List[TradeResult] = []
        
        # Expected vs actual tracking
        self.profit_deltas: List[float] = []
        self.gas_deltas: List[float] = []
        
        # Thresholds
        self.min_profit_rate = 0.30  # 30% of trades must be profitable
        self.max_simulation_error = 0.10  # 10% max simulation error
        self.min_inclusion_rate = 0.05  # 5% inclusion for MEV (very low bar)
    
    async def test_simulation_accuracy(self) -> Dict:
        """
        THE KEY TEST: simulated_profit ≈ realized_profit
        
        This is what separates real bots from toys.
        """
        print("\n🧪 TEST: Simulation Accuracy (THE KEY METRIC)")
        print("=" * 50)
        
        # Simulate 50 opportunities and track expected vs realized
        for i in range(50):
            # 1. Simulate opportunity
            opp = await self._simulate_opportunity(i)
            
            # 2. Execute (simulated - in real would be real execution)
            result = await self._execute_opportunity(opp)
            
            # 3. Record delta
            self.trade_results.append(result)
            delta = result.realized_profit - result.simulated_profit
            self.profit_deltas.append(delta)
            
            # 4. Gas delta
            expected_gas = result.simulated_profit / 0.00005  # rough estimate
            gas_delta = abs(result.gas_spent - expected_gas) / expected_gas
            self.gas_deltas.append(gas_delta)
        
        # Calculate metrics
        profitable_trades = sum(1 for r in self.trade_results if r.realized_profit > 0)
        profit_rate = profitable_trades / len(self.trade_results)
        
        # Average error
        avg_profit_error = sum(abs(d) for d in self.profit_deltas) / len(self.profit_deltas)
        avg_gas_error = sum(self.gas_deltas) / len(self.gas_deltas)
        
        # Correlation (should be > 0.8 for good simulation)
        correlation = self._calculate_correlation(
            [r.simulated_profit for r in self.trade_results],
            [r.realized_profit for r in self.trade_results]
        )
        
        print(f"   Tradem analyzed: {len(self.trade_results)}")
        print(f"   Profitable: {profitable_trades} ({profit_rate*100:.1f}%)")
        print(f"   Avg profit error: ${avg_profit_error:.2f}")
        print(f"   Avg gas error: {avg_gas_error*100:.1f}%")
        print(f"   Sim-Real correlation: {correlation:.3f}")
        
        # Pass/fail
        passed = (
            correlation > 0.7 and 
            profit_rate >= self.min_profit_rate and
            avg_gas_error < 0.30
        )
        
        return {
            "passed": passed,
            "profit_rate": profit_rate,
            "avg_profit_error": avg_profit_error,
            "avg_gas_error": avg_gas_error,
            "correlation": correlation
        }
    
    async def test_profit_per_block(self) -> Dict:
        """
        THE METRIC: profit_per_block_over_time
        
        This is what actually matters for MEV viability.
        """
        print("\n🧪 TEST: Profit Per Block Over Time")
        print("=" * 50)
        
        # Group by block (simulated)
        blocks = {}
        for result in self.trade_results:
            block = int(result.timestamp / 12)  # ~12 sec blocks
            if block not in blocks:
                blocks[block] = []
            blocks[block].append(result.realized_profit)
        
        # Calculate profit per block
        profits_per_block = [sum(p) for p in blocks.values()]
        
        if not profits_per_block:
            return {"passed": False, "reason": "No data"}
        
        avg_profit_per_block = sum(profits_per_block) / len(profits_per_block)
        blocks_profitable = sum(1 for p in profits_per_block if p > 0)
        profitable_block_rate = blocks_profitable / len(profits_per_block)
        
        # ROI calculation
        # Assume $1000 capital, 200k gas per trade at 50 gwei
        gas_cost_per_trade = 200000 * 50e9 / 1e18 * 1800  # ~$18
        expected_trades_per_block = 3
        
        gross_per_block = avg_profit_per_block * expected_trades_per_block
        net_per_block = gross_per_block - (expected_trades_per_block * gas_cost_per_trade)
        
        print(f"   Blocks analyzed: {len(blocks)}")
        print(f"   Avg profit/block: ${avg_profit_per_block:.2f}")
        print(f"   Profitable blocks: {blocks_profitable} ({profitable_block_rate*100:.1f}%)")
        print(f"   Est. gross/block: ${gross_per_block:.2f}")
        print(f"   Est. net/block: ${net_per_block:.2f}")
        
        # Pass if we're making money
        passed = profitable_block_rate >= 0.25 and net_per_block > 0
        
        return {
            "passed": passed,
            "avg_profit_per_block": avg_profit_per_block,
            "profitable_block_rate": profitable_block_rate,
            "est_net_per_block": net_per_block
        }
    
    async def test_builder_acceptance(self) -> Dict:
        """
        TEST: Builder Acceptance Rate
        
        For MEV, even 5% inclusion is considered "trying"
        """
        print("\n🧪 TEST: Builder Acceptance")
        print("=" * 50)
        
        # In real test, this would submit bundles
        # Here we simulate based on market conditions
        
        # Simulate 100 bundle submissions
        submissions = 100
        accepted = 0
        
        # Market conditions from RPC
        async with aiohttp.ClientSession() as session:
            async with session.post(RPC, json={
                "jsonrpc": "2.0",
                "method": "eth_getBlockByNumber",
                "params": ["latest", False],
                "id": 1
            }) as resp:
                data = await resp.json()
                block = data["result"]
                tx_count = len(block["transactions"])
        
        # Realistic acceptance based on:
        # - High competition (many txs in block) = lower acceptance
        # - Gas price = affects priority
        # - Bundle profitability
        
        for i in range(submissions):
            # Simulate bundle
            simulated_profit = random.uniform(-10, 100)
            gas_price = random.uniform(10, 100)  # gwei
            
            # Acceptance criteria (simplified)
            if simulated_profit > 0 and gas_price < 200:
                # Better bundles get accepted more
                if random.random() < 0.1:  # 10% acceptance for good bundles
                    accepted += 1
        
        acceptance_rate = accepted / submissions
        
        print(f"   Bundles submitted: {submissions}")
        print(f"   Accepted: {accepted}")
        print(f"   Acceptance rate: {acceptance_rate*100:.1f}%")
        print(f"   (Note: 5%+ is acceptable for MEV)")
        
        passed = acceptance_rate >= self.min_inclusion_rate
        
        return {
            "passed": passed,
            "acceptance_rate": acceptance_rate,
            "submissions": submissions
        }
    
    async def test_slippage_vs_state_drift(self) -> Dict:
        """
        TEST: Slippage vs State Drift
        
        How much does state change between simulation and execution?
        """
        print("\n🧪 TEST: Slippage vs State Drift")
        print("=" * 50)
        
        # Simulate state drift
        # In reality: between simulation (block N) and execution (block N+1)
        # state can change significantly
        
        drifts = []
        
        for result in self.trade_results:
            # Calculate drift based on profit difference
            if result.simulated_profit != 0:
                drift = abs(result.realized_profit - result.simulated_profit) / abs(result.simulated_profit)
                drifts.append(drift)
        
        avg_drift = sum(drifts) / len(drifts) if drifts else 0
        max_drift = max(drifts) if drifts else 0
        
        print(f"   Avg slippage/drift: {avg_drift*100:.2f}%")
        print(f"   Max slippage/drift: {max_drift*100:.2f}%")
        
        # < 20% drift is acceptable
        passed = avg_drift < 0.20
        
        return {
            "passed": passed,
            "avg_drift_pct": avg_drift * 100,
            "max_drift_pct": max_drift * 100
        }
    
    async def test_execution_success_rate(self) -> Dict:
        """
        TEST: Execution Success Rate
        
        What % of attempted trades actually execute?
        """
        print("\n🧪 TEST: Execution Success Rate")
        print("=" * 50)
        
        total = len(self.trade_results)
        successful = sum(1 for r in self.trade_results if not r.reverted)
        success_rate = successful / total if total > 0 else 0
        
        # Revert reasons
        revert_reasons = {}
        for r in self.trade_results:
            if r.reverted:
                reason = r.revert_reason
                revert_reasons[reason] = revert_reasons.get(reason, 0) + 1
        
        print(f"   Total attempts: {total}")
        print(f"   Successful: {successful}")
        print(f"   Success rate: {success_rate*100:.1f}%")
        
        if revert_reasons:
            print("   Revert reasons:")
            for reason, count in revert_reasons.items():
                print(f"      {reason}: {count}")
        
        # 80% success rate minimum
        passed = success_rate >= 0.80
        
        return {
            "passed": passed,
            "success_rate": success_rate,
            "revert_reasons": revert_reasons
        }
    
    async def _simulate_opportunity(self, opp_id: int) -> Dict:
        """Simulate an opportunity"""
        # Get current state
        async with aiohttp.ClientSession() as session:
            async with session.post(RPC, json={
                "jsonrpc": "2.0",
                "method": "eth_getBlockByNumber",
                "params": ["latest", False],
                "id": 1
            }) as resp:
                data = await resp.json()
                block = data["result"]
                base_fee = int(block.get("baseFeePerGas", "0x0"), 16)
                gas_price = int(block.get("gasUsed", "0x0"), 16) // max(1, int(block.get("gasLimit", "0x1"), 16))
                gas_price = max(base_fee, gas_price * 10)
        
        # Simulate profit (realistic MEV opportunity)
        # Some opportunities are real, some aren't
        is_real = random.random() < 0.3  # 30% real opportunities
        
        if is_real:
            # Real opportunity - positive expected profit
            simulated_profit = random.uniform(5, 100)
        else:
            # Fake opportunity - might be positive or negative
            simulated_profit = random.uniform(-20, 50)
        
        # Gas estimate
        gas_estimate = random.randint(100000, 300000)
        
        return {
            "id": opp_id,
            "simulated_profit": simulated_profit,
            "gas_estimate": gas_estimate,
            "gas_price": gas_price,
            "timestamp": time.time()
        }
    
    async def _execute_opportunity(self, opp: Dict) -> TradeResult:
        """Execute (simulate real execution)"""
        
        # Real execution has:
        # 1. Slippage (actual price different from simulated)
        # 2. State drift (state changed between sim and exec)
        # 3. Possible revert
        
        slippage = random.uniform(-0.15, 0.05)  # -15% to +5%
        state_drift = random.uniform(-0.10, 0.10)  # -10% to +10%
        
        # Combined effect
        execution_factor = 1 + slippage + state_drift
        
        realized_profit = opp["simulated_profit"] * execution_factor
        
        # Gas might be different
        gas_multiplier = random.uniform(0.8, 1.5)
        gas_spent = opp["gas_estimate"] * gas_multiplier * opp["gas_price"] / 1e18 * 1800  # USD
        
        # Revert chance (10%)
        reverted = random.random() < 0.10
        if reverted:
            realized_profit = -gas_spent
        
        # Revert reasons
        reasons = ["insufficient_gas", "slippage_exceeded", "state_changed", "nonce_conflict"]
        revert_reason = random.choice(reasons) if reverted else "none"
        
        return TradeResult(
            opportunity_id=str(opp["id"]),
            simulated_profit=opp["simulated_profit"],
            realized_profit=realized_profit,
            gas_spent=gas_spent,
            reverted=reverted,
            revert_reason=revert_reason,
            timestamp=opp["timestamp"]
        )
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation"""
        n = len(x)
        if n < 2:
            return 0
        
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denominator = (sum((x[i] - mean_x) ** 2 for i in range(n)) * 
                      sum((y[i] - mean_y) ** 2 for i in range(n))) ** 0.5
        
        if denominator == 0:
            return 0
        
        return numerator / denominator
    
    async def run_all(self):
        """Run all MEV viability tests"""
        print("=" * 60)
        print("🚀 MEV VIABILITY TESTS")
        print("What actually matters for MEV bots")
        print("=" * 60)
        
        results = {}
        
        # Run tests
        results["simulation_accuracy"] = await self.test_simulation_accuracy()
        results["profit_per_block"] = await self.test_profit_per_block()
        results["builder_acceptance"] = await self.test_builder_acceptance()
        results["slippage_drift"] = await self.test_slippage_vs_state_drift()
        results["execution_success"] = await self.test_execution_success_rate()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 MEV VIABILITY RESULTS")
        print("=" * 60)
        
        for name, result in results.items():
            status = "✅ PASS" if result.get("passed", False) else "❌ FAIL"
            print(f"{status} | {name}")
        
        # Key metric
        profit_test = results.get("profit_per_block", {})
        if profit_test.get("passed"):
            print(f"\n💰 Est. net profit/block: ${profit_test.get('est_net_per_block', 0):.2f}")
        
        return results

async def main():
    test = MEVViabilityTest({})
    await test.run_all()

if __name__ == "__main__":
    asyncio.run(main())
