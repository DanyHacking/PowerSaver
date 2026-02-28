# Production Trading System Guide

## Overview

This is a **production-ready autonomous flash loan trading system** for mainnet operation.

**CRITICAL**: This is a REAL trading bot for MAINNET - NO simulations, NO test modes.

## Quick Start

### Production Deployment

```bash
# Configure environment variables
cp .env.example .env
# Edit .env with your production credentials

# Deploy and start trading bot
./start.sh
```

### Monitoring

```bash
# Monitor trading logs
tail -f logs/trading_engine.log

# Check system status
python3 scripts/verify_transactions.py

# View deployment report
cat logs/deployment_report_*.md
```

### Stop Trading

```bash
# Stop the trading bot
./stop.sh
```

## System Architecture

### Production Configuration

The system is configured for **mainnet production trading**:

- **Network**: Ethereum Mainnet (or configured network)
- **Test Mode**: DISABLED
- **Simulation**: DISABLED
- **Auto Execute**: ENABLED
- **Trading**: ACTIVE 24/7

### Key Components

1. **Smart Contracts**
   - FlashLoanExecutor.sol
   - Deployed to mainnet via Foundry

2. **Trading Engine**
   - Autonomous 24/7 operation
   - Real-time arbitrage detection
   - Flash loan execution
   - Risk management

3. **Risk Management**
   - Daily loss limits
   - Stop-loss triggers
   - Position size limits
   - Drawdown protection

## Configuration

### Environment Variables (.env)

```bash
# Blockchain Configuration
BLOCKCHAIN_NETWORK=ethereum
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_KEY
CHAIN_ID=1

# Wallet Configuration
DEPLOYER_PRIVATE_KEY=0x...
TRADING_WALLET_ADDRESS=0x...

# Trading Configuration
LOAN_AMOUNT_USD=10000
MAX_LOAN_AMOUNT_USD=100000
TRADING_STRATEGY=balanced

# Risk Management
MAX_DAILY_LOSS_USD=10000
STOP_LOSS_PERCENTAGE=5
TAKE_PROFIT_PERCENTAGE=10

# Flash Loans
FLASH_LOAN_PROVIDER=aave_v3
AAVE_V3_POOL_ADDRESS=0x87870Bca3FfcfD8cDBd647aD42c42b892F4Ad587
```

### Trading Configuration (trading_config.json)

Auto-generated on deployment with production settings:

```json
{
    "trading": {
        "test_mode": false,
        "simulate_trades": false,
        "auto_execute": true,
        "trading_enabled": true
    },
    "risk_management": {
        "max_daily_loss_usd": 10000,
        "stop_loss_percentage": 5,
        "take_profit_percentage": 10
    }
}
```

## Production Operations

### Daily Operations

1. **Monitor System Health**
   ```bash
   ./scripts/verify_transactions.py
   ```

2. **Review Trading Logs**
   ```bash
   tail -f logs/trading_engine.log
   ```

3. **Check Performance Metrics**
   ```bash
   python3 scripts/audit_performance.py
   ```

### Security Audits

```bash
# Run security audit
python3 scripts/audit_security.py

# Run performance audit
python3 scripts/audit_performance.py

# Run all audits
./scripts/run_all_audits.sh
```

### Transaction Verification

```bash
# Verify mainnet transactions
python3 scripts/verify_transactions.py
```

## Risk Management

### Loss Limits

- **Max Daily Loss**: Configurable (default: $10,000)
- **Max Loss Per Trade**: Configurable (default: $1,000)
- **Max Drawdown**: 15%

### Stop Loss & Take Profit

- **Stop Loss**: 5% below entry
- **Take Profit**: 10% above entry
- **Auto-Execute**: Enabled

### Position Limits

- **Max Position Size**: $50,000
- **Max Concurrent Trades**: 3
- **Max Daily Trades**: 50

## Monitoring

### System Health

- CPU usage monitoring
- Memory usage monitoring
- Disk space monitoring
- Network connectivity

### Trading Metrics

- Profit/loss tracking
- Trade execution times
- Gas costs
- Success rates

### Alerts

- Loss threshold breaches
- System errors
- Network issues
- Gas price spikes

## Logs

### Log Files

- `logs/trading_engine.log`: Main trading logs
- `logs/deployment.log`: Deployment logs
- `logs/security_audit.log`: Security audit results
- `logs/performance_audit.log`: Performance metrics

### Log Analysis

```bash
# View recent errors
grep -i "error" logs/trading_engine.log | tail -20

# Count trades
grep -c "Trade executed" logs/trading_engine.log

# Check profit/loss
grep "P/L" logs/trading_engine.log
```

## Troubleshooting

### Trading Engine Not Starting

```bash
# Check logs
cat logs/trading_engine.log

# Verify environment
cat .env

# Restart
./stop.sh && ./start.sh
```

### Transaction Failures

```bash
# Check gas prices
python3 scripts/verify_transactions.py

# Adjust gas settings in .env
MAX_GAS_PRICE_GWEI=100
```

### System Errors

```bash
# Check system health
python3 scripts/audit_performance.py

# Review security audit
python3 scripts/audit_security.py
```

## Production Best Practices

### Security

1. **Never commit private keys**
2. **Use hardware wallets for large amounts**
3. **Regular security audits**
4. **Monitor for unusual activity**

### Risk Management

1. **Start with small amounts**
2. **Monitor performance closely**
3. **Adjust limits based on results**
4. **Have manual override capability**

### Operations

1. **Monitor 24/7**
2. **Regular backups**
3. **Version control**
4. **Document changes**

## Deployment Checklist

- [ ] Environment variables configured
- [ ] Private keys secured
- [ ] Smart contracts deployed
- [ ] Trading configuration set
- [ ] Risk limits defined
- [ ] Monitoring configured
- [ ] Backup procedures in place
- [ ] Emergency stop tested

## Support

For production issues:

1. Check logs in `logs/` directory
2. Review deployment report
3. Run verification scripts
4. Contact support team

## License

This production trading system is part of the Autonomous Flash Loan Trading System.
