#!/bin/bash
# Ultimate PowerSaver Startup Script

echo "=========================================="
echo "   🚀 POWERSAVER ULTIMATE TRADING BOT"
echo "=========================================="

# Check if PRIVATE_KEY is set
if [ -z "$PRIVATE_KEY" ]; then
    echo "❌ ERROR: PRIVATE_KEY not set!"
    echo ""
    echo "Please set your private key:"
    echo "  export PRIVATE_KEY='0xYourPrivateKeyHere'"
    echo ""
    echo "Or create a .env file from .env.example"
    exit 1
fi

# Check if RPC URL is set
if [ -z "$ETHEREUM_RPC" ]; then
    echo "❌ ERROR: ETHEREUM_RPC not set!"
    echo ""
    echo "Please set your RPC URL:"
    echo "  export ETHEREUM_RPC='https://mainnet.infura.io/v3/YOUR_KEY'"
    exit 1
fi

echo "✅ Configuration loaded"
echo ""
echo "Starting Ultimate Trading System..."
echo ""

# Run the system
cd /workspace/project/PowerSaver
python3 -m src.ultimate_trading
