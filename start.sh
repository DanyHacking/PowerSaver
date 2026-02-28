#!/bin/bash

# ============================================================================
# Autonomous Flash Loan Trading System - Mainnet Production Deployment
# ============================================================================
# REAL mainnet autonomous trading bot - 24/7 production operation
# NO simulations, NO test modes - PURE production trading
# Uses REAL Ethereum mainnet node infrastructure
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
DATA_DIR="${SCRIPT_DIR}/data"
CONFIG_DIR="${SCRIPT_DIR}/config"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

# Cleanup function
cleanup() {
    log_warning "Shutting down trading system..."
    if [ -n "$TRADING_ENGINE_PID" ]; then
        kill $TRADING_ENGINE_PID 2>/dev/null || true
    fi
}

trap cleanup EXIT

# Check prerequisites
check_prerequisites() {
    log_section "Checking Prerequisites"
    
    command -v python3 &>/dev/null || { log_error "python3 required"; exit 1; }
    command -v pip3 &>/dev/null || { log_error "pip3 required"; exit 1; }
    command -v curl &>/dev/null || { log_error "curl required"; exit 1; }
    command -v jq &>/dev/null || { log_error "jq required"; exit 1; }
    
    if command -v forge &>/dev/null; then
        log_success "Foundry (forge) is installed"
    else
        log_warning "Foundry not installed. Installing..."
        curl -L https://foundry.paradigm.xyz | bash
        source "$HOME/.bashrc" || source "$HOME/.zshrc"
        foundryup
    fi
    
    if command -v node &>/dev/null; then
        log_success "Node.js is installed: $(node --version)"
    else
        log_error "Node.js is required but not installed"
        exit 1
    fi
    
    log_info "Installing Python dependencies..."
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt -q
        log_success "Python dependencies installed"
    fi
    
    log_success "All prerequisites met"
}

# Setup directories
setup_directories() {
    log_section "Setting Up Directories"
    
    mkdir -p "$LOG_DIR"
    mkdir -p "$DATA_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "${SCRIPT_DIR}/artifacts"
    
    log_success "Directories created"
}

# Load environment variables
load_environment() {
    log_section "Loading Production Environment"
    
    if [ ! -f "${SCRIPT_DIR}/.env" ]; then
        log_error ".env file required for production. Copy from .env.example"
        exit 1
    fi
    
    export $(grep -v '^#' "${SCRIPT_DIR}/.env" | xargs)
    
    log_success "Production environment loaded"
    log_info "  - Network: ${BLOCKCHAIN_NETWORK:-ethereum}"
    log_info "  - RPC: ${ETHEREUM_RPC_URL:-configured}"
    log_info "  - Trading Wallet: ${TRADING_WALLET_ADDRESS:-configured}"
}

# Verify mainnet connectivity
verify_mainnet_connectivity() {
    log_section "Verifying Mainnet Connectivity"
    
    log_info "Testing RPC connectivity..."
    
    local RPC_URL="${ETHEREUM_RPC_URL}"
    local CHAIN_ID="${CHAIN_ID:-1}"
    
    # Test RPC endpoint
    local response=$(curl -s -X POST -H "Content-Type: application/json" \
        --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
        "$RPC_URL" 2>/dev/null)
    
    if [ -z "$response" ]; then
        log_error "RPC endpoint not responding"
        exit 1
    fi
    
    local block_number=$(echo "$response" | jq -r '.result' 2>/dev/null)
    
    if [ -z "$block_number" ] || [ "$block_number" = "null" ]; then
        log_error "Failed to get block number from RPC"
        exit 1
    fi
    
    log_success "Connected to mainnet block: $block_number"
    log_info "Chain ID: $CHAIN_ID"
    
    # Verify wallet balance
    if [ -n "$TRADING_WALLET_ADDRESS" ]; then
        local balance=$(curl -s -X POST -H "Content-Type: application/json" \
            --data "{\"jsonrpc\":\"2.0\",\"method\":\"eth_getBalance\",\"params\":[\"$TRADING_WALLET_ADDRESS\",\"latest\"],\"id\":1}" \
            "$RPC_URL" 2>/dev/null | jq -r '.result' 2>/dev/null)
        
        if [ -n "$balance" ] && [ "$balance" != "null" ]; then
            local balance_eth=$(echo "scale=4; $balance / 1000000000000000000" | bc 2>/dev/null || echo "0")
            log_success "Trading wallet balance: ${balance_eth} ETH"
        fi
    fi
}

# Deploy smart contracts to mainnet
deploy_contracts() {
    log_section "Deploying Smart Contracts to Mainnet"
    
    log_info "Installing contract dependencies..."
    cd "${SCRIPT_DIR}/contracts"
    npm install --silent
    
    log_info "Compiling contracts..."
    forge compile --silent
    
    log_info "Deploying FlashLoanExecutor to mainnet..."
    
    local DEPLOYER_KEY="${TRADING_WALLET_PRIVATE_KEY}"
    
    if [ -z "$DEPLOYER_KEY" ]; then
        log_error "TRADING_WALLET_PRIVATE_KEY not configured"
        exit 1
    fi
    
    # Deploy with proper mainnet settings
    forge create --rpc-url "${ETHEREUM_RPC_URL}" \
        --private-key "$DEPLOYER_KEY" \
        --constructor-args \
        $(echo "${AAVE_V3_POOL_ADDRESS:-0x87870Bca3FfcfD8cDBd647aD42c42b892F4Ad587}" | xargs) \
        ./src/FlashLoanExecutor.sol:FlashLoanExecutor \
        --broadcast --legacy \
        > "${LOG_DIR}/deployment.log" 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "Contracts deployed to mainnet"
    else
        log_error "Contract deployment failed"
        cat "${LOG_DIR}/deployment.log"
        exit 1
    fi
    
    cd "${SCRIPT_DIR}"
}

# Configure trading engine for production
configure_trading_engine() {
    log_section "Configuring Production Trading Engine"
    
    cat > "${CONFIG_DIR}/trading_config.json" << CONFIG_EOF
{
    "blockchain": {
        "network": "${BLOCKCHAIN_NETWORK:-ethereum}",
        "rpc_url": "${ETHEREUM_RPC_URL}",
        "chain_id": ${CHAIN_ID:-1},
        "confirmations": 1,
        "gas_price_gwei": ${GAS_PRICE_GWEI:-30},
        "max_gas_price_gwei": ${MAX_GAS_PRICE_GWEI:-150}
    },
    "trading": {
        "loan_amount_usd": ${LOAN_AMOUNT_USD:-75000},
        "max_loan_amount_usd": ${MAX_LOAN_AMOUNT_USD:-750000},
        "max_position_size_usd": ${MAX_POSITION_SIZE_USD:-375000},
        "min_profit_threshold_usd": ${MIN_PROFIT_THRESHOLD_USD:-200},
        "max_concurrent_trades": ${MAX_CONCURRENT_TRADES:-15},
        "strategy": "${TRADING_STRATEGY:-aggressive}",
        "test_mode": false,
        "simulate_trades": false,
        "auto_execute": true,
        "trading_enabled": true,
        "scan_interval_seconds": 1,
        "max_daily_trades": 100
    },
    "risk_management": {
        "max_daily_loss_usd": ${MAX_DAILY_LOSS_USD:-75000},
        "max_loss_per_trade_usd": ${MAX_LOSS_PER_TRADE_USD:-1000},
        "stop_loss_percentage": ${STOP_LOSS_PERCENTAGE:-3},
        "take_profit_percentage": ${TAKE_PROFIT_PERCENTAGE:-10},
        "max_drawdown_percentage": ${MAX_DRAWDOWN_PERCENTAGE:-15},
        "max_daily_trades": ${MAX_DAILY_TRADES:-100},
        "cooldown_period_seconds": ${COOLDOWN_PERIOD_SECONDS:-60}
    },
    "mev": {
        "enabled": true,
        "private_transactions": true,
        "bundle_submission": true,
        "use_flashbots": true,
        "liquidations_enabled": true,
        "sandwich_enabled": true,
        "min_liquidation_reward": 50,
        "max_gas_price": 150
    },
    "monitoring": {
        "health_check_interval_seconds": 30,
        "metrics_collection_interval_seconds": 60,
        "alert_thresholds": {
            "cpu_percent": 80,
            "memory_percent": 85,
            "disk_percent": 90
        }
    },
    "flash_loans": {
        "provider": "${FLASH_LOAN_PROVIDER:-aave_v3}",
        "pool_address": "${AAVE_V3_POOL_ADDRESS}",
        "max_loan_duration_seconds": 120,
        "retry_attempts": 5,
        "retry_delay_seconds": 2
    },
    "wallet": {
        "address": "${TRADING_WALLET_ADDRESS}",
        "network": "${BLOCKCHAIN_NETWORK}"
    }
}
CONFIG_EOF
    
    log_success "Trading engine configured for PRODUCTION"
}

# Start trading engine
start_trading_engine() {
    log_section "Starting Production Trading Engine"
    
    log_info "Starting autonomous trading bot..."
    
    cd "${SCRIPT_DIR}"
    
    python3 src/main.py \
        --config "${CONFIG_DIR}/trading_config.json" \
        --log-dir "${LOG_DIR}" \
        --data-dir "${DATA_DIR}" \
        > "${LOG_DIR}/trading_engine.log" 2>&1 &
    
    TRADING_ENGINE_PID=$!
    echo $TRADING_ENGINE_PID > "${DATA_DIR}/trading_engine.pid"
    
    log_success "Trading engine started (PID: $TRADING_ENGINE_PID)"
    log_info "Waiting for engine to initialize..."
    
    sleep 5
    
    if kill -0 $TRADING_ENGINE_PID 2>/dev/null; then
        log_success "Trading engine is running"
    else
        log_error "Trading engine failed to start"
        cat "${LOG_DIR}/trading_engine.log"
        exit 1
    fi
}

# Generate deployment report
generate_report() {
    log_section "Generating Deployment Report"
    
    local report_file="${LOG_DIR}/deployment_report_$(date +%Y%m%d_%H%M%S).md"
    
    cat > "$report_file" << REPORT_EOF
# Production Deployment Report
## Timestamp
$(date '+%Y-%m-%d %H:%M:%S')

## Environment
- **Network**: Mainnet (${BLOCKCHAIN_NETWORK:-ethereum})
- **RPC URL**: ${ETHEREUM_RPC_URL}
- **Chain ID**: ${CHAIN_ID:-1}
- **Script Directory**: ${SCRIPT_DIR}

## Trading Configuration
- **Loan Amount**: ${LOAN_AMOUNT_USD:-10000} USD
- **Max Loan**: ${MAX_LOAN_AMOUNT_USD:-100000} USD
- **Strategy**: ${TRADING_STRATEGY:-balanced}
- **Test Mode**: DISABLED (Production)
- **Auto Execute**: ENABLED

## System Status
- **Trading Engine**: Running (PID: ${TRADING_ENGINE_PID})
- **Trading Enabled**: YES
- **Flash Loans**: ACTIVE

## Configuration Files
- **Trading Config**: ${CONFIG_DIR}/trading_config.json
- **Wallet**: ${TRADING_WALLET_ADDRESS}

## Logs
- Trading Engine: ${LOG_DIR}/trading_engine.log
- Deployment: ${LOG_DIR}/deployment.log

## Next Steps
1. Monitor system health continuously
2. Review trading logs regularly
3. Check transaction history on mainnet
4. Analyze performance metrics
5. Monitor gas prices for optimal execution

REPORT_EOF
    
    log_success "Report generated: $report_file"
    cat "$report_file"
}

# Main execution
main() {
    log_section "Autonomous Flash Loan Trading System - Mainnet Production"
    
    log_info "Starting production deployment..."
    log_info "Working directory: ${SCRIPT_DIR}"
    
    # Execute deployment steps
    check_prerequisites
    setup_directories
    load_environment
    verify_mainnet_connectivity
    deploy_contracts
    configure_trading_engine
    start_trading_engine
    generate_report
    
    log_section "Production Deployment Complete!"
    
    log_success "System is now running on MAINNET!"
    log_info "Network: ${BLOCKCHAIN_NETWORK:-ethereum}"
    log_info "Trading Engine: PID ${TRADING_ENGINE_PID}"
    log_info "Logs: ${LOG_DIR}"
    log_info "Data: ${DATA_DIR}"
    log_info "Config: ${CONFIG_DIR}"
    
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}To monitor the system, run:${NC}"
    echo -e "${YELLOW}  tail -f ${LOG_DIR}/trading_engine.log${NC}"
    echo -e "${GREEN}To stop the system, run:${NC}"
    echo -e "${YELLOW}  ./stop.sh${NC}"
    echo -e "${GREEN}========================================${NC}\n"
    
    log_info "System running. Press Ctrl+C to stop."
    wait
}

# Run main function
main "$@"
