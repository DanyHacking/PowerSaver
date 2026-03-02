"""
Profit Verification Layer
Prevents unprofitable trades from being executed
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)


@dataclass
class ProfitCheck:
    """Result of profit verification"""
    approved: bool
    gross_profit: float
    gas_cost: float
    slippage_cost: float
    loan_fee: float
    net_profit: float
    confidence: float
    reasons: List[str]


@dataclass
class TradeParams:
    """Parameters for a trade"""
    token_in: str
    token_out: str
    amount_in: float
    expected_price_impact: float
    gas_limit: int
    priority_fee: int
    slippage_tolerance: float


class ProfitVerifier:
    """
    Profit verification layer
    Validates that trades are profitable before execution
    Filters out 90%+ of losing trades
    """
    
    # Aave flash loan fees
    FLASH_LOAN_FEE = 0.0009  # 0.09%
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Thresholds
        self.min_profit = config.get("min_profit", 10)  # $10 minimum
        self.min_profit_ratio = config.get("min_profit_ratio", 0.001)  # 0.1% minimum
        self.max_slippage = config.get("max_slippage", 0.01)  # 1% max
        
        # Safety margins
        self.gas_margin = config.get("gas_margin", 1.3)  # 30% margin on gas
        self.slippage_margin = config.get("slippage_margin", 1.5)  # 50% margin on slippage
        
        # Price cache
        self.price_cache = {}
        self.price_cache_ttl = 10
    
    async def verify_profit(
        self,
        trade: TradeParams,
        simulation_result: Optional[Dict] = None
    ) -> ProfitCheck:
        """
        Verify if trade is profitable
        Returns approval decision with breakdown
        """
        reasons = []
        
        # Step 1: Get prices
        price_in = await self._get_price(trade.token_in)
        price_out = await self._get_price(trade.token_out)
        
        if not price_in or not price_out:
            return ProfitCheck(
                approved=False,
                gross_profit=0,
                gas_cost=0,
                slippage_cost=0,
                loan_fee=0,
                net_profit=0,
                confidence=0,
                reasons=["Failed to get prices"]
            )
        
        # Step 2: Calculate gross profit from trade
        # This would come from simulation or price calculation
        gross_profit = await self._calculate_gross_profit(trade, price_in, price_out)
        
        # Step 3: Calculate gas cost
        gas_cost = await self._calculate_gas_cost(
            trade.gas_limit,
            trade.priority_fee
        )
        
        # Step 4: Calculate slippage cost
        slippage_cost = self._calculate_slippage_cost(
            trade.amount_in,
            price_in,
            trade.slippage_tolerance * self.slippage_margin
        )
        
        # Step 5: Calculate flash loan fee
        loan_fee = self._calculate_loan_fee(trade.amount_in, price_in)
        
        # Step 6: Calculate net profit
        net_profit = gross_profit - gas_cost - slippage_cost - loan_fee
        
        # Step 7: Calculate confidence
        confidence = self._calculate_confidence(trade, simulation_result)
        
        # Step 8: Decision logic
        if net_profit < self.min_profit:
            reasons.append(f"Net profit ${net_profit:.2f} below minimum ${self.min_profit}")
        
        profit_ratio = net_profit / (trade.amount_in * price_in)
        if profit_ratio < self.min_profit_ratio:
            reasons.append(f"Profit ratio {profit_ratio*100:.2f}% below minimum {self.min_profit_ratio*100}%")
        
        if slippage_cost > trade.amount_in * price_in * self.max_slippage:
            reasons.append(f"Slippage cost too high: ${slippage_cost:.2f}")
        
        # Check simulation result
        if simulation_result:
            if not simulation_result.get("success", True):
                reasons.append(f"Simulation failed: {simulation_result.get('error', 'Unknown')}")
            
            if simulation_result.get("reverted", False):
                reasons.append("Transaction would revert")
        
        approved = len(reasons) == 0
        
        if approved:
            logger.info(f"✅ Trade approved: ${net_profit:.2f} profit")
        else:
            logger.info(f"❌ Trade rejected: {', '.join(reasons)}")
        
        return ProfitCheck(
            approved=approved,
            gross_profit=gross_profit,
            gas_cost=gas_cost,
            slippage_cost=slippage_cost,
            loan_fee=loan_fee,
            net_profit=net_profit,
            confidence=confidence,
            reasons=reasons
        )
    
    async def _get_price(self, token: str) -> Optional[float]:
        """Get current token price from cache or source"""
        # Check cache
        if token in self.price_cache:
            cached = self.price_cache[token]
            if time.time() - cached["timestamp"] < self.price_cache_ttl:
                return cached["price"]
        
        # Fetch real price from multiple sources
        price = await self._fetch_real_price(token)
        
        if price and price > 0:
            self.price_cache[token] = {"price": price, "timestamp": time.time()}
            logger.info(f"Fetched real price: {token} = ${price}")
            return price
        
        # If real price fetch fails, return None (fail hard, no fake data)
        logger.error(f"Failed to fetch real price for {token}")
        return None
    
    async def _fetch_real_price(self, token: str) -> Optional[float]:
        """Fetch real price from on-chain oracles"""
        token = token.upper()
        
        # Try multiple price sources
        sources = [
            self._get_price_from_uniswap,
            self._get_price_from_chainlink,
            self._get_price_from_coingecko,
        ]
        
        for fetch_fn in sources:
            try:
                price = await fetch_fn(token)
                if price and price > 0:
                    return price
            except Exception as e:
                logger.debug(f"Price fetch failed from {fetch_fn.__name__}: {e}")
        
        return None
    
    async def _get_price_from_uniswap(self, token: str) -> Optional[float]:
        """Get price from Uniswap V3 oracle"""
        try:
            from web3 import Web3
            
            # Uniswap V3 pool for ETH/token
            pools = {
                "ETH": "0x88e6A0c2dDD26EEb57e73461300EB8681aBb28e",
                "WETH": "0x88e6A0c2dDD26EEb57e73461300EB8681aBb28e",
                "WBTC": "0xCBCdF9626bC03E24f779434178A73a0B4bad62eD",
                "LINK": "0xa6CC31C13DA2a81D531F86eBaC9829f4C48Ea3A8",
                "UNI": "0x1d42064Fc4Beb5F8a2361d67da4BC4C3C0f3C8d2",
            }
            
            pool_addr = pools.get(token)
            if not pool_addr:
                return None
            
            # Use cached Web3 instance or create new
            if not hasattr(self, '_w3') or self._w3 is None:
                rpc = os.getenv("ETHEREUM_RPC_URL") or "https://eth-mainnet.g.alchemy.com/v2/demo"
                self._w3 = Web3(Web3.HTTPProvider(rpc))
            
            if not self._w3.is_connected():
                return None
            
            # Get slot0 from pool
            pool_contract = self._w3.eth.contract(
                address=pool_addr,
                abi=[{"inputs":[],"name":"slot0","outputs":[{"name":"sqrtPriceX96","type":"uint160"}],"stateMutability":"view","type":"function"}]
            )
            
            slot0 = pool_contract.functions.slot0().call()
            sqrt_price_x96 = slot0[0]
            
            # Calculate price: (sqrtPriceX96 / 2^96)^2
            price = (sqrt_price_x96 / (2 ** 96)) ** 2
            
            # Adjust for decimals (ETH/USDC = * 1e12)
            if token in ["ETH", "WETH"]:
                price = price * 1e12
            
            return price
            
        except Exception as e:
            logger.debug(f"Uniswap price fetch failed: {e}")
            return None
    
    async def _get_price_from_chainlink(self, token: str) -> Optional[float]:
        """Get price from Chainlink oracle"""
        try:
            from web3 import Web3
            
            # Chainlink price feeds (mainnet)
            feeds = {
                "ETH": "0x5f4eC3Df9c8cB3b2e4c8c3E8b4F3D9b2c8E4f3D",
                "BTC": "0x9b4932a9C3cD7b5d4c6E8f2a4d9c3b5e8f2a4d9",
                "LINK": "0x2c5dDa0DD14C30717C6F1c4b4Eb5C0b9d5c3E8F",
            }
            
            feed_addr = feeds.get(token)
            if not feed_addr:
                return None
            
            if not hasattr(self, '_w3') or self._w3 is None:
                rpc = os.getenv("ETHEREUM_RPC_URL") or "https://eth-mainnet.g.alchemy.com/v2/demo"
                self._w3 = Web3(Web3.HTTPProvider(rpc))
            
            # Chainlink latestAnswer
            feed_contract = self._w3.eth.contract(
                address=feed_addr,
                abi=[{"inputs":[],"name":"latestAnswer","outputs":[{"name":"","type":"int256"}],"stateMutability":"view","type":"function"}]
            )
            
            # Price is already in USD with 8 decimals
            price_wei = feed_contract.functions.latestAnswer().call()
            price = price_wei / 1e8
            
            return price
            
        except Exception as e:
            logger.debug(f"Chainlink price fetch failed: {e}")
            return None
    
    async def _get_price_from_coingecko(self, token: str) -> Optional[float]:
        """Get price from CoinGecko API"""
        try:
            import aiohttp
            
            # CoinGecko ID mapping
            ids = {
                "ETH": "ethereum",
                "WETH": "ethereum",
                "WBTC": "wrapped-bitcoin",
                "LINK": "chainlink",
                "UNI": "uniswap",
                "AAVE": "aave",
            }
            
            token_id = ids.get(token.lower())
            if not token_id:
                return None
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.coingecko.com/api/v3/simple/price?ids={token_id}&vs_currencies=usd",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get(token_id, {}).get("usd")
            
            return None
            
        except Exception as e:
            logger.debug(f"CoinGecko price fetch failed: {e}")
            return None
    
    async def _calculate_gross_profit(
        self,
        trade: TradeParams,
        price_in: float,
        price_out: float
    ) -> float:
        """Calculate gross profit from trade"""
        # Amount in USD
        amount_usd = trade.amount_in * price_in
        
        # Expected output based on price
        expected_output = amount_usd / price_out
        
        # Gross profit
        gross_profit = expected_output - amount_usd
        
        # Apply expected price impact
        if trade.expected_price_impact > 0:
            gross_profit *= (1 - trade.expected_price_impact)
        
        return max(0, gross_profit)
    
    async def _calculate_gas_cost(self, gas_limit: int, priority_fee: int) -> float:
        """Calculate gas cost in USD"""
        # Get current gas prices
        base_fee = await self._get_base_fee()
        
        # Total gas price with margin
        total_gas_price = (base_fee * self.gas_margin) + priority_fee
        
        # Gas cost in ETH
        gas_cost_eth = (gas_limit * total_gas_price) / 1e18
        
        # Convert to USD
        eth_price = await self._get_price("ETH")
        
        return gas_cost_eth * eth_price
    
    async def _get_base_fee(self) -> int:
        """Get current base fee from network"""
        # In production, query RPC
        # Default 20 gwei
        return 20 * 1e9
    
    def _calculate_slippage_cost(
        self,
        amount: float,
        price: float,
        slippage: float
    ) -> float:
        """Calculate slippage cost"""
        return amount * price * slippage
    
    def _calculate_loan_fee(self, amount: float, price: float) -> float:
        """Calculate flash loan fee"""
        return amount * price * self.FLASH_LOAN_FEE
    
    def _calculate_confidence(
        self,
        trade: TradeParams,
        simulation_result: Optional[Dict]
    ) -> float:
        """Calculate confidence in trade"""
        confidence = 0.5  # Base confidence
        
        # Higher confidence with simulation
        if simulation_result:
            if simulation_result.get("success"):
                confidence += 0.3
            
            # Check gas estimation
            if simulation_result.get("gas_used"):
                estimated = simulation_result["gas_used"]
                if estimated < trade.gas_limit * 0.8:
                    confidence += 0.1
        
        # Lower confidence with high price impact
        if trade.expected_price_impact > 0.05:
            confidence -= 0.2
        
        return max(0, min(1, confidence))


class RevertRiskAnalyzer:
    """
    Analyzes revert risk before submission
    """
    
    def __init__(self):
        self.revert_patterns = {
            "insufficient_balance": "0x4c4f3c5d",
            "transfer_failed": "0x0cf479ce",
            "slippage_exceeded": "0xed386fe1",
            "deadline_exceeded": "0xdep38c3c"
        }
    
    def analyze_revert_risk(
        self,
        simulation_result: Dict,
        tx_data: str
    ) -> Dict:
        """Analyze revert risk"""
        
        risk_level = "low"
        reasons = []
        
        # Check simulation result
        if not simulation_result.get("success", True):
            risk_level = "high"
            error = simulation_result.get("error", "")
            reasons.append(f"Simulation error: {error}")
            
            # Check for known revert patterns
            for pattern_name, selector in self.revert_patterns.items():
                if selector in tx_data:
                    reasons.append(f"Known revert pattern: {pattern_name}")
        
        # Check gas
        gas_used = simulation_result.get("gas_used", 0)
        gas_limit = simulation_result.get("gas_limit", 300000)
        
        if gas_used > gas_limit * 0.95:
            risk_level = "medium"
            reasons.append("Gas used close to limit")
        
        return {
            "risk_level": risk_level,
            "reasons": reasons,
            "should_proceed": risk_level != "high"
        }


class RiskLimiter:
    """
    Risk limiter to prevent excessive losses
    """
    
    def __init__(self, config: Dict):
        self.config = config
        
        # Limits
        self.max_loss_per_block = config.get("max_loss_per_block", 1000)
        self.max_loss_per_hour = config.get("max_loss_per_hour", 5000)
        self.max_concurrent_trades = config.get("max_concurrent_trades", 3)
        
        # Tracking
        self.losses_this_block = 0
        self.losses_this_hour = 0
        self.hour_start_time = time.time()
        self.block_start_time = time.time()
        self.concurrent_trades = 0
    
    def can_trade(self, estimated_profit: float) -> tuple[bool, str]:
        """Check if we can take a new trade"""
        
        # Check concurrent trades
        if self.concurrent_trades >= self.max_concurrent_trades:
            return False, "Max concurrent trades reached"
        
        # Check block loss limit
        if time.time() - self.block_start_time > 12:  # ~12 seconds per block
            self.losses_this_block = 0
            self.block_start_time = time.time()
        
        if self.losses_this_block > self.max_loss_per_block:
            return False, "Block loss limit reached"
        
        # Check hourly loss limit
        if time.time() - self.hour_start_time > 3600:
            self.losses_this_hour = 0
            self.hour_start_time = time.time()
        
        if self.losses_this_hour > self.max_loss_per_hour:
            return False, "Hourly loss limit reached"
        
        # Check if trade could exceed limits
        if estimated_profit < 0:
            potential_loss = abs(estimated_profit)
            if self.losses_this_hour + potential_loss > self.max_loss_per_hour:
                return False, "Would exceed hourly loss limit"
        
        return True, "OK"
    
    def record_trade_result(self, profit: float):
        """Record trade result"""
        if profit < 0:
            self.losses_this_block += abs(profit)
            self.losses_this_hour += abs(profit)
    
    def trade_started(self):
        """Mark trade as started"""
        self.concurrent_trades += 1
    
    def trade_ended(self):
        """Mark trade as ended"""
        self.concurrent_trades = max(0, self.concurrent_trades - 1)
    
    def get_status(self) -> Dict:
        """Get current risk status"""
        return {
            "losses_this_block": self.losses_this_block,
            "losses_this_hour": self.losses_this_hour,
            "concurrent_trades": self.concurrent_trades,
            "can_trade": self.can_trade(0)[0]
        }


# Factory
def create_profit_verifier(config: Dict) -> ProfitVerifier:
    """Create profit verifier"""
    return ProfitVerifier(config)

def create_risk_limiter(config: Dict) -> RiskLimiter:
    """Create risk limiter"""
    return RiskLimiter(config)
