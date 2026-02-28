#!/bin/bash
# Minimal deployment script for smart contract

set -e

echo "=== Autonomous Trading System Deployment ==="

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Please edit .env with your configuration"
    exit 1
fi

# Load environment variables
source .env

# Check required variables
if [ -z "$PRIVATE_KEY" ]; then
    echo "ERROR: PRIVATE_KEY not set in .env"
    exit 1
fi

if [ -z "$RPC_URL" ] || [[ "$RPC_URL" == *"YOUR_INFURA"* ]]; then
    echo "ERROR: RPC_URL not configured properly"
    exit 1
fi

echo "Installing Foundry..."
curl -L https://foundry.paradigm.xyz | bash
source ~/.bashrc
foundryup

echo "Building smart contracts..."
forge build

echo "Deploying to Ethereum Mainnet..."
forge script script/Deploy.s.sol \
    --rpc-url "$RPC_URL" \
    --private-key "$PRIVATE_KEY" \
    --broadcast \
    --verify

echo "Deployment complete!"
echo "Contract address will be shown in the deployment logs"
