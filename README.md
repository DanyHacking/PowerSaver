# Autonomous Trading System

Minimal configuration for autonomous arbitrage trading with flash loans.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Run Trading Engine
```bash
python start_trading.py
```

## Minimal Configuration

Required environment variables:
- `PRIVATE_KEY` - Your Ethereum private key
- `RPC_URL` - Infura/Alchemy RPC URL
- `LOAN_AMOUNT_USD` - Starting loan amount (default: 10000)
- `MIN_PROFIT_THRESHOLD_USD` - Minimum profit to execute (default: 500)

## Smart Contract Deployment

```bash
# Install Foundry
curl -L https://foundry.paradigm.xyz | bash
source ~/.bashrc
foundryup

# Build and deploy
forge build
forge script script/Deploy.s.sol --rpc-url $RPC_URL --private-key $PRIVATE_KEY
```

## Emergency Controls

- Pause trading: Set `EMERGENCY_PAUSE=true` in .env
- Stop trading: Press Ctrl+C
- Emergency stop: System auto-stops on critical errors

## Monitoring

Check trading stats:
```python
from trading.complete_trading_engine import CompleteAutonomousTradingEngine
engine = CompleteAutonomousTradingEngine({...})
stats = engine.get_stats()
print(stats)
```

## Security

- Never commit .env file
- Use hardware wallet for large amounts
- Start with small amounts ($100-500)
- Regular security audits recommended
