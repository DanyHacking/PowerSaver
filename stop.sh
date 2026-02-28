#!/bin/bash

# ============================================================================
# Stop Script - Stop the Autonomous Flash Loan Trading System
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"

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

# Stop processes
stop_processes() {
    log_info "Stopping running processes..."
    
    # Stop trading engine
    if pgrep -f "python3 src/main.py" > /dev/null; then
        TRADING_PID=$(pgrep -f "python3 src/main.py")
        log_info "Stopping trading engine (PID: $TRADING_PID)..."
        kill $TRADING_PID 2>/dev/null || true
        log_success "Trading engine stopped"
    else
        log_info "Trading engine not running"
    fi
    
    # Stop anvil/local node
    if pgrep -f "anvil" > /dev/null; then
        ANVIL_PID=$(pgrep -f "anvil")
        log_info "Stopping local node (PID: $ANVIL_PID)..."
        kill $ANVIL_PID 2>/dev/null || true
        log_success "Local node stopped"
    else
        log_info "Local node not running"
    fi
    
    sleep 2
}

# Generate shutdown report
generate_shutdown_report() {
    log_info "Generating shutdown report..."
    
    local report_file="${LOG_DIR}/shutdown_report_$(date +%Y%m%d_%H%M%S).md"
    
    cat > "$report_file" << REPORT_EOF
# Shutdown Report

## Timestamp
$(date '+%Y-%m-%d %H:%M:%S')

## System Status
- Trading Engine: Stopped
- Local Node: Stopped

## Session Summary
- Start Time: $(cat "${LOG_DIR}/deployment_report_*.md" 2>/dev/null | grep "Timestamp" | tail -1 || echo "Unknown")
- End Time: $(date '+%Y-%m-%d %H:%M:%S')

## Logs
- Trading Engine: ${LOG_DIR}/trading_engine.log
- E2E Tests: ${LOG_DIR}/e2e_tests.log
- Deployment: ${LOG_DIR}/deployment.log

## Next Steps
1. Review logs for any errors
2. Check transaction history
3. Analyze performance metrics
4. Restart with ./start.sh when ready

REPORT_EOF
    
    log_success "Shutdown report: $report_file"
    cat "$report_file"
}

# Main execution
main() {
    log_section "Stopping Autonomous Flash Loan Trading System"
    
    log_info "Stopping all services..."
    
    stop_processes
    generate_shutdown_report
    
    log_success "All services stopped"
    log_info "System shutdown complete"
    
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}To restart the system, run:${NC}"
    echo -e "${YELLOW}  ./start.sh${NC}"
    echo -e "${GREEN}========================================${NC}\n"
}

log_section() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

# Run main function
main "$@"
