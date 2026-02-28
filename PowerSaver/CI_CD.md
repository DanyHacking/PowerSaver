# CI/CD Pipeline & Monitoring

## Overview

This document describes the CI/CD pipeline and monitoring infrastructure for the Flash Loan Trading System.

## CI/CD Pipeline

### GitHub Actions Workflows

#### 1. Main CI/CD Pipeline (`.github/workflows/ci-cd.yml`)

The main pipeline runs on every push and pull request:

```yaml
jobs:
  - code-quality: Linting, formatting, type checking
  - testing: Unit and integration tests
  - security: Security scanning
  - build: Package building
  - deploy: Production deployment
  - docker: Docker image build and push
  - notify: Notifications
```

#### 2. Code Quality (`.github/workflows/code-quality.yml`)

Runs automated code quality checks:

- **Linting**: Ruff linter
- **Formatting**: Ruff formatter
- **Type Checking**: Mypy
- **Documentation**: Docstring checks

#### 3. Testing (`.github/workflows/testing.yml`)

Comprehensive testing suite:

- **Unit Tests**: pytest with coverage
- **Integration Tests**: Full system tests
- **Performance Tests**: Benchmarking
- **Multi-Python**: Tests on Python 3.10, 3.11, 3.12

#### 4. Security (`.github/workflows/security.yml`)

Security scanning:

- **Dependency Scanning**: Safety, pip-audit
- **Code Security**: Bandit
- **Secret Detection**: TruffleHog, Gitleaks
- **Docker Security**: Trivy vulnerability scanner
- **Dependency Review**: License and vulnerability checks

### Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    PUSH / PULL REQUEST                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    CODE QUALITY CHECKS                       │
│  - Linting (Ruff)                                           │
│  - Formatting (Ruff)                                        │
│  - Type Checking (Mypy)                                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      TESTING                                 │
│  - Unit Tests (pytest)                                      │
│  - Integration Tests                                        │
│  - Performance Tests                                        │
│  - Coverage Reports                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY SCANNING                         │
│  - Dependency Vulnerabilities                               │
│  - Code Security (Bandit)                                   │
│  - Secret Detection                                         │
│  - Docker Security (Trivy)                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       BUILD                                  │
│  - Package Build                                            │
│  - Package Validation                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     DEPLOYMENT                               │
│  - Docker Image Build & Push                                │
│  - PyPI Upload (if tagged)                                  │
│  - Staging Deployment                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   NOTIFICATION                               │
│  - Success/Failure Alerts                                   │
│  - Dashboard Updates                                        │
└─────────────────────────────────────────────────────────────┘
```

## Deployment

### Deploy Script

The `deploy.sh` script provides automated deployment:

```bash
# Deploy to staging
./deploy.sh staging

# Deploy to production
./deploy.sh production

# Deploy Docker image
./deploy.sh docker

# Full deployment (all environments)
./deploy.sh all
```

### Deployment Environments

#### Staging Environment

- Automated on every push to `develop` branch
- Full test suite required
- Docker image tagged with commit SHA
- Manual approval for production

#### Production Environment

- Automated on every push to `main` branch
- All checks must pass
- Docker image tagged with version
- PyPI upload for tagged releases

### Docker Deployment

```bash
# Build Docker image
docker build -t flash-loan-trader:latest .

# Run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f trading-engine

# Restart services
docker-compose restart

# Stop services
docker-compose down
```

### Environment Variables

All sensitive configuration is managed through environment variables:

```bash
# Blockchain Configuration
BLOCKCHAIN_NETWORK=ethereum
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_PROJECT_ID

# Wallet Configuration
TRADING_WALLET_PRIVATE_KEY=0x...
TRADING_WALLET_ADDRESS=0x...

# API Keys
ETHERSCAN_API_KEY=your_key
COINGECKO_API_KEY=your_key

# Alerting
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
TELEGRAM_BOT_TOKEN=your_token
```

## Monitoring & Observability

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    TRADING ENGINE                           │
│  - Prometheus Metrics Exporter                              │
│  - Health Check Endpoint                                    │
│  - Logging to Logstash                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    LOGSTASH                                  │
│  - Log Collection & Processing                              │
│  - Log Parsing & Enrichment                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    ELASTICSEARCH                             │
│  - Log Storage & Indexing                                   │
│  - Search & Analytics                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    PROMETHEUS                                │
│  - Metrics Collection                                       │
│  - Time-Series Storage                                      │
│  - Alerting Rules                                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    GRAFANA                                   │
│  - Dashboards & Visualization                               │
│  - Alerting & Notifications                                 │
│  - Performance Analytics                                    │
└─────────────────────────────────────────────────────────────┘
```

### Metrics

#### Trading Metrics

- `trades_total`: Total number of trades executed
- `trades_successful_total`: Successful trades count
- `trades_failed_total`: Failed trades count
- `trade_profit_usd`: Trade profit in USD
- `trade_gas_cost_usd`: Gas cost in USD
- `trade_duration_seconds`: Trade execution time

#### System Metrics

- `system_uptime_seconds`: System uptime
- `system_memory_usage_bytes`: Memory usage
- `system_cpu_usage_ratio`: CPU usage ratio
- `system_disk_usage_bytes`: Disk usage
- `system_network_bytes_total`: Network traffic

#### Performance Metrics

- `performance_trade_count`: Trades per time period
- `performance_profit_usd`: Total profit
- `performance_win_rate`: Win rate percentage
- `performance_avg_profit_usd`: Average profit per trade

### Dashboards

#### 1. Trading Performance Dashboard

- Total trades and profit
- Win rate over time
- Strategy performance comparison
- Token pair performance
- Gas cost analysis

#### 2. System Health Dashboard

- System uptime
- Resource usage (CPU, memory, disk)
- Network traffic
- Error rates

#### 3. Alerting Dashboard

- Active alerts
- Alert history
- Alert response times
- System health status

### Alerting

#### Prometheus Alerting Rules

```yaml
groups:
  - name: trading-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(trades_failed_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: High error rate detected
          
      - alert: LowWinRate
        expr: (trades_successful_total / trades_total) < 0.4
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: Win rate below 40%
          
      - alert: HighGasCost
        expr: avg(trade_gas_cost_usd) > 100
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: High gas costs detected
          
      - alert: SystemDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: Trading engine is down
```

#### Alert Channels

- **Discord**: Real-time notifications
- **Email**: Daily summaries
- **Telegram**: Instant alerts
- **PagerDuty**: Critical incidents

### Logging

#### Log Format

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "service": "trading-engine",
  "message": "Trade executed successfully",
  "trade_id": "trade-123",
  "strategy": "arbitrage_v2",
  "profit_usd": 150.50,
  "gas_cost_usd": 25.30,
  "duration_seconds": 12.5
}
```

#### Log Levels

- **DEBUG**: Detailed debugging information
- **INFO**: General operational messages
- **WARNING**: Potential issues
- **ERROR**: Errors that don't stop execution
- **CRITICAL**: Critical errors requiring immediate attention

### Health Checks

#### HTTP Health Endpoint

```bash
# Health check
curl http://localhost:8000/health

# Detailed health
curl http://localhost:8000/health/detailed
```

#### Health Check Response

```json
{
  "status": "healthy",
  "uptime_seconds": 86400,
  "trades_executed": 150,
  "trades_failed": 5,
  "win_rate": 0.967,
  "total_profit_usd": 2500.00,
  "system_resources": {
    "cpu_usage": 0.45,
    "memory_usage": 0.60,
    "disk_usage": 0.30
  },
  "database": {
    "status": "connected",
    "query_time_ms": 5
  },
  "blockchain": {
    "status": "connected",
    "chain_id": 1,
    "block_number": 18900000
  }
}
```

### Database

#### PostgreSQL Setup

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Access database
docker-compose exec postgres psql -U trader -d flash_loan_trader

# Run migrations
docker-compose exec postgres psql -U trader -d flash_loan_trader -f /docker-entrypoint-initdb.d/init.sql
```

#### Database Views

- `daily_performance`: Daily trading statistics
- `strategy_performance`: Strategy comparison
- `token_performance`: Token pair analysis

#### Database Functions

- `archive_old_trades()`: Archive old trades to history
- `get_system_health()`: Get system health status

### Monitoring Stack

#### Components

1. **Prometheus**: Metrics collection and alerting
2. **Grafana**: Visualization and dashboards
3. **Elasticsearch**: Log storage and search
4. **Logstash**: Log processing
5. **PostgreSQL**: Transaction storage
6. **Redis**: Caching and session management

#### Access URLs

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Kibana**: http://localhost:5601
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### Best Practices

#### Monitoring

1. **Set up alerts** for critical metrics
2. **Review dashboards** daily
3. **Archive old data** regularly
4. **Test alerting** channels
5. **Document runbooks** for incidents

#### Security

1. **Never commit** sensitive data
2. **Rotate secrets** regularly
3. **Use HTTPS** for all endpoints
4. **Enable authentication** for dashboards
5. **Monitor access logs**

#### Performance

1. **Optimize queries** regularly
2. **Scale horizontally** when needed
3. **Use caching** for frequently accessed data
4. **Monitor resource usage**
5. **Set up auto-scaling**

## Troubleshooting

### Common Issues

#### Trading Engine Not Starting

```bash
# Check logs
docker-compose logs trading-engine

# Check configuration
docker-compose exec trading-engine python -c "from config_loader import load_config; load_config()"

# Verify environment variables
docker-compose exec trading-engine env | grep TRADING
```

#### Database Connection Issues

```bash
# Check PostgreSQL status
docker-compose ps postgres

# Test connection
docker-compose exec postgres psql -U trader -c "SELECT 1"

# Check logs
docker-compose logs postgres
```

#### High Error Rate

1. Check system health dashboard
2. Review recent alerts
3. Check blockchain RPC endpoints
4. Verify wallet balance
5. Check gas prices

#### Performance Issues

1. Check resource usage in Grafana
2. Review database query performance
3. Check network latency
4. Analyze trade execution times
5. Review gas optimization settings

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)