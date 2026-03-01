#!/bin/bash
set -e
cd "$(dirname "$0")"
pip3 install -q python-dotenv web3 2>/dev/null || true
[ -f .env ] || cp .env.example .env
exec python3 -m src.main
