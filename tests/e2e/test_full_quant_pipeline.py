"""
End-to-End (E2E) Test — Complete Quantitative Trading Pipeline.

Verifies the full lifecycle:
    Market Data -> Data Quality -> Feature Engineering -> Strategy Signals ->
    Portfolio Construction -> Risk Governance -> Backtest Simulation ->
    Database Persistence -> FastAPI REST Exposure.
"""

from __future__ import annotations

from datetime import date

import polars as pl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.application.backtesting.engine import BacktestEngine
from src.application.portfolio.engine import PortfolioEngine
from src.application.services.data_quality_service import DataQualityService
from src.application.services.portfolio_service import PortfolioService
from src.application.services.risk_service import RiskService
from src.domain.models import (
    BacktestConfig,
    PortfolioConstraints,
    PortfolioConstructionMethod,
    QualityCheckStatus,
    RiskLimitConfig,
    RiskVerdict,
    TimeRange,
)
from src.features.engine import FeatureEngine
from src.strategies.mean_reversion import MeanReversionStrategy


@pytest.mark.e2e
def test_complete_quant_pipeline(
    sample_multi_symbol_data: dict[str, pl.DataFrame],
    client: TestClient,
    db_session: Session,
) -> None:
    """Execute and validate the complete Phase 2 quant research & trading lifecycle."""
    db = db_session

    # --------------------------------------------------------------------------
    # Step 1: Data Ingestion & Data Quality Validation
    # --------------------------------------------------------------------------
    dq_service = DataQualityService()
    dq_reports = {}
    for symbol, df in sample_multi_symbol_data.items():
        report = dq_service.validate_and_record(
            df=df,
            symbol=symbol,
            dataset_name="daily_ohlcv_e2e",
            db=db,
        )
        assert report.status in (QualityCheckStatus.PASSED, QualityCheckStatus.WARNING)
        assert report.is_valid is True
        dq_reports[symbol] = report

    assert "SPY" in dq_reports and "QQQ" in dq_reports

    # --------------------------------------------------------------------------
    # Step 2: Feature Engineering (Vectorized Polars)
    # --------------------------------------------------------------------------
    feature_engine = FeatureEngine()
    feature_data: dict[str, pl.DataFrame] = {}
    for symbol, df in sample_multi_symbol_data.items():
        df_feat = feature_engine.transform(df)
        assert "return_1d" in df_feat.columns
        assert "volatility_20d" in df_feat.columns
        assert "sma_20" in df_feat.columns
        assert "z_score_20d" in df_feat.columns
        assert "drawdown" in df_feat.columns
        feature_data[symbol] = df_feat

    # --------------------------------------------------------------------------
    # Step 3: Strategy Signal Generation (Mean Reversion)
    # --------------------------------------------------------------------------
    strategy = MeanReversionStrategy()
    signals = strategy.generate_signals(
        data=feature_data,
        parameters={"lookback_period": 20, "entry_threshold": 1.5, "exit_threshold": 0.5},
    )
    assert len(signals) == 2  # Signals for SPY and QQQ

    # --------------------------------------------------------------------------
    # Step 4: Portfolio Construction & Constraints
    # --------------------------------------------------------------------------
    portfolio_engine = PortfolioEngine()
    constraints = PortfolioConstraints(
        max_position_weight=0.60,
        max_gross_exposure=1.00,
        max_turnover=0.50,
    )
    target_weights = portfolio_engine.construct_weights(
        signals=signals,
        method=PortfolioConstructionMethod.EQUAL_WEIGHT,
        constraints=constraints,
    )
    assert target_weights.gross_exposure <= 1.00 + 1e-4
    for w in target_weights.weights.values():
        assert abs(w) <= 0.60 + 1e-4

    # --------------------------------------------------------------------------
    # Step 5: Backtest Engine Execution
    # --------------------------------------------------------------------------
    backtest_config = BacktestConfig(
        strategy_name="mean_reversion",
        strategy_version=strategy.version,
        parameters={"lookback_period": 20, "entry_threshold": 1.5, "exit_threshold": 0.5},
        universe=["SPY", "QQQ"],
        time_range=TimeRange(start=date(2023, 1, 2), end=date(2023, 3, 14)),
        initial_cash=100_000.0,
        commission_rate_bps=5.0,
        slippage_rate_bps=5.0,
    )
    backtester = BacktestEngine()
    backtest_result = backtester.run(backtest_config, feature_data, strategy)

    assert backtest_result.status.value == "completed"
    assert len(backtest_result.equity_curve) > 0
    assert "total_return" in backtest_result.metrics
    assert "sharpe_ratio" in backtest_result.metrics
    assert "max_drawdown" in backtest_result.metrics

    # --------------------------------------------------------------------------
    # Step 6: Risk Engine Audit & Limit Governance
    # --------------------------------------------------------------------------
    risk_service = RiskService()
    risk_limits = RiskLimitConfig(
        max_position_weight=0.60,
        max_gross_exposure=1.00,
        max_volatility=0.50,
        max_drawdown=0.25,
        max_var_95=0.10,
    )
    risk_profile = risk_service.evaluate_and_record(
        equity_curve=backtest_result.equity_curve,
        returns=backtest_result.returns,
        current_weights=target_weights.weights,
        limits=risk_limits,
        db=db,
    )
    assert risk_profile.verdict == RiskVerdict.APPROVED
    assert risk_profile.var_95 >= 0.0
    assert risk_profile.cvar_95 >= risk_profile.var_95

    # --------------------------------------------------------------------------
    # Step 7: Portfolio Persistence & Rebalancing
    # --------------------------------------------------------------------------
    portfolio_service = PortfolioService()
    portfolio = portfolio_service.create_portfolio(
        db=db,
        name="Quant Alpha E2E Portfolio",
        description="E2E systematic portfolio test",
        initial_cash=100_000.0,
    )
    assert portfolio.id is not None

    # Rebalance portfolio
    latest_prices = {
        symbol: float(df["close"][-1]) for symbol, df in sample_multi_symbol_data.items()
    }
    portfolio_service.rebalance(
        db=db,
        portfolio_id=portfolio.id,
        signals=signals,
        prices=latest_prices,
        method=PortfolioConstructionMethod.EQUAL_WEIGHT,
        constraints=constraints,
    )

    # --------------------------------------------------------------------------
    # Step 8: Query System State via FastAPI REST API
    # --------------------------------------------------------------------------
    # 8.1 Query Portfolio
    port_res = client.get(f"/portfolios/{portfolio.id}")
    assert port_res.status_code == 200
    assert port_res.json()["name"] == "Quant Alpha E2E Portfolio"

    # 8.2 Query Positions
    pos_res = client.get(f"/portfolios/{portfolio.id}/positions")
    assert pos_res.status_code == 200
    assert len(pos_res.json()) >= 1

    # 8.3 Query Performance
    perf_res = client.get(f"/portfolios/{portfolio.id}/performance")
    assert perf_res.status_code == 200
    assert len(perf_res.json()["snapshots"]) >= 1

    # 8.4 Query Risk Metrics
    risk_res = client.get("/risk")
    assert risk_res.status_code == 200
    assert len(risk_res.json()) >= 1

    # 8.5 Query Data Quality Runs
    dq_res = client.get("/data-quality")
    assert dq_res.status_code == 200
    assert len(dq_res.json()) >= 2

    # 8.6 Query Strategies
    strat_res = client.get("/strategies")
    assert strat_res.status_code == 200
    assert len(strat_res.json()) == 2
