#!/bin/bash
set -e

cd "$(dirname "$0")"
PROJECT_DIR=$(pwd)

echo "🚀 POWERSAVER - AVTONOMNI TRGOVALNI BOT"
echo "=========================================="

# ============================================
# KORAK 0: Preveri in zaženi Docker
# ============================================
echo "🐳 Preverjam Docker..."

# Preveri če docker API obstaja
if ! docker info >/dev/null 2>&1; then
    echo "   Docker ne teče, poskusim zagnati..."
    
    # Poskusi zagnati dockerd
    sudo dockerd > /tmp/docker.log 2>&1 &
    
    # Čakaj da se Docker zažene
    for i in {1..30}; do
        if docker info >/dev/null 2>&1; then
            echo "   ✅ Docker zagnan!"
            break
        fi
        sleep 1
    done
    
    # Če še ne teče, poskusi brez sudo
    if ! docker info >/dev/null 2>&1; then
        dockerd > /tmp/docker.log 2>&1 &
        sleep 5
    fi
fi

if ! docker info >/dev/null 2>&1; then
    echo "❌ NAPAKA: Docker ne deluje!"
    echo "   Namesti Docker: https://docs.docker.com/get-docker"
    exit 1
fi

echo "✅ Docker teče!"

# ============================================
# KORAK 1: Namesti odvisnosti
# ============================================
echo "📦 Namestam Python odvisnosti..."
pip3 install -q python-dotenv web3 eth-account 2>/dev/null || true
echo "✅ Odvisnosti nameščene"

# ============================================
# KORAK 2: Preveri in zaženi Docker/Erigon
# ============================================
echo ""
echo "🔧 Preverjam Ethereum node (Erigon)..."

# Preveri če Erigon že teče
ERIGON_RUNNING=false
ERIGON_BLOCK="0x0"

if curl -s -X POST -H "Content-Type: application/json" \
   --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
   http://localhost:8545 2>/dev/null | grep -q '"result"'; then
    ERIGON_RUNNING=true
    ERIGON_BLOCK=$(curl -s -X POST -H "Content-Type: application/json" \
       --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
       http://localhost:8545 | grep -o '"result":"[^"]*"' | cut -d'"' -f4)
    echo "✅ Erigon že teče! Block: $ERIGON_BLOCK"
fi

# Če Erigon ne teče, ga zaženi
if [ "$ERIGON_RUNNING" = "false" ]; then
    echo "📥 Začenjam Erigon node (prvi sync traja dlje)..."
    
    # Preveri docker volume
    if ! docker volume ls | grep -q erigon-data; then
        echo "   Ustvarjam Docker volume..."
        docker volume create erigon-data 2>/dev/null || true
    fi
    
    # Zaženi Erigon container
    echo "   Začenjam container..."
    docker rm -f erigon-node 2>/dev/null || true
    
    docker run -d --name erigon-node \
        --restart unless-stopped \
        -p 8545:8545 -p 8546:8546 -p 30303:30303 \
        -v erigon-data:/erigon \
        erigontech/erigon:latest \
        --prune=prune --chain=mainnet \
        --http.vaddr=0.0.0.0:8545 \
        --ws.vaddr=0.0.0.0:8546 \
        --http.api=eth,debug,net,trace,web3 \
        --http.corsdomain="*" \
        --maxpeers=100 \
        --snapshot.algobase="fast" 2>&1 || echo "   ❌ Napaka pri zagonu Erigona"
    
    # Čakaj na sync
    echo ""
    echo "⏳ Čakam na Erigon sync..."
    echo "   (Prvi sync = ~100GB, lahko traja ure/dnevi)"
    echo "   Brez panike - to je normalno!"
    echo ""
    
    SYNCED=false
    LAST_BLOCK="0x0"
    
    for i in $(seq 1 3600); do  # 5 ur max
        sleep 5
        
        RESP=$(curl -s -X POST -H "Content-Type: application/json" \
           --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
           http://localhost:8545 2>/dev/null || echo "")
        
        if echo "$RESP" | grep -q '"result"'; then
            BLOCK=$(echo "$RESP" | grep -o '"result":"[^"]*"' | cut -d'"' -f4)
            
            if [ "$BLOCK" != "0x0" ] && [ -n "$BLOCK" ]; then
                # Pretvori v decimalno za primerjavo
                BLOCK_DEC=$((16#$BLOCK))
                
                if [ $BLOCK_DEC -gt 0 ]; then
                    LAST_BLOCK=$BLOCK
                    SYNCED=true
                    
                    # Show progress every 30 seconds
                    if [ $((i % 6)) -eq 0 ]; then
                        echo "   📊 Block: $BLOCK ($BLOCK_DEC)"
                    fi
                fi
            fi
        fi
        
        # Če je synced več kot 10 checkov zapored, končaj
        if [ "$SYNCED" = "true" ]; then
            break
        fi
    done
    
    if [ "$SYNCED" = "true" ]; then
        echo ""
        echo "✅ Erigon SYNCD! Block: $LAST_BLOCK"
    else
        echo ""
        echo "⚠️  Erigon še ni synced (Block: $LAST_BLOCK)"
        echo "   Nadaljujem z botom - bo deloval ko se sync-a"
    fi
fi

# ============================================
# KORAK 3: Nastavi .env
# ============================================
echo ""
echo "🔐 Nastavljam .env..."

if [ ! -f .env ]; then
    cp .env.example .env
    echo "   Ustvarjen nov .env"
fi

# Vedno uporabi lokalni Erigon RPC
sed -i 's|^ETHEREUM_RPC_URL=.*|ETHEREUM_RPC_URL=http://localhost:8545|g' .env 2>/dev/null || true
if ! grep -q "^ETHEREUM_RPC_URL=" .env; then
    echo "ETHEREUM_RPC_URL=http://localhost:8545" >> .env
fi

# Naloži spremenljivke
source .env 2>/dev/null || true

# ============================================
# KORAK 4: Ustvari denarnico če je potrebno
# ============================================
if [ -z "$TRADING_WALLET_PRIVATE_KEY" ] || [ "$TRADING_WALLET_PRIVATE_KEY" = "" ] || [ "$TRADING_WALLET_PRIVATE_KEY" = "0x0000" ]; then
    echo "💰 Ustvarjam novo denarnico..."
    
    python3 << 'PYEOF'
from eth_account import Account
import os

acct = Account.create()

# Preberi obstoječ .env
env_lines = []
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        env_lines = f.readlines()

# Posodobi ali dodaj
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
print(f"   ⚠️  SHRANI PRIVATE KEY: 0x{acct.key.hex()}")
PYEOF
else
    echo "   ✅ Denarnica že nastavljena"
fi

# ============================================
# KORAK 5: Zaženi bot
# ============================================
echo ""
echo "🚀 Začenjam trading bot..."
echo "=========================================="
echo ""

exec python3 -m src.main
