"""
Local Simulation Engine with Anvil Fork
Real-time state simulation without RPC latency
"""

import asyncio
import logging
import subprocess
import os
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SimulationResult:
    """Result of transaction simulation"""
    success: bool
    gas_used: int
    return_value: Any
    logs: List[Dict]
    state_changes: Dict
    profit: float
    error: Optional[str] = None


@dataclass
class ForkState:
    """Anvil fork state"""
    fork_url: str
    fork_block: int
    snapshot_id: Optional[str] = None


class LocalSimulationEngine:
    """
    Local simulation using Anvil fork
    Features:
    - Persistent Anvil fork
    - Snapshot/restore for fast state reset
    - Batch simulation pipeline
    - Zero RPC latency for simulations
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Anvil configuration
        self.fork_url = config.get("fork_url", os.getenv("ETHEREUM_RPC", ""))
        self.port = config.get("anvil_port", 8545)
        self.chain_id = config.get("chain_id", 1)
        
        # Process management
        self.anvil_process = None
        self.http_endpoint = f"http://localhost:{self.port}"
        self.ws_endpoint = f"ws://localhost:{self.port + 1}"
        
        # State management
        self.current_snapshot = None
        self.snapshot_stack = []
        
        # Simulation cache
        self.simulation_cache: Dict[str, SimulationResult] = {}
        self.cache_ttl = 5  # seconds
        
        # Batch processing
        self.batch_size = config.get("batch_size", 10)
    
    async def start(self):
        """Start Anvil fork"""
        if not self.fork_url:
            logger.warning("No fork URL configured, using public RPC")
            return
        
        try:
            # Kill any existing anvil on port
            await self._kill_existing_anvil()
            
            # Start Anvil with fork
            cmd = [
                "anvil",
                "--host", "0.0.0.0",
                "--port", str(self.port),
                "--chain-id", str(self.chain_id),
                "--fork-url", self.fork_url,
                "--fork-block-number", str(await self._get_latest_block()),
                "--accounts", "10",
                "--balance", "10000",
            ]
            
            # Start process
            self.anvil_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for anvil to be ready
            await self._wait_for_ready()
            
            # Take initial snapshot
            await self.take_snapshot()
            
            logger.info(f"✅ Anvil fork started on port {self.port}")
            
        except Exception as e:
            logger.error(f"Failed to start Anvil: {e}")
            raise
    
    async def stop(self):
        """Stop Anvil fork"""
        if self.anvil_process:
            self.anvil_process.terminate()
            try:
                self.anvil_process.wait(timeout=5)
            except:
                self.anvil_process.kill()
            logger.info("🛑 Anvil fork stopped")
    
    async def _kill_existing_anvil(self):
        """Kill any existing anvil process"""
        try:
            subprocess.run(["pkill", "-f", "anvil"], timeout=5)
            await asyncio.sleep(1)
        except:
            pass
    
    async def _get_latest_block(self) -> int:
        """Get latest block number from fork"""
        # This would query the fork RPC
        return 0  # Let anvil determine
    
    async def _wait_for_ready(self):
        """Wait for Anvil to be ready"""
        import aiohttp
        
        for _ in range(30):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.http_endpoint,
                        json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
                    ) as resp:
                        if resp.status == 200:
                            return
            except:
                pass
            await asyncio.sleep(1)
        
        raise Exception("Anvil failed to start")
    
    # ==================== SNAPSHOT MANAGEMENT ====================
    
    async def take_snapshot(self) -> str:
        """Take a snapshot of current state"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.http_endpoint,
                json={
                    "jsonrpc": "2.0",
                    "method": "evm_snapshot",
                    "params": [],
                    "id": 1
                }
            ) as resp:
                data = await resp.json()
                snapshot_id = data.get("result")
                
                if snapshot_id:
                    self.snapshot_stack.append(snapshot_id)
                    logger.debug(f"Snapshot taken: {snapshot_id}")
                
                return snapshot_id
    
    async def restore_snapshot(self, snapshot_id: Optional[str] = None) -> bool:
        """Restore to previous snapshot"""
        import aiohttp
        
        # Use provided or pop from stack
        restore_id = snapshot_id or (self.snapshot_stack.pop() if self.snapshot_stack else None)
        
        if not restore_id:
            logger.warning("No snapshot to restore")
            return False
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.http_endpoint,
                json={
                    "jsonrpc": "2.0",
                    "method": "evm_revert",
                    "params": [restore_id],
                    "id": 1
                }
            ) as resp:
                result = await resp.json()
                success = "result" in result and result["result"] == True
                
                if success:
                    logger.debug(f"Snapshot restored: {restore_id}")
                    # Take new snapshot after revert
                    await self.take_snapshot()
                
                return success
    
    async def reset_to_fresh(self):
        """Reset to fresh fork state"""
        await self.restore_snapshot()
    
    # ==================== SIMULATION ====================
    
    async def simulate_transaction(
        self,
        from_addr: str,
        to_addr: str,
        data: str,
        value: int = 0,
        gas: Optional[int] = None
    ) -> SimulationResult:
        """
        Simulate a single transaction
        Uses local fork - extremely fast
        """
        import aiohttp
        
        # Check cache
        cache_key = f"{from_addr}:{to_addr}:{data[:20]}"
        if cache_key in self.simulation_cache:
            cached = self.simulation_cache[cache_key]
            if time.time() - cached.get("_timestamp", 0) < self.cache_ttl:
                return cached
        
        # Default gas
        if not gas:
            gas = 3000000
        
        try:
            async with aiohttp.ClientSession() as session:
                # Build transaction
                tx = {
                    "from": from_addr,
                    "to": to_addr,
                    "data": data,
                    "value": hex(value),
                    "gas": hex(gas),
                    "gasPrice": hex(20000000000),  # 20 gwei
                }
                
                # Simulate
                async with session.post(
                    self.http_endpoint,
                    json={
                        "jsonrpc": "2.0",
                        "method": "eth_call",
                        "params": [tx, "latest"],
                        "id": 1
                    }
                ) as resp:
                    result = await resp.json()
                    
                    if "error" in result:
                        return SimulationResult(
                            success=False,
                            gas_used=0,
                            return_value=None,
                            logs=[],
                            state_changes={},
                            profit=0,
                            error=result["error"].get("message")
                        )
                    
                    # Estimate gas used
                    gas_used = gas  # Approximate
                    
                    return SimulationResult(
                        success=True,
                        gas_used=gas_used,
                        return_value=result.get("result"),
                        logs=[],
                        state_changes={},
                        profit=0  # Would calculate from state changes
                    )
        
        except Exception as e:
            return SimulationResult(
                success=False,
                gas_used=0,
                return_value=None,
                logs=[],
                state_changes={},
                profit=0,
                error=str(e)
            )
    
    async def simulate_batch(
        self,
        transactions: List[Dict]
    ) -> List[SimulationResult]:
        """
        Simulate multiple transactions in batch
        Uses multicall for efficiency
        """
        results = []
        
        # Process in batches
        for i in range(0, len(transactions), self.batch_size):
            batch = transactions[i:i + self.batch_size]
            
            # Simulate each
            for tx in batch:
                result = await self.simulate_transaction(
                    from_addr=tx.get("from"),
                    to_addr=tx.get("to"),
                    data=tx.get("data", "0x"),
                    value=tx.get("value", 0)
                )
                results.append(result)
            
            # Small delay to prevent overwhelming
            await asyncio.sleep(0.01)
        
        return results
    
    async def simulate_bundle(
        self,
        transactions: List[Dict],
        block_number: Optional[int] = None
    ) -> SimulationResult:
        """
        Simulate a bundle of transactions
        All must succeed for bundle to be valid
        """
        import aiohttp
        
        # Take snapshot before simulation
        await self.take_snapshot()
        
        try:
            results = []
            
            # Execute each tx in order
            for i, tx in enumerate(transactions):
                result = await self.simulate_transaction(
                    from_addr=tx.get("from"),
                    to_addr=tx.get("to"),
                    data=tx.get("data", "0x"),
                    value=tx.get("value", 0)
                )
                
                if not result.success:
                    # Bundle failed - revert
                    await self.restore_snapshot()
                    return SimulationResult(
                        success=False,
                        gas_used=sum(r.gas_used for r in results),
                        return_value=None,
                        logs=[],
                        state_changes={},
                        profit=0,
                        error=f"Transaction {i} failed: {result.error}"
                    )
                
                results.append(result)
            
            # All succeeded - calculate total gas
            total_gas = sum(r.gas_used for r in results)
            
            return SimulationResult(
                success=True,
                gas_used=total_gas,
                return_value="bundle_success",
                logs=[],
                state_changes={},
                profit=0
            )
        
        finally:
            # Always revert after bundle simulation
            await self.restore_snapshot()
    
    # ==================== STATE QUERY ====================
    
    async def get_token_balance(self, token: str, address: str) -> int:
        """Get token balance of address"""
        import aiohttp
        
        # ERC20 balanceOf selector
        selector = "0x70a08231"
        data = selector + address[2:].zfill(64)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.http_endpoint,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_call",
                    "params": [{
                        "to": token,
                        "data": data
                    }, "latest"],
                    "id": 1
                }
            ) as resp:
                result = await resp.json()
                return int(result.get("result", "0x0"), 16)
    
    async def get_eth_balance(self, address: str) -> int:
        """Get ETH balance"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.http_endpoint,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_getBalance",
                    "params": [address, "latest"],
                    "id": 1
                }
            ) as resp:
                result = await resp.json()
                return int(result.get("result", "0x0"), 16)
    
    async def get_gas_price(self) -> int:
        """Get current gas price"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.http_endpoint,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_gasPrice",
                    "params": [],
                    "id": 1
                }
            ) as resp:
                result = await resp.json()
                return int(result.get("result", "0x0"), 16)
    
    # ==================== HEALTH CHECK ====================
    
    async def health_check(self) -> Dict:
        """Check if simulation engine is healthy"""
        try:
            gas_price = await self.get_gas_price()
            return {
                "healthy": True,
                "anvil_running": self.anvil_process is not None if self.anvil_process else False,
                "gas_price": gas_price,
                "snapshot_available": len(self.snapshot_stack) > 0
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }


# ==================== CACHE SYSTEMS ====================

class StateCache:
    """
    Local cache for pool reserves and token prices
    Dramatically speeds up simulation
    """
    
    def __init__(self):
        self.pool_reserves: Dict[str, Dict] = {}  # pool_addr -> {reserve0, reserve1}
        self.token_prices: Dict[str, float] = {}  # token -> price USD
        self.token_decimals: Dict[str, int] = {}  # token -> decimals
        self.last_update: Dict[str, float] = {}  # key -> timestamp
        
        self.cache_ttl = 10  # 10 seconds
    
    async def get_pool_reserves(self, pool_addr: str) -> Optional[Dict]:
        """Get cached pool reserves"""
        if pool_addr in self.pool_reserves:
            if time.time() - self.last_update.get(pool_addr, 0) < self.cache_ttl:
                return self.pool_reserves[pool_addr]
        return None
    
    async def update_pool_reserves(self, pool_addr: str, reserves: Dict):
        """Update pool reserves cache"""
        self.pool_reserves[pool_addr] = reserves
        self.last_update[pool_addr] = time.time()
    
    async def get_token_price(self, token: str) -> Optional[float]:
        """Get cached token price"""
        if token in self.token_prices:
            if time.time() - self.last_update.get(token, 0) < self.cache_ttl:
                return self.token_prices[token]
        return None
    
    async def update_token_price(self, token: str, price: float):
        """Update token price cache"""
        self.token_prices[token] = price
        self.last_update[token] = time.time()
    
    async def batch_update(self, updates: Dict):
        """Batch update multiple cache entries"""
        for key, value in updates.items():
            if isinstance(value, dict):
                await self.update_pool_reserves(key, value)
            elif isinstance(value, float):
                await self.update_token_price(key, value)


class MulticallReader:
    """
    Batch read multiple contract states in single call
    Uses multicall pattern for efficiency
    """
    
    def __init__(self, rpc_url: str):
        self.rpc_url = rpc_url
        # Mainnet Multicall address
        self.MULTICALL = "0x5e227AD1969e4932108a51a7d9D64dAd4C153067"
    
    async def batch_call(
        self,
        calls: List[Dict]
    ) -> List[Optional[str]]:
        """
        Execute batch calls via multicall
        calls: [{"to": address, "data": bytes}]
        Returns: [result bytes]
        """
        import aiohttp
        
        # Aggregate calls
        calls_data = []
        for call in calls:
            calls_data.append([
                call["to"],
                call.get("data", "0x")
            ])
        
        # Encode aggregate
        import eth_abi
        encoded = eth_abi.encode(["(address,bytes)[]"], [calls_data])
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "method": "eth_call",
                        "params": [{
                            "to": self.MULTICALL,
                            "data": "0xac9650d8" + encoded.hex()  # aggregate selector
                        }, "latest"],
                        "id": 1
                    }
                ) as resp:
                    result = await resp.json()
                    
                    if "error" in result:
                        return [None] * len(calls)
                    
                    # Decode results
                    return_data = result["result"][2:]  # skip 0x prefix
                    decoded = eth_abi.decode(["(bool,bytes[])"], bytes.fromhex(return_data))
                    
                    return decoded[0][1] if decoded else [None] * len(calls)
        
        except Exception as e:
            logger.error(f"Multicall failed: {e}")
            return [None] * len(calls)


# Factory
def create_simulation_engine(config: Dict) -> LocalSimulationEngine:
    """Create local simulation engine"""
    return LocalSimulationEngine(config)

def create_state_cache() -> StateCache:
    """Create state cache"""
    return StateCache()
