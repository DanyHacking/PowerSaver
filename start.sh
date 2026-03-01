#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "🚀 POWERSAVER - AVTONOMNI TRGOVALNI BOT"
echo "=========================================="

# Auto-install dependencies
pip3 install -q python-dotenv web3 eth-account 2>/dev/null || true

# Ensure .env exists
if [ ! -f .env ]; then
    cp .env.example .env
fi

# Load existing or generate wallet
source .env 2>/dev/null || true

# Generate wallet if not configured
if [ -z "$TRADING_WALLET_PRIVATE_KEY" ] || [ "$TRADING_WALLET_PRIVATE_KEY" == "0x0000" ]; then
    echo "📋 Ustvarjam novo denarnico..."
    python3 << 'PYEOF'
from eth_account import Account
import secrets

# Generate mnemonic
mnemonic = ' '.join([secrets.choice("abcdefghijklmnopqrstuvwxyz") + ''.join(secrets.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(11)) for _ in range(12)])
# Actually use proper bip39
from bip39 import mnemonic_to_seed
import hashlib

# Simple 12-word mnemonic
words = open("/usr/share/dict/words").read().splitlines() if __name__ == "__main__" else None

# Use eth_account's built-in
acct = Account.create()
print(f"PRIVATE_KEY={acct.key.hex()}")
print(f"WALLET_ADDRESS={acct.address}")
PYEOF
    
    # Save to .env
    python3 << 'PYEOF'
from eth_account import Account
import os

# Generate new wallet
acct = Account.create()

# Read existing .env
env_lines = []
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        env_lines = f.readlines()

# Update or add keys
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
print(f"   Shrani si MNEMONIC ali PRIVATE KEY!")
PYEOF
fi

# Fix placeholder values
sed -i 's|https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID|https://rpc.ankr.com/eth|g' .env 2>/dev/null || true
sed -i 's|0x0000000000000000000000000000000000000000000000000000000000000000|0x0000000000000000000000000000000000000001|g' .env 2>/dev/null || true

# Ensure required variables
if ! grep -q "^ETHEREUM_RPC_URL=" .env; then
    echo "ETHEREUM_RPC_URL=https://rpc.ankr.com/eth" >> .env
fi

echo ""
echo "🚀 Začenjam trading bot..."
echo ""

# Run the bot
exec python3 -m src.main
