#!/bin/bash

# ============================================================================
# POWERSAVER - AVTONOMNI TRGOVALNI BOT
# ============================================================================
# Samo poženi in vse se naloži in zažene avtomatsko!
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
        log_error "Manjka .env datoteka!"
        echo ""
        echo "Ustvari .env z naslednjimi podatki:"
        echo ""
        cat .env.example
        echo ""
        exit 1
    fi
    
    # Preveri če so podatki vneseni
    if grep -qE "YOUR_|REPLACE|example" .env 2>/dev/null; then
        log_error ".env ni pravilno nastavljen!"
        echo ""
        echo "Odpri .env in zamenjaj YOUR_... z resničnimi vrednostmi!"
        exit 1
    fi
    
    # Zaženi namestitev in trading
    install_dependencies
    setup_node
    start_trading
}

# ============================================================================
# NAMESTITEV ODVISNOSTI
# ============================================================================

install_dependencies() {
    log_info "1/3 Namestam odvisnosti..."
    
    # Python
    if ! command -v python3 &>/dev/null; then
        log_error "Manjka Python3!"
        exit 1
    fi
    
    # pip
    pip3 install -r requirements.txt -q 2>/dev/null || pip install -r requirements.txt -q 2>/dev/null || true
    
    # Foundry (če še ni)
    if ! command -v forge &>/dev/null; then
        log_info "Namestam Foundry..."
        curl -L https://foundry.paradigm.xyz | bash
        source ~/.bashrc 2>/dev/null || source ~/.zshrc 2>/dev/null
        foundryup 2>/dev/null || true
    fi
    
    log_success "Odvisnosti nameščene"
}

# ============================================================================
# NASTAVITEV NODE-A
# ============================================================================

setup_node() {
    log_info "2/3 Nastavljam Ethereum node..."
    
    # Preveri ali že teče node
    if curl -s -X POST -H "Content-Type: application/json" \
        --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
        http://localhost:8545 2>/dev/null | grep -q result; then
        log_success "Node že teče (localhost:8545)"
        return 0
    fi
    
    # Preveri RPC v .env
    source .env
    
    if [ -n "$ETHEREUM_RPC_URL" ] && [ "$ETHEREUM_RPC_URL" != "http://localhost:8545" ]; then
        log_success "Uporabljam zunanji RPC: ${ETHEREUM_RPC_URL:0:40}..."
        return 0
    fi
    
    # Namesti in zaženi Reth
    log_info "Namestam Reth node (najhitrejši)..."
    
    ARCH=$(uname -m)
    [ "$ARCH" = "x86_64" ] && ARCH="x86_64" || ARCH="aarch64"
    
    cd /tmp
    if curl -fsSL "https://github.com/paradigmxyz/reth/releases/download/v0.2.0/reth-v0.2.0-${ARCH}-unknown-linux-gnu.tar.gz" -o reth.tar.gz; then
        sudo tar -xzf reth.tar.gz -C /usr/local/bin --overwrite 2>/dev/null
        rm reth.tar.gz
        
        if command -v reth &>/dev/null; then
            log_info "Zaženjam Reth (light mode)..."
            mkdir -p ~/.reth
            nohup reth node \
                --chain mainnet \
                --datadir ~/.reth \
                --light \
                --http \
                --http.api eth,net,debug,trace \
                --http.vhosts=* \
                --http.corsdomain=* \
                > ~/.reth.log 2>&1 &
            
            # Čakaj da se zažene
            sleep 5
            
            # Preveri če teče
            if curl -s -X POST -H "Content-Type: application/json" \
                --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
                http://localhost:8545 2>/dev/null | grep -q result; then
                log_success "Reth teče na http://localhost:8545"
            else
                log_warning "Reth se ni zagnal, uporabljam zunanji RPC"
            fi
        fi
    else
        log_warning "Reth ni na voljo, uporabljam zunanji RPC"
    fi
    
    cd "$SCRIPT_DIR"
}

# ============================================================================
# ZAGON TRADINGA
# ============================================================================

start_trading() {
    log_info "3/3 ${GREEN}🚀 ZAŽENAM AVTONOMNEGA BOTA!${NC}"
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                    🤖 BOT TEČE 24/7 🤖                        ║"
    echo "╠══════════════════════════════════════════════════════════════════╣"
    echo "║  - Skenira priložnosti                                        ║"
    echo "║  - Izvršuje posle                                            ║"
    echo "║  - Upravlja tveganja                                         ║"
    echo "║                                                                  ║"
    echo "║  Za zaustavitev pritisni: Ctrl + C                            ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Zaženi
    python3 -m src.main --network mainnet
}

# Zagon
main "$@"
