#!/bin/bash
set -e
cd "$(dirname "$0")"

# Auto-install dependencies
pip3 install -q python-dotenv web3 2>/dev/null || pip install -q python-dotenv web3 2>/dev/null || true

# Generate .env if missing
if [ ! -f .env ]; then
    cp .env.example .env
fi

# Auto-configure if placeholder values
if grep -q "YOUR_INFURA\|0x0000000000000000000000000000000000000000000000" .env 2>/dev/null; then
    # Just ensure basic config exists
    if ! grep -q "^ETHEREUM_RPC_URL=" .env; then
        echo "ETHEREUM_RPC_URL=https://rpc.ankr.com/eth" >> .env
    fi
fi

# Run the bot
exec python3 -m src.main --network mainnet
