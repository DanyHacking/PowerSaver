#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "🚀 POWERSAVER - AVTONOMNI TRGOVALNI BOT"
echo "=========================================="

# Auto-install dependencies
pip3 install -q python-dotenv web3 eth-account 2>/dev/null || true

# Check if Erigon is needed
USE_LOCAL_ERIGON=${USE_LOCAL_ERIGON:-false}

if [ "$USE_LOCAL_ERIGON" = "true" ]; then
    echo "🔧 Začenjam Erigon node..."
    docker-compose up -d erigon
    echo "⏳ Čakam da se Erigon sync-a (to lahko traja ure/dni)..."
    echo "   Za hitrejši začetek pritisni Ctrl+C in nadaljuj brez Erigona"
    echo "   Ali nastavi USE_LOCAL_ERIGON=false"
    
    # Wait for Erigon to be ready
    for i in {1..60}; do
        if curl -s -X POST -H "Content-Type: application/json" \
           --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
           http://localhost:8545 >/dev/null 2>&1; then
            echo "✅ Erigon je pripravljen!"
            break
        fi
        echo "   Čakam... ($i/60)"
        sleep 5
    done
fi

# Ensure .env exists
if [ ! -f .env ]; then
    cp .env.example .env
fi

# Load existing or generate wallet
source .env 2>/dev/null || true

# Generate wallet if not configured
if [ -z "$TRADING_WALLET_PRIVATE_KEY" ] || [ "$TRADING_WALLET_PRIVATE_KEY" == "0x0000" ]; then
    echo "📋 Ustvarjam novo denarnico..."
    python3 << 'PYEOF'
from eth_account import Account
import os

acct = Account.create()
env_lines = []
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        env_lines = f.readlines()

found_key = False
found_addr = False
new_lines = []

for line in env_lines:
    if line.startswith('TRADING_WALLET_PRIVATE_KEY='):
        new_lines.append(f'TRADING_WALLET_PRIVATE_KEY=0x{acct.key.hex()}\n')
        found_key = True
    elif line.startswith('TRADING_WALLET_ADDRESS='):
        new_lines.append(f'TRADING_WALLET_ADDRESS={acct.address}\n')
        found_addr = True
    else:
        new_lines.append(line)

if not found_key:
    new_lines.append(f'TRADING_WALLET_PRIVATE_KEY=0x{acct.key.hex()}\n')
if not found_addr:
    new_lines.append(f'TRADING_WALLET_ADDRESS={acct.address}\n')

with open('.env', 'w') as f:
    f.writelines(new_lines)

print(f"✅ Nova denarnica ustvarjena!")
print(f"   Naslov: {acct.address}")
PYEOF
fi

# Fix placeholder values
sed -i 's|https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID|https://rpc.ankr.com/eth|g' .env 2>/dev/null || true
sed -i 's|0x0000000000000000000000000000000000000000000000|0x0000000000000000000000000000000000000001|g' .env 2>/dev/null || true

# Use local Erigon if enabled
if [ "$USE_LOCAL_ERIGON" = "true" ]; then
    sed -i 's|ETHEREUM_RPC_URL=.*|ETHEREUM_RPC_URL=http://localhost:8545|g' .env 2>/dev/null || true
fi

# Ensure required variables
if ! grep -q "^ETHEREUM_RPC_URL=" .env; then
    echo "ETHEREUM_RPC_URL=https://rpc.ankr.com/eth" >> .env
fi

echo ""
echo "🚀 Začenjam trading bot..."
echo ""

exec python3 -m src.main
