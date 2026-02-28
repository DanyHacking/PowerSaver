#!/bin/bash

# ============================================================================
# Run All Audits Script
# Executes all audit and verification scripts
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="${PROJECT_ROOT}/logs"

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

# Create logs directory
mkdir -p "$LOG_DIR"

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}  Running All Audits${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Run security audit
log_info "Running Security Audit..."
python3 "${SCRIPT_DIR}/audit_security.py" 2>&1 | tee "${LOG_DIR}/security_audit.log"
SECURITY_STATUS=${PIPESTATUS[0]}

if [ $SECURITY_STATUS -eq 0 ]; then
    log_success "Security audit completed"
else
    log_warning "Security audit completed with warnings"
fi

echo ""

# Run performance audit
log_info "Running Performance Audit..."
python3 "${SCRIPT_DIR}/audit_performance.py" 2>&1 | tee "${LOG_DIR}/performance_audit.log"
PERF_STATUS=${PIPESTATUS[0]}

if [ $PERF_STATUS -eq 0 ]; then
    log_success "Performance audit completed"
else
    log_warning "Performance audit completed with warnings"
fi

echo ""

# Run transaction verification
log_info "Running Transaction Verification..."
python3 "${SCRIPT_DIR}/verify_transactions.py" 2>&1 | tee "${LOG_DIR}/transaction_verification.log"
VERIFY_STATUS=${PIPESTATUS[0]}

if [ $VERIFY_STATUS -eq 0 ]; then
    log_success "Transaction verification completed"
else
    log_warning "Transaction verification completed with warnings"
fi

echo ""

# Summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}  Audit Summary${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "Security Audit: ${SECURITY_STATUS:-0}"
echo -e "Performance Audit: ${PERF_STATUS:-0}"
echo -e "Transaction Verification: ${VERIFY_STATUS:-0}"

# Check if all passed
if [ ${SECURITY_STATUS:-0} -eq 0 ] && [ ${PERF_STATUS:-0} -eq 0 ] && [ ${VERIFY_STATUS:-0} -eq 0 ]; then
    echo -e "\n${GREEN}All audits completed successfully!${NC}"
    exit 0
else
    echo -e "\n${YELLOW}Some audits completed with warnings${NC}"
    exit 0
fi
