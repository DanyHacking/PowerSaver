#!/bin/bash

# ============================================================================
# POWERSAVER - AVTONOMNI TRGOVALNI BOT
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[X]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ============================================================================
# GLAVNI PROGRAM
# ============================================================================

main() {
    clear
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║           🚀 POWERSAVER - AVTONOMNI TRGOVALNI BOT 🚀          ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
    
    # Preveri .env
    if [ ! -f .env ]; then
        log_error "Manjka .env!"
        cp .env.example .env
        log_success "Ustvaril sem .env - UREDI GA ZDaj!"
        echo ""
        echo "Odpri .env in vnesi svoje podatke, nato zaženi ./start.sh"
        exit 1
    fi
    
    log_success "Konfiguracija najdena"
    
    # Zaženi
    install_dependencies
    setup_node
    start_trading
}

# ============================================================================
# NAMESTITEV ODVISNOSTI
# ============================================================================

install_dependencies() {
    log_info "1/3 Namestam odvisnosti..."
    
    pip3 install -r requirements.txt -q 2>/dev/null || pip install -r requirements.txt -q 2>/dev/null || true
    
    if ! command -v forge &>/dev/null; then
        log_info "Namestam Foundry..."
        curl -L https://foundry.paradigm.xyz | bash
        source ~/.bashrc 2>/dev/null || source ~/.zshrc 2>/dev/null
        foundryup 2>/dev/null || true
    fi
    
    log_success "Odvisnosti nameščene"
}

# ============================================================================
# NODE
# ============================================================================

setup_node() {
    log_info "2/3 Nastavljam Ethereum node..."
    
    # Preveri če že teče
    if curl -s -X POST -H "Content-Type: application/json" \
        --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
        http://localhost:8545 2>/dev/null | grep -q result; then
        log_success "Node že teče"
        return 0
    fi
    
    log_info "Uporabljam zunanji RPC"
}

# ============================================================================
# ZAGON
# ============================================================================

start_trading() {
    log_info "3/3 🚀 ZAŽENAM BOTA!"
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                    🤖 BOT TEČE 24/7 🤖                        ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
    
    python3 -m src.main --network mainnet
}

main "$@"
