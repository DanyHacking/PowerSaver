"""
External Signal API
Allows external systems to inject signals and price overrides
"""

import asyncio
import logging
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time

logger = logging.getLogger(__name__)


@dataclass
class ExternalSignal:
    """Signal from external system"""
    signal_type: str  # "buy", "sell", "hold", "publish"
    token: str
    price: float  # Override price (optional)
    confidence: float
    source: str  # Who sent this signal
    timestamp: float = field(default_factory=time.time)


@dataclass  
class PriceOverride:
    """Manual price override from external source"""
    token: str
    price: float
    source: str
    timestamp: float = field(default_factory=time.time)
    ttl: int = 60  # seconds


class ExternalSignalAPI:
    """
    API for receiving external signals and price overrides
    Can be called via HTTP, WebSocket, or message queue
    """
    
    def __init__(self):
        # Price overrides (higher priority than oracle)
        self._price_overrides: Dict[str, PriceOverride] = {}
        
        # External signals queue
        self._signal_queue: asyncio.Queue = asyncio.Queue()
        
        # Signal history
        self._signal_history: list[ExternalSignal] = []
        self._max_history = 100
        
        # Whether to use external signals
        self._enabled = True
    
    # ========== PRICE OVERRIDE API ==========
    
    async def set_price_override(self, token: str, price: float, source: str = "manual", ttl: int = 60) -> bool:
        """
        Set manual price override
        POST /api/price Override
        
        Example:
        {
            "token": "ETH",
            "price": 1850.50,
            "source": "my_signal_provider",
            "ttl": 120
        }
        """
        token = token.upper()
        
        if price <= 0:
            logger.error(f"Invalid price {price} for {token}")
            return False
        
        override = PriceOverride(
            token=token,
            price=price,
            source=source,
            ttl=ttl
        )
        
        self._price_overrides[token] = override
        logger.info(f"Price override set: {token} = ${price} (source: {source}, ttl: {ttl}s)")
        return True
    
    def get_price_override(self, token: str) -> Optional[float]:
        """
        Get price override if valid
        Returns None if no override or expired
        """
        token = token.upper()
        
        if token not in self._price_overrides:
            return None
        
        override = self._price_overrides[token]
        
        # Check if expired
        if time.time() - override.timestamp > override.ttl:
            del self._price_overrides[token]
            return None
        
        return override.price
    
    async def clear_price_override(self, token: str) -> bool:
        """Clear price override"""
        token = token.upper()
        if token in self._price_overrides:
            del self._price_overrides[token]
            logger.info(f"Price override cleared for {token}")
            return True
        return False
    
    # ========== SIGNAL API ==========
    
    async def receive_signal(
        self,
        signal_type: str,
        token: str,
        price: Optional[float] = None,
        confidence: float = 1.0,
        source: str = "manual"
    ) -> bool:
        """
        Receive external trading signal
        POST /api/signal
        
        Example:
        {
            "signal": "buy",
            "token": "ETH",
            "price": 1850.50,  // optional override
            "confidence": 0.95,
            "source": "my_ai_model"
        }
        """
        # Validate signal
        if signal_type not in ["buy", "sell", "hold"]:
            logger.error(f"Invalid signal type: {signal_type}")
            return False
        
        token = token.upper()
        
        # If price provided, set override too
        if price and price > 0:
            await self.set_price_override(token, price, source)
        
        signal = ExternalSignal(
            signal_type=signal_type,
            token=token,
            price=price,
            confidence=confidence,
            source=source
        )
        
        # Add to queue for processing
        await self._signal_queue.put(signal)
        
        # Add to history
        self._signal_history.append(signal)
        if len(self._signal_history) > self._max_history:
            self._signal_history = self._signal_history[-self._max_history:]
        
        logger.info(f"External signal received: {signal_type.upper()} {token} @ ${price or 'oracle'} (conf: {confidence})")
        return True
    
    async def get_next_signal(self, timeout: float = 1.0) -> Optional[ExternalSignal]:
        """Get next signal from queue (non-blocking)"""
        try:
            return await asyncio.wait_for(self._signal_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
    
    def get_signal_history(self, limit: int = 10) -> list[Dict]:
        """Get recent signals"""
        return [
            {
                "signal_type": s.signal_type,
                "token": s.token,
                "price": s.price,
                "confidence": s.confidence,
                "source": s.source,
                "timestamp": s.timestamp
            }
            for s in self._signal_history[-limit:]
        ]
    
    # ========== ORACLE INTEGRATION ==========
    
    async def get_effective_price(self, token: str, oracle_price: Optional[float] = None) -> float:
        """
        Get effective price - override or oracle
        This is what your trading logic should call
        """
        # Check override first
        override = self.get_price_override(token)
        if override:
            return override
        
        # Fall back to oracle price
        if oracle_price:
            return oracle_price
        
        # No price available
        return 0.0
    
    # ========== FLASK HTTP SERVER ==========
    
    def create_flask_app(self, oracle_publisher=None):
        """
        Create Flask API server
        
        Args:
            oracle_publisher: OnChainOraclePublisher instance for on-chain publishing
        """
        from flask import Flask, request, jsonify
        
        app = Flask(__name__)
        self.oracle_publisher = oracle_publisher
        
        @app.route('/api/price/override', methods=['POST'])
        def set_price():
            """Set price override"""
            data = request.json
            token = data.get('token')
            price = data.get('price')
            source = data.get('source', 'http_api')
            ttl = data.get('ttl', 60)
            
            if not token or not price:
                return jsonify({"error": "Missing token or price"}), 400
            
            success = asyncio.run(self.set_price_override(token, price, source, ttl))
            return jsonify({"success": success})
        
        @app.route('/api/price/override/<token>', methods=['DELETE'])
        def clear_price(token):
            """Clear price override"""
            success = asyncio.run(self.clear_price_override(token))
            return jsonify({"success": success})
        
        @app.route('/api/signal', methods=['POST'])
        def receive_signal():
            """Receive trading signal"""
            data = request.json
            signal = data.get('signal')
            token = data.get('token')
            price = data.get('price')
            confidence = data.get('confidence', 1.0)
            source = data.get('source', 'http_api')
            
            if not signal or not token:
                return jsonify({"error": "Missing signal or token"}), 400
            
            success = asyncio.run(self.receive_signal(signal, token, price, confidence, source))
            return jsonify({"success": success})
        
        @app.route('/api/oracle/publish', methods=['POST'])
        def publish_to_chain():
            """
            Publish price to blockchain oracle
            
            Example:
            {
                "token": "ETH",
                "price": 1850.50,
                "decimals": 8
            }
            
            Other DeFi protocols can now read this price from the oracle contract
            """
            data = request.json
            token = data.get('token')
            price = data.get('price')
            decimals = data.get('decimals', 8)
            
            if not token or not price:
                return jsonify({"error": "Missing token or price"}), 400
            
            if not self.oracle_publisher:
                return jsonify({"error": "Oracle publisher not configured"}), 500
            
            # Run async publish
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.oracle_publisher.publish_to_oracle_contract(
                        contract_address=self.oracle_publisher.PRICE_FEEDS.get(token.upper()),
                        token=token,
                        price=price,
                        decimals=decimals
                    )
                )
                tx_hash = future.result()
            
            if tx_hash:
                return jsonify({
                    "success": True,
                    "token": token,
                    "price": price,
                    "tx_hash": tx_hash,
                    "explorer_url": f"https://etherscan.io/tx/{tx_hash}"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Failed to publish to blockchain"
                })
        
        @app.route('/api/oracle/batch', methods=['POST'])
        def batch_publish():
            """Batch publish prices to blockchain"""
            data = request.json
            prices = data.get('prices', {})
            decimals = data.get('decimals', 8)
            
            if not prices:
                return jsonify({"error": "Missing prices"}), 400
            
            if not self.oracle_publisher:
                return jsonify({"error": "Oracle publisher not configured"}), 500
            
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.oracle_publisher.batch_update(prices, decimals)
                )
                results = future.result()
            
            return jsonify({
                "success": True,
                "results": results
            })
        
        @app.route('/api/signals', methods=['GET'])
        def get_signals():
            """Get signal history"""
            limit = request.args.get('limit', 10, type=int)
            return jsonify(self.get_signal_history(limit))
        
        @app.route('/api/status', methods=['GET'])
        def status():
            """Get API status"""
            return jsonify({
                "enabled": self._enabled,
                "active_overrides": list(self._price_overrides.keys()),
                "queue_size": self._signal_queue.qsize(),
                "oracle_publisher": self.oracle_publisher is not None
            })
        
        return app


# ========== USAGE EXAMPLE ==========

async def example_usage():
    """How to integrate with your trading bot"""
    
    api = ExternalSignalAPI()
    
    # Example 1: Set price override
    await api.set_price_override("ETH", 1850.50, "my_signal_provider", ttl=120)
    
    # Example 2: Receive trading signal
    await api.receive_signal("buy", "ETH", price=1850.50, confidence=0.95, source="my_ai")
    
    # Example 3: Get effective price in your trading logic
    oracle_price = 1800.0
    effective_price = await api.get_effective_price("ETH", oracle_price)
    print(f"Using price: ${effective_price}")
    
    # Example 4: Process signals in your loop
    while True:
        signal = await api.get_next_signal()
        if signal:
            print(f"Processing signal: {signal.signal_type} {signal.token}")


if __name__ == "__main__":
    # Run Flask server
    api = ExternalSignalAPI()
    app = api.create_flask_app()
    app.run(host="0.0.0.0", port=8080)
