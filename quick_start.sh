#!/bin/bash
# Quick start script for autonomous trading system

set -e

echo "=== Autonomous Trading System - Quick Start ==="

# Check Python version
python3 --version || { echo "Python 3 required"; exit 1; }

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "Please edit .env with your configuration before running:"
    echo "  - PRIVATE_KEY"
    echo "  - RPC_URL"
    echo "  - LOAN_AMOUNT_USD"
    exit 0
fi

# Validate configuration
echo "Validating configuration..."
python3 -c "from src.config import config; config.validate()"

echo ""
echo "=== Setup Complete ==="
echo "To start trading: python start_trading.py"
echo "To stop trading: Ctrl+C"
echo ""
