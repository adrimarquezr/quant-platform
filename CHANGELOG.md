# Changelog

All notable changes to the `quant-platform` project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-08-19 — Production Ready Release (Fase 4)

### Added
- **Unified CLI Tool (`quant-platform`)**:
  - Full CLI with subcommands: `backtest`, `data-quality`, `rebalance`, `risk`, `version`.
  - Registered as console script in `pyproject.toml` and callable via `python -m apps.cli.main`.
  - Rich ANSI performance tear sheets and structured JSON metric export (`--export-json`).
- **Institutional FIFO Trade Analytics**:
  - Full round-trip trade matching algorithm in `MetricsCalculator`.
  - Computes `win_rate`, `profit_factor`, `avg_trade_return`, `best_trade`, `worst_trade`, and `total_trades` from order/execution histories with slippage and commission friction.
- **Formal Look-Ahead Bias Verification**:
  - Dedicated unit test suite `tests/unit/test_lookahead_bias.py` mathematically verifying zero look-ahead bias across feature engineering and next-bar simulation.
- **End-to-End Platform Demonstration**:
  - Standalone runnable script `examples/end_to_end_demo.py` showcasing the full 10-stage quant pipeline.
- **Expanded Test Coverage**:
  - 115 tests passing across unit, integration, and E2E tiers with >91% test coverage.

### Changed
- **Modernized Datetime Handling**:
  - Migrated all deprecated `datetime.utcnow()` occurrences to Python 3.12+ `datetime.now(timezone.utc)` and `datetime.UTC`.
  - Eradicated 52 deprecation warnings across domain models, database ORM, application services, and Pydantic schemas.
- **Strict Typing & Mypy Compliance**:
  - Fixed sequence invariance in `MetricsCalculator` by adopting `Sequence[float]`.
  - Resolved all generator fixture type annotations in `tests/conftest.py` and `tests/integration/test_database.py`.
  - Achieved 100% strict type check pass (`mypy src apps tests` with 0 errors in 67 source files).
- **Resource Lifecycle Management**:
  - Ensured proper database engine disposal and connection cleanup in integration test fixtures.
- **Documentation & Release Artifacts**:
  - Updated `README.md` with complete architecture diagrams, CLI reference, and production operations guide.

---

## [0.2.0] - 2026-08-19 — Phase 2 & Infrastructure (Fase 2)

### Added
- Multi-asset strategy support (Cross-Sectional Momentum, Mean Reversion).
- Systematic portfolio construction engine with constraint enforcement (Equal Weight, Inverse Volatility, Turnover Dampening).
- Quantitative risk engine with Historical VaR 95%, CVaR 95%, Continuous Drawdown tracking, and HHI.
- Airflow DAGs for daily pipeline scheduling (`daily_quant_pipeline.py`, `market_data_pipeline.py`).
- Apache Superset analytics integration with pre-built analytical SQL views.
- Complete FastAPI REST API with endpoints for backtests, market data, portfolios, risk, and data quality.

---

## [0.1.0] - 2026-08-19 — Initial Architecture (Fase 1)

### Added
- Core domain entities, value objects, and interfaces.
- Parquet storage engine with DuckDB query capabilities.
- 10-rule automated data quality validation suite.
- Vectorized feature engineering engine using Polars.
- Baseline backtesting engine with next-bar execution.
