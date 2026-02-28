-- Flash Loan Trading System - Database Initialization
-- PostgreSQL 15

-- Create database
CREATE DATABASE flash_loan_trader;

\c flash_loan_trader;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create tables
CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trade_id VARCHAR(50) UNIQUE NOT NULL,
    strategy VARCHAR(50) NOT NULL,
    token_in VARCHAR(20) NOT NULL,
    token_out VARCHAR(20) NOT NULL,
    amount_in NUMERIC(36, 18) NOT NULL,
    amount_out NUMERIC(36, 18) NOT NULL,
    profit_usd NUMERIC(18, 2) NOT NULL,
    gas_cost_eth NUMERIC(18, 18) NOT NULL,
    gas_cost_usd NUMERIC(18, 2) NOT NULL,
    transaction_hash VARCHAR(66),
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS trades_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trade_id VARCHAR(50) NOT NULL,
    strategy VARCHAR(50) NOT NULL,
    token_in VARCHAR(20) NOT NULL,
    token_out VARCHAR(20) NOT NULL,
    amount_in NUMERIC(36, 18) NOT NULL,
    amount_out NUMERIC(36, 18) NOT NULL,
    profit_usd NUMERIC(18, 2) NOT NULL,
    gas_cost_eth NUMERIC(18, 18) NOT NULL,
    gas_cost_usd NUMERIC(18, 2) NOT NULL,
    transaction_hash VARCHAR(66),
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    metadata JSONB,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC(18, 6) NOT NULL,
    metric_unit VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,
    acknowledged_by VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS configuration_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_key VARCHAR(100) NOT NULL,
    config_value TEXT NOT NULL,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC(18, 6) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_trades_trade_id ON trades(trade_id);
CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy);
CREATE INDEX IF NOT EXISTS idx_trades_token_in ON trades(token_in);
CREATE INDEX IF NOT EXISTS idx_trades_token_out ON trades(token_out);
CREATE INDEX IF NOT EXISTS idx_trades_profit_usd ON trades(profit_usd);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_created_at ON trades(created_at);
CREATE INDEX IF NOT EXISTS idx_trades_transaction_hash ON trades(transaction_hash);

CREATE INDEX IF NOT EXISTS idx_trades_history_trade_id ON trades_history(trade_id);
CREATE INDEX IF NOT EXISTS idx_trades_history_created_at ON trades_history(created_at);

CREATE INDEX IF NOT EXISTS idx_system_metrics_name ON system_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);

CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_name ON performance_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON performance_metrics(timestamp);

-- Create views
CREATE VIEW IF NOT EXISTS daily_performance AS
SELECT 
    DATE(created_at) as trade_date,
    COUNT(*) as total_trades,
    COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) as successful_trades,
    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_trades,
    SUM(profit_usd) as total_profit,
    AVG(profit_usd) as avg_profit,
    MAX(profit_usd) as max_profit,
    MIN(profit_usd) as min_profit,
    SUM(gas_cost_usd) as total_gas_cost,
    COUNT(CASE WHEN profit_usd > 0 THEN 1 END) as profitable_trades,
    ROUND(100.0 * COUNT(CASE WHEN profit_usd > 0 THEN 1 END) / COUNT(*), 2) as win_rate
FROM trades
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY trade_date DESC;

CREATE VIEW IF NOT EXISTS strategy_performance AS
SELECT 
    strategy,
    COUNT(*) as total_trades,
    COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) as successful_trades,
    SUM(profit_usd) as total_profit,
    AVG(profit_usd) as avg_profit,
    MAX(profit_usd) as max_profit,
    MIN(profit_usd) as min_profit,
    SUM(gas_cost_usd) as total_gas_cost,
    COUNT(CASE WHEN profit_usd > 0 THEN 1 END) as profitable_trades,
    ROUND(100.0 * COUNT(CASE WHEN profit_usd > 0 THEN 1 END) / COUNT(*), 2) as win_rate
FROM trades
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY strategy
ORDER BY total_profit DESC;

CREATE VIEW IF NOT EXISTS token_performance AS
SELECT 
    token_in,
    token_out,
    COUNT(*) as total_trades,
    SUM(profit_usd) as total_profit,
    AVG(profit_usd) as avg_profit,
    MAX(profit_usd) as max_profit,
    MIN(profit_usd) as min_profit,
    SUM(gas_cost_usd) as total_gas_cost,
    COUNT(CASE WHEN profit_usd > 0 THEN 1 END) as profitable_trades,
    ROUND(100.0 * COUNT(CASE WHEN profit_usd > 0 THEN 1 END) / COUNT(*), 2) as win_rate
FROM trades
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY token_in, token_out
ORDER BY total_profit DESC;

-- Create functions
CREATE OR REPLACE FUNCTION archive_old_trades(days_to_keep INTEGER DEFAULT 90)
RETURNS VOID AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    -- Move old trades to history table
    INSERT INTO trades_history
    SELECT * FROM trades
    WHERE created_at < CURRENT_DATE - INTERVAL '1 day'
    AND status IN ('SUCCESS', 'FAILED')
    RETURNING *;
    
    GET DIAGNOSTICS archived_count = ROW_COUNT;
    
    -- Delete from trades table
    DELETE FROM trades
    WHERE created_at < CURRENT_DATE - INTERVAL '1 day'
    AND status IN ('SUCCESS', 'FAILED');
    
    RAISE NOTICE 'Archived % trades', archived_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_system_health()
RETURNS JSONB AS $$
DECLARE
    total_trades INTEGER;
    successful_trades INTEGER;
    failed_trades INTEGER;
    total_profit NUMERIC;
    avg_profit NUMERIC;
    win_rate NUMERIC;
    recent_errors INTEGER;
    last_trade TIMESTAMP;
BEGIN
    SELECT 
        COUNT(*),
        COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END),
        COUNT(CASE WHEN status = 'FAILED' THEN 1 END),
        SUM(profit_usd),
        AVG(profit_usd),
        ROUND(100.0 * COUNT(CASE WHEN profit_usd > 0 THEN 1 END) / NULLIF(COUNT(*), 0), 2),
        COUNT(CASE WHEN created_at > CURRENT_TIMESTAMP - INTERVAL '1 hour' THEN 1 END),
        MAX(created_at)
    INTO total_trades, successful_trades, failed_trades, total_profit, avg_profit, win_rate, recent_errors, last_trade
    FROM trades
    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days';
    
    RETURN jsonb_build_object(
        'total_trades', total_trades,
        'successful_trades', successful_trades,
        'failed_trades', failed_trades,
        'total_profit', total_profit,
        'avg_profit', avg_profit,
        'win_rate', win_rate,
        'recent_errors', recent_errors,
        'last_trade', last_trade,
        'health_status', CASE 
            WHEN win_rate >= 60 AND total_profit > 0 THEN 'HEALTHY'
            WHEN win_rate >= 40 THEN 'WARNING'
            ELSE 'CRITICAL'
        END
    );
END;
$$ LANGUAGE plpgsql;

-- Create triggers
CREATE OR REPLACE FUNCTION log_configuration_change()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO configuration_history (config_key, config_value, changed_by, reason)
    VALUES (NEW.config_key, NEW.config_value, current_user, 'Automatic change');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER configuration_change_trigger
AFTER INSERT OR UPDATE ON configuration_history
FOR EACH ROW
EXECUTE FUNCTION log_configuration_change();

-- Insert initial configuration
INSERT INTO configuration_history (config_key, config_value, changed_by, reason)
VALUES 
    ('LOAN_AMOUNT_USD', '10000', 'system', 'Initial configuration'),
    ('MAX_LOAN_AMOUNT_USD', '100000', 'system', 'Initial configuration'),
    ('MIN_PROFIT_THRESHOLD_USD', '500', 'system', 'Initial configuration'),
    ('MAX_CONCURRENT_TRADES', '3', 'system', 'Initial configuration'),
    ('TRADING_STRATEGY', 'balanced', 'system', 'Initial configuration'),
    ('MAX_DAILY_LOSS_USD', '10000', 'system', 'Initial configuration'),
    ('GAS_OPTIMIZATION_ENABLED', 'true', 'system', 'Initial configuration'),
    ('AI_PREDICTIONS_ENABLED', 'true', 'system', 'Initial configuration'),
    ('PORTFOLIO_REBALANCING_ENABLED', 'true', 'system', 'Initial configuration');

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trader;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trader;
GRANT USAGE, SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;

-- Create readonly user
CREATE USER readonly_user WITH PASSWORD 'readonly_password';

-- Create materialized views for performance
CREATE MATERIALIZED VIEW IF NOT EXISTS materialized_daily_stats AS
SELECT 
    DATE(created_at) as trade_date,
    COUNT(*) as total_trades,
    COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) as successful_trades,
    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_trades,
    SUM(profit_usd) as total_profit,
    AVG(profit_usd) as avg_profit,
    MAX(profit_usd) as max_profit,
    MIN(profit_usd) as min_profit,
    SUM(gas_cost_usd) as total_gas_cost,
    COUNT(CASE WHEN profit_usd > 0 THEN 1 END) as profitable_trades,
    ROUND(100.0 * COUNT(CASE WHEN profit_usd > 0 THEN 1 END) / COUNT(*), 2) as win_rate
FROM trades
GROUP BY DATE(created_at)
ORDER BY trade_date DESC;

CREATE INDEX IF NOT EXISTS idx_materialized_daily_stats_date ON materialized_daily_stats(trade_date);

-- Refresh materialized view
REFRESH MATERIALIZED VIEW CONCURRENTLY materialized_daily_stats;

COMMENT ON TABLE trades IS 'Stores all trading transactions';
COMMENT ON TABLE trades_history IS 'Archived trading transactions';
COMMENT ON TABLE system_metrics IS 'System performance metrics';
COMMENT ON TABLE alerts IS 'System alerts and notifications';
COMMENT ON TABLE configuration_history IS 'Configuration change history';
COMMENT ON TABLE performance_metrics IS 'Performance metrics over time';

COMMENT ON VIEW daily_performance IS 'Daily performance summary';
COMMENT ON VIEW strategy_performance IS 'Strategy performance summary';
COMMENT ON VIEW token_performance IS 'Token pair performance summary';

COMMENT ON FUNCTION archive_old_trades IS 'Archives old trades to history table';
COMMENT ON FUNCTION get_system_health IS 'Returns system health status';

-- Create scheduled tasks (requires pg_cron extension)
-- CREATE EXTENSION IF NOT EXISTS pg_cron;
-- SELECT cron.schedule('archive-trades', '0 0 * * *', 'SELECT archive_old_trades(90);');
-- SELECT cron.schedule('refresh-materialized-views', '0 * * * *', 'REFRESH MATERIALIZED VIEW CONCURRENTLY materialized_daily_stats;');