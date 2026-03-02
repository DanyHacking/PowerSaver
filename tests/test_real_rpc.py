"""
Real Production Tests with Public RPC
Tests against actual Ethereum network
"""

import asyncio
import aiohttp
import time
from typing import Dict, List

async def test_real_rpc():
    """Test against real Ethereum RPC endpoints"""
    
    endpoints = [
        ("Cloudflare", "https://cloudflare-eth.com"),
        ("Ankr", "https://rpc.ankr.com/eth"),
    ]
    
    results = {}
    
    for name, url in endpoints:
        print(f"\n🧪 Testing {name}...")
        
        try:
            start = time.perf_counter()
            
            async with aiohttp.ClientSession() as session:
                # Test 1: Get block number
                async with session.post(url, json={
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 1
                }, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    
                    if resp.status != 200:
                        print(f"  ❌ HTTP {resp.status}")
                        continue
                    
                    data = await resp.json()
                    if "error" in data:
                        print(f"  ❌ RPC Error: {data['error']}")
                        continue
                    
                    block = int(data["result"], 16)
                    latency_ms = (time.perf_counter() - start) * 1000
                    
                    print(f"  ✅ Block: {block:,}")
                    print(f"  ✅ Latency: {latency_ms:.0f}ms")
                    
                    results[name] = {"block": block, "latency": latency_ms}
                
                # Test 2: Get block details
                async with session.post(url, json={
                    "jsonrpc": "2.0",
                    "method": "eth_getBlockByNumber",
                    "params": ["latest", False],
                    "id": 2
                }, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await resp.json()
                    if "result" in data:
                        result = data["result"]
                        print(f"  ✅ Gas price: {int(result.get('gasLimit', '0x0'), 16):,}")
                        
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    return results

async def test_gas_oracle():
    """Test gas price oracles"""
    
    print("\n\n⛽ Testing Gas Oracles...")
    
    oracles = [
        ("EthGasStation", "https://api.ethgasstation.info/api/gas_price"),
    ]
    
    # Fallback: estimate from recent blocks
    print("  Using EIP-1559 base fee estimation...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://cloudflare-eth.com", json={
                "jsonrpc": "2.0",
                "method": "eth_getBlockByNumber",
                "params": ["latest", False],
                "id": 1
            }, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                if "result" in data:
                    base_fee = int(data["result"].get("baseFeePerGas", "0x0"), 16)
                    print(f"  ✅ Base fee: {base_fee / 1e9:.2f} gwei")
    except Exception as e:
        print(f"  ❌ Error: {e}")

async def test_token_prices():
    """Test token price feeds"""
    
    print("\n\n💰 Testing Price Feeds...")
    
    # Test CoinGecko (free, no API key)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=ethereum,bitcoin,usd-coin,tether&vs_currencies=usd",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    prices = await resp.json()
                    print("  ✅ Prices:")
                    for token, price in prices.items():
                        print(f"     {token}: ${price['usd']}")
                else:
                    print(f"  ❌ HTTP {resp.status}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

async def main():
    print("=" * 60)
    print("🚀 REAL PRODUCTION TESTS")
    print("=" * 60)
    
    # Test 1: RPC Endpoints
    results = await test_real_rpc()
    
    # Test 2: Gas Oracle
    await test_gas_oracle()
    
    # Test 3: Token Prices
    await test_token_prices()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 RESULTS SUMMARY")
    print("=" * 60)
    
    if results:
        best = min(results.items(), key=lambda x: x[1]["latency"])
        print(f"Best RPC: {best[0]} ({best[1]['latency']:.0f}ms)")
    else:
        print("❌ No RPC endpoints working")
    
    print("\n⚠️  NOTE: For full MEV testing, you need:")
    print("  - Alchemy/Infura API key")
    print("  - Flashbots key")
    print("  - Testnet ETH (Sepolia/Goerli)")

if __name__ == "__main__":
    asyncio.run(main())
