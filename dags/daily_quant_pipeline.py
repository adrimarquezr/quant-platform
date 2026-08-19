"""
Daily Quant Pipeline DAG — End-to-End Orchestration of Quantitative Research Pipeline.

Pipeline:
    market_data_ingestion -> data_quality -> feature_generation ->
    strategy_signals -> portfolio_construction -> risk_audit -> backtest_benchmark
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

DEFAULT_UNIVERSE = ["SPY", "QQQ", "IWM", "TLT", "GLD"]
DATA_DIR = Path("data")


def stage_market_data_ingest(**context) -> list[str]:
    from src.infrastructure.data_providers.yahoo_finance import YahooFinanceProvider
    from src.infrastructure.storage.parquet_storage import ParquetStorage

    provider = YahooFinanceProvider()
    storage = ParquetStorage(base_dir=DATA_DIR)
    end_date = date.today()
    start_date = end_date - timedelta(days=365 * 2)

    symbols_saved: list[str] = []
    for symbol in DEFAULT_UNIVERSE:
        df = provider.fetch_ohlcv(symbol, start_date, end_date)
        storage.save_ohlcv(df, symbol=symbol, frequency="1d")
        symbols_saved.append(symbol)

    return symbols_saved


def stage_data_quality(**context) -> bool:
    from src.application.data_quality import DataQualityValidator
    from src.domain.models import QualityCheckStatus
    from src.infrastructure.storage.parquet_storage import ParquetStorage

    storage = ParquetStorage(base_dir=DATA_DIR)
    validator = DataQualityValidator()

    for symbol in DEFAULT_UNIVERSE:
        df = storage.load_ohlcv(symbol)
        report = validator.validate_dataset(df, symbol=symbol)
        if report.status == QualityCheckStatus.FAILED:
            msg = f"Data quality validation FAILED for {symbol}: {report.errors}"
            raise ValueError(msg)

    return True


def stage_feature_generation(**context) -> bool:
    from src.features.engine import FeatureEngine
    from src.infrastructure.storage.parquet_storage import ParquetStorage

    storage = ParquetStorage(base_dir=DATA_DIR)
    engine = FeatureEngine()

    for symbol in DEFAULT_UNIVERSE:
        df = storage.load_ohlcv(symbol)
        df_feat = engine.transform(df)
        storage.save_features(df_feat, feature_set_name=f"{symbol}_features", version="v1")

    return True


def stage_strategy_signals(**context) -> dict[str, int]:
    from src.features.engine import compute_all_features
    from src.infrastructure.storage.parquet_storage import ParquetStorage
    from src.strategies.mean_reversion import MeanReversionStrategy
    from src.strategies.momentum import MomentumStrategy

    storage = ParquetStorage(base_dir=DATA_DIR)
    data: dict[str, object] = {}
    for s in DEFAULT_UNIVERSE:
        df = storage.load_ohlcv(s)
        data[s] = compute_all_features(df)

    mom_strat = MomentumStrategy()
    mr_strat = MeanReversionStrategy()

    mom_signals = mom_strat.generate_signals(data, {"lookback_period": 20})
    mr_signals = mr_strat.generate_signals(data, {"lookback_period": 20, "entry_threshold": 2.0})

    logger.info(
        "Generated %d Momentum signals and %d Mean Reversion signals",
        len(mom_signals),
        len(mr_signals),
    )
    return {"momentum_signals": len(mom_signals), "mean_reversion_signals": len(mr_signals)}


def stage_portfolio_construction(**context) -> dict[str, float]:
    from src.application.portfolio.engine import PortfolioEngine
    from src.domain.models import PortfolioConstraints, PortfolioConstructionMethod
    from src.features.engine import compute_all_features
    from src.infrastructure.storage.parquet_storage import ParquetStorage
    from src.strategies.momentum import MomentumStrategy

    storage = ParquetStorage(base_dir=DATA_DIR)
    data: dict[str, object] = {}
    for s in DEFAULT_UNIVERSE:
        data[s] = compute_all_features(storage.load_ohlcv(s))

    mom_signals = MomentumStrategy().generate_signals(data, {"lookback_period": 20})

    portfolio_engine = PortfolioEngine()
    target_weights = portfolio_engine.construct_weights(
        signals=mom_signals,
        method=PortfolioConstructionMethod.EQUAL_WEIGHT,
        constraints=PortfolioConstraints(max_position_weight=0.25, max_gross_exposure=1.00),
    )

    logger.info("Target portfolio weights: %s", target_weights.weights)
    return target_weights.weights


def stage_risk_audit(**context) -> str:
    from src.application.risk.engine import RiskEngine
    from src.domain.models import RiskLimitConfig, RiskVerdict

    risk_engine = RiskEngine()
    # Dummy series for periodic risk evaluation
    equity_curve = [100_000.0 * (1.0 + 0.0005 * i) for i in range(50)]
    returns = [0.0005] * 49
    weights = {"SPY": 0.20, "QQQ": 0.20, "IWM": 0.20, "TLT": 0.20, "GLD": 0.20}

    profile = risk_engine.evaluate_risk(
        equity_curve=equity_curve,
        returns=returns,
        current_weights=weights,
        limits=RiskLimitConfig(
            max_position_weight=0.25,
            max_gross_exposure=1.00,
            max_volatility=0.20,
            max_drawdown=0.15,
        ),
    )

    if profile.verdict == RiskVerdict.REJECTED:
        msg = f"Risk limits violated: {[v.description for v in profile.violations]}"
        logger.warning(msg)
        return "REJECTED"

    logger.info("Risk audit PASSED: VaR 95%% = %.2f%%", profile.var_95 * 100)
    return "APPROVED"


def stage_backtest_benchmark(**context) -> dict[str, float]:
    from src.application.backtesting.engine import BacktestEngine
    from src.domain.models import BacktestConfig, TimeRange
    from src.features.engine import compute_all_features
    from src.infrastructure.storage.parquet_storage import ParquetStorage
    from src.strategies.momentum import MomentumStrategy

    storage = ParquetStorage(base_dir=DATA_DIR)
    data: dict[str, object] = {}
    for s in DEFAULT_UNIVERSE:
        data[s] = compute_all_features(storage.load_ohlcv(s))

    end_d = date.today()
    start_d = end_d - timedelta(days=365)

    config = BacktestConfig(
        strategy_name="momentum",
        strategy_version="1.0.0",
        parameters={"lookback_period": 20, "threshold": 0.0},
        universe=DEFAULT_UNIVERSE,
        time_range=TimeRange(start=start_d, end=end_d),
        initial_cash=100_000.0,
    )

    engine = BacktestEngine()
    result = engine.run(config, data, MomentumStrategy())
    logger.info(
        "Completed benchmark backtest: Sharpe=%.2f", result.metrics.get("sharpe_ratio", 0.0)
    )
    return result.metrics


default_args = {
    "owner": "quant_platform",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="daily_quant_pipeline",
    default_args=default_args,
    description="End-to-End Daily Quantitative Trading & Research Pipeline",
    schedule_interval="30 22 * * 1-5",  # 10:30 PM UTC on trading days
    catchup=False,
    tags=["daily", "quant", "backtest", "portfolio", "risk"],
) as dag:
    t_ingest = PythonOperator(
        task_id="market_data_ingestion",
        python_callable=stage_market_data_ingest,
    )

    t_dq = PythonOperator(
        task_id="data_quality_validation",
        python_callable=stage_data_quality,
    )

    t_features = PythonOperator(
        task_id="feature_generation",
        python_callable=stage_feature_generation,
    )

    t_signals = PythonOperator(
        task_id="strategy_signals",
        python_callable=stage_strategy_signals,
    )

    t_portfolio = PythonOperator(
        task_id="portfolio_construction",
        python_callable=stage_portfolio_construction,
    )

    t_risk = PythonOperator(
        task_id="risk_audit",
        python_callable=stage_risk_audit,
    )

    t_backtest = PythonOperator(
        task_id="backtest_benchmark",
        python_callable=stage_backtest_benchmark,
    )

    t_ingest >> t_dq >> t_features >> t_signals >> t_portfolio >> t_risk >> t_backtest
