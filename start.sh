#!/bin/bash

# ═══════════════════════════════════════════════════════════════════
#  POWERSAVER SMART START
#  Production Bootstrap & System Validation
# ═══════════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║        🚀 POWERSAVER SMART START v2.0                 ║"
echo "║        Production Bootstrap & System Validation        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# PHASE SELECTION
echo -e "\n${YELLOW}📋 SELECT ENVIRONMENT:${NC}"
echo "1) Testnet (Sepolia)"
echo "2) Mainnet"
echo -n "Choice [1-2]: "
read -r ENV_CHOICE

case $ENV_CHOICE in
    1) NETWORK="sepolia"; CHAIN_ID=11155111; echo -e "${GREEN}✓ Testnet mode${NC}" ;;
    2) NETWORK="mainnet"; CHAIN_ID=1; echo -e "${GREEN}✓ Mainnet mode${NC}" ;;
    *) echo -e "${RED}✗ Invalid${NC}"; exit 1 ;;
esac

# REQUIRED VARIABLES
echo -e "\n${YELLOW}🔑 CONFIGURATION INPUT${NC}"

echo -n "PRIVATE KEY (0x...): "
read -r PRIVATE_KEY
[ -z "$PRIVATE_KEY" ] && echo -e "${RED}✗ Private key required${NC}" && exit 1
export PRIVATE_KEY

echo -n "ETHEREUM RPC URL: "
read -r ETHEREUM_RPC
[ -z "$ETHEREUM_RPC" ] && echo -e "${RED}✗ RPC required${NC}" && exit 1
export ETHEREUM_RPC

echo -n "ARBITRUM RPC (optional): "
read -r ARBITRUM_RPC
[ -n "$ARBITRUM_RPC" ] && export ARBITRUM_RPC

echo -n "OPTIMISM RPC (optional): "
read -r OPTIMISM_RPC
[ -n "$OPTIMISM_RPC" ] && export OPTIMISM_RPC

# PHASE 1: SYSTEM CHECKS
echo -e "\n${YELLOW}🔍 PHASE 1: SYSTEM VALIDATION${NC}"
echo -n "Python... "
python3 --version >/dev/null 2>&1 && echo -e "${GREEN}✓${NC}" || { echo -e "${RED}✗${NC}"; exit 1; }

echo -n "Dependencies... "
pip3 install web3 aiohttp eth-account numpy -q 2>/dev/null
echo -e "${GREEN}✓${NC}"

# PHASE 2: RPC VALIDATION
echo -e "\n${YELLOW}🌐 PHASE 2: RPC VALIDATION${NC}"
echo -n "Ethereum RPC... "
ETH_BLOCK=$(curl -s -X POST "$ETHEREUM_RPC" -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' | python3 -c "import sys,json; print(int(json.load(sys.stdin)['result'], 16))" 2>/dev/null) || ETH_BLOCK=0
[ "$ETH_BLOCK" -gt 0 ] && echo -e "${GREEN}✓ Block: $ETH_BLOCK${NC}" || { echo -e "${RED}✗ Failed${NC}"; exit 1; }

echo -n "RPC Latency... "
START=$(date +%s%N)
curl -s -X POST "$ETHEREUM_RPC" -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' >/dev/null
LATENCY=$(( ($(date +%s%N) - START) / 1000000 ))
[ $LATENCY -lt 500 ] && echo -e "${GREEN}✓ ${LATENCY}ms${NC}" || { [ $LATENCY -lt 1000 ] && echo -e "${YELLOW}⚠ ${LATENCY}ms${NC}" || echo -e "${RED}✗ ${LATENCY}ms (slow)${NC}"; }

# PHASE 3: WALLET
echo -e "\n${YELLOW}💰 PHASE 3: WALLET VALIDATION${NC}"
WALLET_ADDRESS=$(python3 -c "from eth_account import Account; print(Account.from_key('$PRIVATE_KEY').address)")
echo "Wallet: $WALLET_ADDRESS"

ETH_BALANCE=$(curl -s -X POST "$ETHEREUM_RPC" -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_getBalance\",\"params\":[\"$WALLET_ADDRESS\",\"latest\"],\"id\":1}" \
    | python3 -c "import sys,json; print(int(json.load(sys.stdin)['result'], 16)/1e18)" 2>/dev/null) || ETH_BALANCE=0

echo -e "Balance: ${GREEN}$ETH_BALANCE ETH${NC}"

# PHASE 4: ANVIL FORK
echo -e "\n${YELLOW}⚙️ PHASE 4: FORK SETUP${NC}"
echo -n "Start Anvil fork? (y/n): "
read -r ANVIL_CHOICE

if [ "$ANVIL_CHOICE" = "y" ] || [ "$ANVIL_CHOICE" = "Y" ]; then
    if command -v anvil &>/dev/null; then
        echo -n "Starting Anvil... "
        pkill -f anvil 2>/dev/null || true
        sleep 1
        anvil --fork-url "$ETHEREUM_RPC" --port 8545 --chain-id $CHAIN_ID &
        sleep 3
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${YELLOW}⚠ Anvil not found (install Foundry)${NC}"
    fi
fi

# PHASE 5: CONFIG
echo -e "\n${YELLOW}📝 PHASE 5: CONFIG GENERATION${NC}"

cat > .env << EOF
NETWORK=$NETWORK
CHAIN_ID=$CHAIN_ID
PRIVATE_KEY=$PRIVATE_KEY
ETHEREUM_RPC=$ETHEREUM_RPC
$( [ -n "$ARBITRUM_RPC" ] && echo "ARBITRUM_RPC=$ARBITRUM_RPC" )
$( [ -n "$OPTIMISM_RPC" ] && echo "OPTIMISM_RPC=$OPTIMISM_RPC" )
INITIAL_CAPITAL=10000
MIN_PROFIT=50
MAX_GAS=100
SCAN_INTERVAL=5
MAX_POSITION=50000
MAX_DAILY_LOSS=5000
MAX_CONCURRENT_TRADES=3
TEST_MODE=false
EOF

echo -e "${GREEN}✓ Config saved to .env${NC}"

# PHASE 6: MODULE VALIDATION
echo -e "\n${YELLOW}✅ PHASE 6: MODULE VALIDATION${NC}"
python3 -c "
import sys; sys.path.insert(0, '.')
from src.utils.local_simulation import LocalSimulationEngine
from src.utils.private_routing import FlashbotsRelay
from src.utils.profit_verification import ProfitVerifier
from src.utils.gas_strategist import GasStrategist
from src.utils.opportunity_scoring import OpportunityScorer
print('OK')
" 2>/dev/null && echo -e "${GREEN}✓ All modules OK${NC}" || { echo -e "${RED}✗ Module error${NC}"; exit 1; }

# FINAL
echo -e "\n${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              🎉 SYSTEM READY 🎉                        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"

echo -e "Network: ${GREEN}$NETWORK${NC}"
echo -e "Wallet: ${GREEN}$WALLET_ADDRESS${NC}"
echo -e "Balance: ${GREEN}$ETH_BALANCE ETH${NC}"
echo -e "RPC Latency: ${GREEN}$LATENCY ms${NC}"
echo ""
echo -e "${YELLOW}Next: python3 -m src.ultimate_trading${NC}"
echo ""
echo -e "${RED}⚠️  WARNING: Real trading = significant risk!${NC}"
echo ""
echo -n "Start now? (y/n): "
read -r START_CHOICE
[ "$START_CHOICE" = "y" ] && python3 -m src.ultimate_trading || echo "Ready. Run manually when ready."
