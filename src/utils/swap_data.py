"""
Complete Swap Data Structure
Every swap must have: path, amount_in, amount_out, minOut, pool_liquidity, fee_tier
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class ExchangeType(Enum):
    UNISWAP_V2 = "uniswap_v2"
    UNISWAP_V3 = "uniswap_v3"
    SUSHISWAP = "sushiswap"
    CURVE = "curve"
    BALANCER = "balancer"
    DODO = "dodo"


@dataclass
class SwapRoute:
    """Complete swap route with all details"""
    # Path: list of tokens in order
    path: List[str] = field(default_factory=list)
    
    # Amounts
    amount_in: float = 0.0
    amount_out: float = 0.0
    min_out: float = 0.0  # Minimum acceptable output with slippage
    
    # Pool info
    pool_address: str = ""
    pool_liquidity: float = 0.0  # USD value
    
    # Exchange details
    exchange: str = ""
    fee_tier: int = 3000  # basis points (3000 = 0.3%)
    
    # Additional data
    gas_estimate: int = 150000
    price_impact: float = 0.0  # percentage
    
    def to_dict(self) -> Dict:
        return {
            "path": self.path,
            "amount_in": self.amount_in,
            "amount_out": self.amount_out,
            "min_out": self.min_out,
            "pool_address": self.pool_address,
            "pool_liquidity": self.pool_liquidity,
            "exchange": self.exchange,
            "fee_tier": self.fee_tier,
            "gas_estimate": self.gas_estimate,
            "price_impact": self.price_impact
        }


@dataclass 
class ArbitrageOpportunity:
    """Complete arbitrage opportunity with full details"""
    # Trade path (e.g., ETH -> USDC -> DAI -> ETH)
    path: List[str] = field(default_factory=list)
    
    # Exchange sequence
    exchanges: List[str] = field(default_factory=list)
    
    # Amounts
    amount_in: float = 0.0
    amount_out: float = 0.0
    min_out: float = 0.0
    
    # Per-hop details
    hops: List[SwapRoute] = field(default_factory=list)
    
    # Pool liquidity at each step
    pool_liquidities: List[float] = field(default_factory=list)
    
    # Fee tiers for each exchange
    fee_tiers: List[int] = field(default_factory=list)
    
    # Calculated values
    gross_profit: float = 0.0
    gas_cost: float = 0.0
    flash_loan_fee: float = 0.0
    net_profit: float = 0.0
    
    # Confidence and timing
    confidence: float = 0.0
    timestamp: float = 0.0
    expires_at: float = 0.0  # Unix timestamp
    
    # Token addresses (for on-chain execution)
    token_addresses: List[str] = field(default_factory=list)
    
    def validate(self) -> bool:
        """Validate opportunity has all required fields"""
        if not self.path or len(self.path) < 2:
            return False
        if self.amount_in <= 0:
            return False
        if not self.exchanges:
            return False
        if self.net_profit <= 0:
            return False
        # Check all required fields exist
        for hop in self.hops:
            if not hop.pool_address:
                return False
            if hop.pool_liquidity <= 0:
                return False
        return True
    
    def to_dict(self) -> Dict:
        return {
            "path": self.path,
            "exchanges": self.exchanges,
            "amount_in": self.amount_in,
            "amount_out": self.amount_out,
            "min_out": self.min_out,
            "hops": [h.to_dict() for h in self.hops],
            "pool_liquidities": self.pool_liquidities,
            "fee_tiers": self.fee_tiers,
            "gross_profit": self.gross_profit,
            "gas_cost": self.gas_cost,
            "flash_loan_fee": self.flash_loan_fee,
            "net_profit": self.net_profit,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "expires_at": self.expires_at,
            "token_addresses": self.token_addresses,
            "valid": self.validate()
        }


class SwapDataBuilder:
    """Build complete swap data with all required fields"""
    
    # Fee tiers by exchange (basis points)
    FEE_TIERS = {
        "uniswap_v3": {"low": 500, "medium": 3000, "high": 10000},
        "uniswap_v2": 300,
        "sushiswap": 300,
        "curve": 40,  # Very low fees
        "balancer": 100,
        "dodo": 300,
    }
    
    def __init__(self, rpc_url: str = None):
        self.rpc_url = rpc_url or "http://localhost:8545"
        self._w3 = None
    
    @property
    def w3(self):
        if not self._w3:
            from web3 import Web3
            self._w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        return self._w3
    
    async def build_swap_route(
        self,
        token_in: str,
        token_out: str,
        amount_in: float,
        exchange: str,
        slippage_tolerance: float = 0.01
    ) -> Optional[SwapRoute]:
        """Build complete swap route with all required fields"""
        
        try:
            # Get token addresses
            token_addresses = self._get_token_addresses()
            
            token_in_addr = token_addresses.get(token_in.upper())
            token_out_addr = token_addresses.get(token_out.upper())
            
            if not token_in_addr or not token_out_addr:
                return None
            
            # Get pool address and liquidity
            pool_address = await self._get_pool_address(token_in_addr, token_out_addr, exchange)
            
            if not pool_address:
                return None
            
            # Get pool liquidity
            liquidity = await self._get_pool_liquidity(pool_address, token_in_addr, token_out_addr)
            
            # Get amount out (quote)
            amount_out = await self._get_amount_out(
                token_in_addr, token_out_addr, amount_in, exchange
            )
            
            if amount_out <= 0:
                return None
            
            # Calculate min out with slippage
            min_out = amount_out * (1 - slippage_tolerance)
            
            # Get fee tier
            fee_tier = self._get_fee_tier(exchange)
            
            # Calculate price impact
            price_impact = self._calculate_price_impact(amount_in, amount_out, liquidity)
            
            # Estimate gas
            gas_estimate = self._estimate_gas(exchange)
            
            return SwapRoute(
                path=[token_in, token_out],
                amount_in=amount_in,
                amount_out=amount_out,
                min_out=min_out,
                pool_address=pool_address,
                pool_liquidity=liquidity,
                exchange=exchange,
                fee_tier=fee_tier,
                gas_estimate=gas_estimate,
                price_impact=price_impact
            )
            
        except Exception as e:
            return None
    
    async def build_arbitrage_opportunity(
        self,
        token_path: List[str],
        exchanges: List[str],
        amount_in: float,
        flash_loan_fee: float = 0.0009
    ) -> Optional[ArbitrageOpportunity]:
        """Build complete arbitrage opportunity"""
        
        if len(token_path) < 2 or len(token_path) != len(exchanges) + 1:
            return None
        
        hops = []
        liquidities = []
        fee_tiers = []
        
        current_amount = amount_in
        
        # Build each hop
        for i in range(len(exchanges)):
            token_in = token_path[i]
            token_out = token_path[i + 1]
            exchange = exchanges[i]
            
            hop = await self.build_swap_route(
                token_in, token_out, current_amount, exchange
            )
            
            if not hop:
                return None
            
            hops.append(hop)
            liquidities.append(hop.pool_liquidity)
            fee_tiers.append(hop.fee_tier)
            current_amount = hop.amount_out
        
        # Final amount out
        final_amount_out = current_amount
        
        # Calculate profits
        gross_profit = final_amount_out - amount_in
        gas_cost = 50  # Estimated
        flash_loan_fee_usd = amount_in * flash_loan_fee
        net_profit = gross_profit - gas_cost - flash_loan_fee_usd
        
        # Calculate confidence based on liquidity
        min_liquidity = min(liquidities) if liquidities else 0
        confidence = min(0.95, 0.5 + (min_liquidity / 1000000) * 0.1)
        
        # Get token addresses
        token_addresses = [self._get_token_addresses().get(t, "") for t in token_path]
        
        return ArbitrageOpportunity(
            path=token_path,
            exchanges=exchanges,
            amount_in=amount_in,
            amount_out=final_amount_out,
            min_out=final_amount_out * 0.99,  # 1% slippage buffer
            hops=hops,
            pool_liquidities=liquidities,
            fee_tiers=fee_tiers,
            gross_profit=gross_profit,
            gas_cost=gas_cost,
            flash_loan_fee=flash_loan_fee_usd,
            net_profit=net_profit,
            confidence=confidence,
            timestamp=__import__('time').time(),
            expires_at=__import__('time').time() + 30,  # 30 seconds
            token_addresses=token_addresses
        )
    
    def _get_token_addresses(self) -> Dict[str, str]:
        return {
            "ETH": "0x0000000000000000000000000000000000000000",
            "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "DAI": "0x6B175474E89094C44Da98b954EedE6C8EDc609666",
            "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
            "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
            "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
            "AAVE": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
            "CRV": "0xD533a949740bb3306d119CC777fa900bA034cd52",
            "SUSHI": "0x6B3595068778DD592e39A122f4f5a5cF09C90fE2",
            "MATIC": "0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeeb0",
            "LDO": "0x5A98FcBEA4Cf5422B8948a6e3f2eF3A92dF8B80",
            "OP": "0x4200000000000000000000000000000000000006",
            "ARB": "0x912CE59144191C1204E61159e7a6E8fA17F5A95A",
        }
    
    async def _get_pool_address(self, token_a: str, token_b: str, exchange: str) -> Optional[str]:
        try:
            if "uniswap_v3" in exchange:
                factory = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
                fee_tiers = [3000, 500, 10000]
                
                factory_abi = '[{"constant":true,"inputs":[{"name":"tokenA","type":"address"},{"name":"tokenB","type":"address"},{"name":"fee","type":"uint24"}],"name":"getPool","outputs":[{"name":"pool","type":"address"}],"type":"function"}]'
                factory_contract = self.w3.eth.contract(address=factory, abi=factory_abi)
                
                for fee in fee_tiers:
                    pool = factory_contract.functions.getPool(token_a, token_b, fee).call()
                    if pool != "0x0000000000000000000000000000000000000000":
                        return pool
            
            elif "uniswap_v2" in exchange or "sushi" in exchange:
                factory = "0x5C69bEe701ef814a2B6fe3cF77eE1eD5e2b3f2c4"
                
                if token_a.lower() > token_b.lower():
                    token_a, token_b = token_b, token_a
                
                factory_abi = '[{"constant":true,"inputs":[{"name":"tokenA","type":"address"},{"name":"tokenB","type":"address"}],"name":"getPair","outputs":[{"name":"pair","type":"address"}],"type":"function"}]'
                factory_contract = self.w3.eth.contract(address=factory, abi=factory_abi)
                pair = factory_contract.functions.getPair(token_a, token_b).call()
                
                if pair != "0x0000000000000000000000000000000000000000":
                    return pair
            
            return None
        except:
            return None
    
    async def _get_pool_liquidity(self, pool_address: str, token_a: str, token_b: str) -> float:
        try:
            # Try Uniswap V2 style
            pair_abi = '[{"constant":true,"inputs":[],"name":"getReserves","outputs":[{"name":"reserve0","type":"uint112"},{"name":"reserve1","type":"uint112"},{"name":"blockTimestampLast","type":"uint32"}],"type":"function"}]'
            contract = self.w3.eth.contract(address=pool_address, abi=pair_abi)
            reserves = contract.functions.getReserves().call()
            
            # Get token prices (simplified - use ETH as base)
            reserve0 = reserves[0]
            reserve1 = reserves[1]
            
            # Assume $2000 per ETH, calculate USD liquidity
            # This would use real prices in production
            liquidity_eth = (reserve0 + reserve1) / 1e18
            liquidity_usd = liquidity_eth * 2000  # Simplified
            
            return liquidity_usd
        except:
            return 0.0
    
    async def _get_amount_out(
        self, 
        token_in: str, 
        token_out: str, 
        amount_in: float,
        exchange: str
    ) -> float:
        try:
            # Get pool and reserves
            pool = await self._get_pool_address(token_in, token_out, exchange)
            if not pool:
                return 0.0
            
            # Get reserves
            reserves_abi = '[{"constant":true,"inputs":[],"name":"getReserves","outputs":[{"name":"reserve0","type":"uint112"},{"name":"reserve1","type":"uint112"}],"type":"function"}]'
            contract = self.w3.eth.contract(address=pool, abi=reserves_abi)
            reserves = contract.functions.getReserves().call()
            
            # Determine which is input and output
            if token_in.lower() < token_out.lower():
                reserve_in = reserves[0]
                reserve_out = reserves[1]
            else:
                reserve_in = reserves[1]
                reserve_out = reserves[0]
            
            # Get fee
            fee = self._get_fee_tier(exchange) / 10000
            
            # Calculate output with fee
            amount_in_with_fee = amount_in * (1 - fee)
            numerator = amount_in_with_fee * reserve_out
            denominator = reserve_in + amount_in_with_fee
            
            return numerator / denominator if denominator > 0 else 0
            
        except:
            return 0.0
    
    def _get_fee_tier(self, exchange: str) -> int:
        if "uniswap_v3" in exchange:
            return 3000  # Default 0.3%
        return self.FEE_TIERS.get(exchange, 300)
    
    def _calculate_price_impact(self, amount_in: float, amount_out: float, liquidity: float) -> float:
        if liquidity <= 0:
            return 100.0
        
        # Simple price impact calculation
        # Larger trades relative to liquidity = higher impact
        trade_size_ratio = amount_in / liquidity
        impact = trade_size_ratio * 100  # percentage
        
        return min(impact, 100.0)  # Cap at 100%
    
    def _estimate_gas(self, exchange: str) -> int:
        gas_estimates = {
            "uniswap_v3": 200000,
            "uniswap_v2": 150000,
            "sushiswap": 180000,
            "curve": 300000,
            "balancer": 250000,
        }
        return gas_estimates.get(exchange, 200000)


# Factory
def create_swap_builder(rpc_url: str = None) -> SwapDataBuilder:
    return SwapDataBuilder(rpc_url)


# Example usage
async def main():
    builder = create_swap_builder("http://localhost:8545")
    
    # Build single swap
    swap = await builder.build_swap_route(
        token_in="ETH",
        token_out="USDC",
        amount_in=10000,
        exchange="uniswap_v3"
    )
    
    if swap:
        print("Swap Route:")
        print(f"  Path: {' -> '.join(swap.path)}")
        print(f"  Amount In: ${swap.amount_in:,.2f}")
        print(f"  Amount Out: ${swap.amount_out:,.2f}")
        print(f"  Min Out: ${swap.min_out:,.2f}")
        print(f"  Pool Liquidity: ${swap.pool_liquidity:,.2f}")
        print(f"  Fee Tier: {swap.fee_tier} bps")
        print(f"  Price Impact: {swap.price_impact:.2f}%")
    
    # Build arbitrage
    arb = await builder.build_arbitrage_opportunity(
        token_path=["ETH", "USDC", "DAI", "ETH"],
        exchanges=["uniswap_v3", "uniswap_v3", "uniswap_v3"],
        amount_in=10000
    )
    
    if arb:
        print("\nArbitrage Opportunity:")
        print(f"  Path: {' -> '.join(arb.path)}")
        print(f"  Amount In: ${arb.amount_in:,.2f}")
        print(f"  Amount Out: ${arb.amount_out:,.2f}")
        print(f"  Net Profit: ${arb.net_profit:,.2f}")
        print(f"  Valid: {arb.validate()}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
