"""
Real Production Integration Tests
Using ethereum.publicnode.com
"""

import asyncio
import aiohttp
import time
import json

RPC = "https://ethereum.publicnode.com"

class RealIntegrationTests:
    """Integration tests against real Ethereum"""
    
    def __init__(self):
        self.results = {}
    
    async def test_rpc_connectivity(self) -> dict:
        """Test 1: RPC Connectivity"""
        print("\n🧪 TEST 1: RPC Connectivity")
        
        latencies = []
        blocks = []
        
        for i in range(10):
            start = time.perf_counter()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(RPC, json={
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 1
                }) as resp:
                    data = await resp.json()
                    block = int(data["result"], 16)
                    blocks.append(block)
                    
                    latency = (time.perf_counter() - start) * 1000
                    latencies.append(latency)
        
        avg_latency = sum(latencies) / len(latencies)
        block_variance = max(blocks) - min(blocks)
        
        result = {
            "passed": avg_latency < 200,
            "avg_latency_ms": avg_latency,
            "blocks": blocks,
            "block_variance": block_variance
        }
        
        print(f"   Latency: {avg_latency:.0f}ms (threshold: 200ms)")
        print(f"   Blocks: {min(blocks)}-{max(blocks)} (variance: {block_variance})")
        
        self.results["connectivity"] = result
        return result
    
    async def test_gas_pricing(self) -> dict:
        """Test 2: Gas Pricing Model"""
        print("\n🧪 TEST 2: Gas Pricing")
        
        async with aiohttp.ClientSession() as session:
            # Get latest block
            async with session.post(RPC, json={
                "jsonrpc": "2.0",
                "method": "eth_getBlockByNumber",
                "params": ["latest", False],
                "id": 1
            }) as resp:
                data = await resp.json()
                block = data["result"]
                
                base_fee = int(block.get("baseFeePerGas", "0x0"), 16)
                gas_limit = int(block.get("gasLimit", "0x0"), 16)
                gas_used = int(block.get("gasUsed", "0x0"), 16)
        
        # Get current gas price
        async with aiohttp.ClientSession() as session:
            async with session.post(RPC, json={
                "jsonrpc": "2.0",
                "method": "eth_gasPrice",
                "params": [],
                "id": 2
            }) as resp:
                data = await resp.json()
                gas_price = int(data["result"], 16)
        
        # Calculate utilization
        utilization = gas_used / gas_limit if gas_limit > 0 else 0
        
        # Check EIP-1559 compliance
        eip1559_compliant = base_fee > 0
        
        result = {
            "passed": eip1559_compliant,
            "base_fee_gwei": base_fee / 1e9,
            "gas_price_gwei": gas_price / 1e9,
            "utilization_pct": utilization * 100,
            "eip1559": eip1559_compliant
        }
        
        print(f"   Base fee: {base_fee/1e9:.4f} gwei")
        print(f"   Gas price: {gas_price/1e9:.4f} gwei")
        print(f"   Utilization: {utilization*100:.1f}%")
        print(f"   EIP-1559: {'✅' if eip1559_compliant else '❌'}")
        
        self.results["gas"] = result
        return result
    
    async def test_block_data(self) -> dict:
        """Test 3: Block Data Quality"""
        print("\n🧪 TEST 3: Block Data")
        
        async with aiohttp.ClientSession() as session:
            # Get block
            async with session.post(RPC, json={
                "jsonrpc": "2.0",
                "method": "eth_getBlockByNumber",
                "params": ["latest", True],
                "id": 1
            }) as resp:
                data = await resp.json()
                block = data["result"]
        
        # Validate block structure
        required_fields = ["number", "hash", "parentHash", "timestamp", "gasUsed", "gasLimit", "transactions"]
        has_all = all(field in block for field in required_fields)
        
        # Check timestamp is recent (within 30 seconds)
        block_time = int(block["timestamp"], 16)
        current_time = time.time()
        time_diff = abs(current_time - block_time)
        is_recent = time_diff < 30
        
        # Count transactions
        tx_count = len(block["transactions"])
        
        result = {
            "passed": has_all and is_recent,
            "has_all_fields": has_all,
            "is_recent": is_recent,
            "time_diff_sec": time_diff,
            "tx_count": tx_count
        }
        
        print(f"   Fields: {'✅' if has_all else '❌'}")
        print(f"   Recent (diff: {time_diff:.1f}s): {'✅' if is_recent else '❌'}")
        print(f"   Transactions: {tx_count}")
        
        self.results["block_data"] = result
        return result
    
    async def test_balance_queries(self) -> dict:
        """Test 4: Balance Queries"""
        print("\n🧪 TEST 4: Balance Queries")
        
        # Test with known addresses
        addresses = [
            "0x0000000000000000000000000000000000000000",  # Burn address
            "0x00000000219ab540356cBB839Cbe05303d7705Fa",  # Beacon deposit
        ]
        
        results = []
        
        async with aiohttp.ClientSession() as session:
            for addr in addresses:
                async with session.post(RPC, json={
                    "jsonrpc": "2.0",
                    "method": "eth_getBalance",
                    "params": [addr, "latest"],
                    "id": 1
                }) as resp:
                    data = await resp.json()
                    balance = int(data["result"], 16)
                    results.append({"address": addr, "balance": balance})
        
        result = {
            "passed": len(results) == len(addresses),
            "addresses": results
        }
        
        for r in results:
            print(f"   {r['address'][:20]}...: {r['balance']/1e18:.2f} ETH")
        
        self.results["balance"] = result
        return result
    
    async def test_token_prices(self) -> dict:
        """Test 5: Token Price Feeds"""
        print("\n🧪 TEST 5: Token Prices")
        
        # Get ETH price
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    eth_price = data["ethereum"]["usd"]
                else:
                    eth_price = 0
        
        result = {
            "passed": eth_price > 0,
            "eth_price": eth_price
        }
        
        print(f"   ETH: ${eth_price}")
        
        self.results["prices"] = result
        return result
    
    async def test_batch_requests(self) -> dict:
        """Test 6: Batch Request Performance"""
        print("\n🧪 TEST 6: Batch Requests")
        
        # Create batch of 5 requests
        batch = [
            {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": i}
            for i in range(5)
        ]
        
        start = time.perf_counter()
        
        async with aiohttp.ClientSession() as session:
            async with session.post(RPC, json=batch) as resp:
                results = await resp.json()
        
        batch_time = (time.perf_counter() - start) * 1000
        
        # Compare to sequential
        start = time.perf_counter()
        async with aiohttp.ClientSession() as session:
            for i in range(5):
                async with session.post(RPC, json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": i}) as resp:
                    await resp.json()
        
        sequential_time = (time.perf_counter() - start) * 1000
        
        speedup = sequential_time / batch_time
        
        result = {
            "passed": batch_time < sequential_time,
            "batch_ms": batch_time,
            "sequential_ms": sequential_time,
            "speedup": speedup
        }
        
        print(f"   Batch: {batch_time:.0f}ms")
        print(f"   Sequential: {sequential_time:.0f}ms")
        print(f"   Speedup: {speedup:.1f}x")
        
        self.results["batch"] = result
        return result
    
    async def test_simulation_accuracy(self) -> dict:
        """Test 7: Simulation Accuracy (Basic)"""
        print("\n🧪 TEST 7: Simulation Accuracy")
        
        # Simulate a simple call and compare
        # This is a basic test - real simulation would need local fork
        
        async with aiohttp.ClientSession() as session:
            # Get current state
            async with session.post(RPC, json={
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{
                    "to": "0x0000000000000000000000000000000000000000",
                    "data": "0x"
                }, "latest"],
                "id": 1
            }) as resp:
                data = await resp.json()
                result1 = data.get("result")
            
            # Get same call again
            async with session.post(RPC, json={
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{
                    "to": "0x0000000000000000000000000000000000000000",
                    "data": "0x"
                }, "latest"],
                "id": 2
            }) as resp:
                data = await resp.json()
                result2 = data.get("result")
        
        # Results should be identical (deterministic)
        deterministic = result1 == result2
        
        result = {
            "passed": deterministic,
            "deterministic": deterministic
        }
        
        print(f"   Deterministic: {'✅' if deterministic else '❌'}")
        
        self.results["simulation"] = result
        return result
    
    async def run_all(self):
        """Run all tests"""
        print("=" * 60)
        print("🚀 REAL PRODUCTION INTEGRATION TESTS")
        print("=" * 60)
        print(f"RPC: {RPC}")
        
        await self.test_rpc_connectivity()
        await self.test_gas_pricing()
        await self.test_block_data()
        await self.test_balance_queries()
        await self.test_token_prices()
        await self.test_batch_requests()
        await self.test_simulation_accuracy()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 RESULTS SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.results.values() if r.get("passed", False))
        total = len(self.results)
        
        for name, result in self.results.items():
            status = "✅ PASS" if result.get("passed", False) else "❌ FAIL"
            print(f"{status} | {name}")
        
        print(f"\nScore: {passed}/{total} ({passed/total*100:.0f}%)")
        
        return passed == total

async def main():
    tests = RealIntegrationTests()
    await tests.run_all()

if __name__ == "__main__":
    asyncio.run(main())
