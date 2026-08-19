-- =============================================================================
-- Apache Superset — SQL Views & Analytical Datasets for Quant Platform
-- =============================================================================

-- 1. Portfolio Overview Dataset
CREATE OR REPLACE VIEW v_portfolio_overview AS
SELECT
    p.id AS portfolio_id,
    p.name AS portfolio_name,
    p.total_value AS current_nav,
    p.cash AS cash_balance,
    (p.total_value - p.cash) AS invested_capital,
    CASE WHEN p.total_value > 0 THEN (p.total_value - p.cash) / p.total_value ELSE 0 END AS invested_fraction,
    COUNT(pos.id) AS position_count,
    p.updated_at AS last_updated_at
FROM portfolios p
LEFT JOIN positions pos ON pos.portfolio_id = p.id AND abs(pos.quantity) > 1e-6
GROUP BY p.id, p.name, p.total_value, p.cash, p.updated_at;

-- 2. Portfolio Equity Curve & Drawdowns
CREATE OR REPLACE VIEW v_portfolio_equity_curve AS
SELECT
    ps.portfolio_id,
    p.name AS portfolio_name,
    ps.timestamp AS date,
    ps.total_value AS nav,
    ps.daily_return,
    ps.positions_value,
    ps.cash
FROM portfolio_snapshots ps
JOIN portfolios p ON p.id = ps.portfolio_id
ORDER BY ps.portfolio_id, ps.timestamp ASC;

-- 3. Current Position Weights & Holdings
CREATE OR REPLACE VIEW v_portfolio_holdings AS
SELECT
    pos.portfolio_id,
    p.name AS portfolio_name,
    a.symbol AS asset_symbol,
    a.name AS asset_name,
    a.asset_class,
    a.sector,
    pos.quantity,
    pos.avg_entry_price,
    pos.current_price,
    pos.market_value,
    pos.unrealized_pnl,
    CASE WHEN p.total_value > 0 THEN pos.market_value / p.total_value ELSE 0 END AS position_weight
FROM positions pos
JOIN portfolios p ON p.id = pos.portfolio_id
JOIN assets a ON a.id = pos.asset_id
WHERE abs(pos.quantity) > 1e-6;

-- 4. Risk Metrics & Limit Governance Summary
CREATE OR REPLACE VIEW v_risk_metrics_summary AS
SELECT
    rm.id AS risk_metric_id,
    rm.portfolio_id,
    p.name AS portfolio_name,
    rm.timestamp,
    rm.var_95,
    rm.cvar_95,
    rm.volatility AS annualized_volatility,
    rm.max_drawdown,
    rm.beta,
    rm.concentration AS hhi_concentration,
    rm.leverage AS gross_exposure
FROM risk_metrics rm
LEFT JOIN portfolios p ON p.id = rm.portfolio_id
ORDER BY rm.timestamp DESC;

-- 5. Risk Limit Violations Audit
CREATE OR REPLACE VIEW v_risk_violations_audit AS
SELECT
    rv.id AS violation_id,
    rv.portfolio_id,
    p.name AS portfolio_name,
    rv.rule_name,
    rv.description,
    rv.actual_value,
    rv.limit_value,
    rv.severity,
    rv.created_at AS violation_time
FROM risk_violations rv
LEFT JOIN portfolios p ON p.id = rv.portfolio_id
ORDER BY rv.created_at DESC;

-- 6. Strategy Performance Comparison
CREATE OR REPLACE VIEW v_strategy_comparison AS
SELECT
    s.name AS strategy_name,
    sv.version AS strategy_version,
    b.id AS backtest_id,
    b.status,
    b.started_at,
    bm.total_return,
    bm.cagr,
    bm.annualized_volatility,
    bm.sharpe_ratio,
    bm.sortino_ratio,
    bm.calmar_ratio,
    bm.max_drawdown,
    bm.win_rate,
    bm.profit_factor,
    bm.total_trades,
    bm.turnover
FROM backtests b
JOIN backtest_configs bc ON bc.id = b.config_id
JOIN strategy_versions sv ON sv.id = bc.strategy_version_id
JOIN strategies s ON s.id = sv.strategy_id
LEFT JOIN backtest_metrics bm ON bm.backtest_id = b.id
WHERE b.status = 'completed';

-- 7. Data Quality Validation Audit
CREATE OR REPLACE VIEW v_data_quality_audit AS
SELECT
    dqr.id AS run_id,
    dqr.dataset,
    dqr.symbol,
    dqr.status AS overall_status,
    dqr.rows_checked,
    dqc.check_name,
    dqc.status AS check_status,
    dqc.message AS check_message,
    dqr.created_at
FROM data_quality_runs dqr
LEFT JOIN data_quality_checks dqc ON dqc.run_id = dqr.id
ORDER BY dqr.created_at DESC;
