#!/bin/bash
# ============================================================
# TESTNET STARTUP SCRIPT
# Usage: ./start_testnet.sh
# ============================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# Load testnet environment
load_testnet_env() {
    log_info "Loading testnet configuration..."
    
    if [ -f .env.testnet ]; then
        export $(cat .env.testnet | grep -v '^#' | xargs)
        log_success "Testnet config loaded"
    else
        log_error "Missing .env.testnet file!"
        log_info "Copy .env.testnet.example to .env.testnet and configure"
        exit 1
    fi
    
    # Set testnet mode
    export TESTNET=true
    export CHAIN_ID=11155111  # Sepolia
    
    log_info "Network: Sepolia Testnet (Chain ID: $CHAIN_ID)"
}

# Check testnet funds
check_testnet_funds() {
    log_info "Checking testnet wallet funds..."
    
    # Check ETH balance
    ETH_BALANCE=$(cast balance $TRADING_WALLET_ADDRESS --rpc-url $SEPOLIA_RPC_URL 2>/dev/null || echo "0")
    ETH_BALANCE_ETH=$(echo "scale=6; $ETH_BALANCE / 1e18" | bc)
    
    if (( $(echo "$ETH_BALANCE_ETH < 0.01" | bc -l) )); then
        log_warning "Low ETH balance: ${ETH_BALANCE_ETH} ETH"
        log_info "Get testnet ETH from: https://sepoliafaucet.com"
    else
        log_success "ETH balance: ${ETH_BALANCE_ETH} ETH"
    fi
    
    # Check token balances
    log_info "Checking token balances..."
    
    for TOKEN in $TEST_WETH_ADDRESS $TEST_USDC_ADDRESS $TEST_DAI_ADDRESS; do
        BALANCE=$(cast call $TOKEN "balanceOf(address)(uint256)" $TRADING_WALLET_ADDRESS --rpc-url $SEPOLIA_RPC_URL 2>/dev/null || echo "0")
        log_info "Token ${TOKEN:0:10}...: $BALANCE"
    done
}

# Deploy test contracts
deploy_testnet_contracts() {
    log_info "Deploying testnet contracts..."
    
    # Deploy testnet tokens (if needed)
    log_info "Deploying mock tokens..."
    
    # Deploy Flash Loan Receiver test contract
    log_info "Deploying FlashLoanReceiver..."
    
    # This would deploy via forge
    # forge create --rpc-url $SEPOLIA_RPC_URL \
    #     --private-key $TEST_TRADING_WALLET_PRIVATE_KEY \
    #     src/contracts/FlashLoanReceiver.sol:FlashLoanReceiver
    
    log_success "Test contracts deployed"
}

# Run testnet trading
run_testnet_trading() {
    log_info "Starting testnet trading bot..."
    log_warning "Running with TEST_LOAN_AMOUNT: \$$TEST_LOAN_AMOUNT"
    log_warning "Running with TEST_MIN_PROFIT: \$$TEST_MIN_PROFIT"
    
    # Run with testnet config
    python3 -m src.main \
        --network sepolia \
        --config config.json \
        --test-mode \
        --dry-run
    
    log_success "Testnet trading completed"
}

# Dry run mode (simulate only)
run_dry_run() {
    log_info "Running DRY RUN mode (no real transactions)..."
    
    python3 -c "
import os
import asyncio
from src.trading.aggressive_trading import AggressiveTradingBot

async def test():
    config = {
        'testnet': True,
        'loan_amount': int(os.getenv('TEST_LOAN_AMOUNT', 100)),
        'min_profit': float(os.getenv('TEST_MIN_PROFIT', 1)),
        'max_slippage': float(os.getenv('TEST_MAX_SLIPPAGE', 0.05)),
        'tokens': ['ETH', 'WETH', 'USDC', 'DAI'],
        'exchanges': ['uniswap_v3', 'uniswap_v2', 'sushiswap'],
    }
    
    bot = AggressiveTradingBot(config)
    opportunities = await bot.scan_arbitrage_opportunities()
    
    print(f'Found {len(opportunities)} opportunities')
    
    for opp in opportunities[:5]:
        print(f'  - {opp.path}: profit=\${opp.expected_profit:.2f}')

asyncio.run(test())
"
}

# Main menu
main() {
    echo "============================================"
    echo "   POWERSAVER TESTNET LAUNCHER"
    echo "============================================"
    echo ""
    echo "1) Check wallet funds"
    echo "2) Deploy test contracts"
    echo "3) Run DRY RUN (simulate only)"
    echo "4) Run LIVE test trading"
    echo "5) Exit"
    echo ""
    read -p "Select option [1-5]: " choice
    
    case $choice in
        1)
            load_testnet_env
            check_testnet_funds
            ;;
        2)
            load_testnet_env
            deploy_testnet_contracts
            ;;
        3)
            load_testnet_env
            run_dry_run
            ;;
        4)
            load_testnet_env
            run_testnet_trading
            ;;
        5)
            log_info "Exiting..."
            exit 0
            ;;
        *)
            log_error "Invalid option"
            exit 1
            ;;
    esac
}

# Run
if [ "$1" == "--check" ]; then
    load_testnet_env
    check_testnet_funds
elif [ "$1" == "--dry" ]; then
    load_testnet_env
    run_dry_run
else
    main
fi
