#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "🚀 POWERSAVER - AVTONOMNI TRGOVALNI BOT"
echo "=========================================="

# Auto-install dependencies
pip3 install -q python-dotenv web3 eth-account 2>/dev/null || true

# Check if Erigon is already running
ERIGON_RUNNING=false
if curl -s -X POST -H "Content-Type: application/json" \
   --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
   http://localhost:8545 >/dev/null 2>&1; then
    ERIGON_RUNNING=true
    echo "✅ Erigon node že teče!"
fi

# Start Erigon if not running
if [ "$ERIGON_RUNNING" = "false" ]; then
    echo "🔧 Začenjam Erigon node..."
    
    # Check if docker-compose erigon service exists
    if docker-compose ps erigon 2>/dev/null | grep -q "Up"; then
        echo "✅ Erigon container že dela"
    else
        # Start Erigon container
        docker-compose up -d erigon || {
            echo "❌ Napaka pri zagonu Erigona"
            echo "   Poskusam z docker run..."
            docker run -d --name erigon-node \
                -p 8545:8545 -p 8546:8546 -p 30303:30303 \
                -v erigon-data:/erigon \
                thorax/erigon:latest \
                --prune=prune --chain=mainnet \
                --http.vaddr=0.0.0.0:8545 \
                --ws.vaddr=0.0.0.0:8546 \
                --http.api=eth,debug,net,trace,web3
        }
    fi
    
    echo "⏳ Čakam da se Erigon sync-a..."
    echo "   (To lahko traja več ur/dni - prvi sync je najdaljši)"
    echo ""
    
    # Wait for Erigon with progress
    SYNCED=false
    for i in {1..3600}; do  # 5 hours max wait
        if curl -s -X POST -H "Content-Type: application/json" \
           --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
           http://localhost:8545 >/dev/null 2>&1; then
            
            # Get current block
            BLOCK=$(curl -s -X POST -H "Content-Type: application/json" \
                --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
                http://localhost:8545 | grep -o '"result":"0x[^"]*"' | cut -d'"' -f4)
            
            if [ -n "$BLOCK" ]; then
                echo "✅ Erigon SYNCD! Block: $BLOCK"
                SYNCED=true
                break
            fi
        fi
        
        if [ $((i % 30)) -eq 0 ]; then
            echo "   Še vedno syncam... ($i/3600)"
        fi
        sleep 10
    done
    
    if [ "$SYNCED" = "false" ]; then
        echo "⚠️  Erigon še ni synced, ampak nadaljujem z zagonom bota..."
        echo "   (Bot bo deloval z javnim RPC dokler se Erigon ne synca)"
    fi
fi

# Ensure .env exists
if [ ! -f .env ]; then
    cp .env.example .env
fi

# Use local Erigon RPC
sed -i 's|ETHEREUM_RPC_URL=.*|ETHEREUM_RPC_URL=http://localhost:8545|g' .env 2>/dev/null || true
if ! grep -q "^ETHEREUM_RPC_URL=" .env; then
    echo "ETHEREUM_RPC_URL=http://localhost:8545" >> .env
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

echo ""
echo "🚀 Začenjam trading bot..."
echo ""

exec python3 -m src.main
