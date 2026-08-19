# Quant Platform — Production Quantitative Research & Trading

[![Python Version](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Type Checked: Mypy](https://img.shields.io/badge/mypy-strict%20checked-brightgreen.svg)](https://mypy-lang.org/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Test Coverage](https://img.shields.io/badge/coverage-%3E91%25-brightgreen.svg)](https://pytest.org/)
[![Release Status](https://img.shields.io/badge/status-PRODUCTION%20READY%20(v1.0.0)-success.svg)]()

An institutional-grade quantitative trading research and systematic investment platform built with Python 3.12+, designed for reproducible research, vectorized feature computation, multi-strategy backtesting, automated portfolio optimization, and quantitative risk management.

---

## 🏛️ Architecture Overview

The platform is designed following **Hexagonal / Clean Architecture** principles, enforcing strict separation of concerns across Domain, Application, Features, Strategies, Execution, Infrastructure, and Presentation layers.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                   PRESENTATION & UNIFIED INTERFACES                      │
│   • React Web UI (SPA): Dashboard, Backtester, Data Explorer, Portfolios │
│   • Apache Superset BI: Equity Curves, Risk & VaR, Asset Weights, SQL    │
│   • Unified CLI: quant-platform backtest / risk / data-quality / rebal   │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │ (REST API & Analytics)
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                             FASTAPI REST API                             │
│   /backtests  •  /strategies  •  /market-data  •  /portfolios  •  /risk  │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │ (Service Layer)
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                   APACHE AIRFLOW ORCHESTRATION                           │
│   • market_data_pipeline: Ingest -> Data Quality -> Feature Store        │
│   • daily_quant_pipeline: End-to-End Daily Pipeline & Rebalance          │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
    ┌────────────────────────────────┼────────────────────────────────┐
    ▼                                ▼                                ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│  DATA QUALITY LAYER  │  │   FEATURE ENGINE     │  │  STRATEGY SIGNALS    │
│  10 Automated Checks │  │ Vectorized Returns,  │  │ Momentum, Mean Rev., │
│  Prices, Gaps, OHLC  │  │ Vol, Z-Score, Trends │  │ Parameter Validation │
└──────────┬───────────┘  └──────────┬───────────┘  └──────────┬───────────┘
           │                         │                         │
           └─────────────────────────┼─────────────────────────┘
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                   PORTFOLIO & RISK ENGINES                               │
│  • Equal Weight, Inverse Volatility & Volatility Targeting Sizing        │
│  • Constraints: Max Position Weight, Gross Exposure, Turnover Limits    │
│  • Historical VaR (95%), CVaR (ES), Continuous Drawdowns, HHI, Beta     │
│  • Hard/Soft Governance Limits & Verdict (APPROVED / REJECTED)           │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                      ┌──────────────┴──────────────┐
                      ▼                             ▼
         ┌──────────────────────────┐  ┌──────────────────────────┐
         │     POSTGRESQL 16        │  │     PARQUET DATA LAKE     │
         │  Portfolios, Snapshots,  │  │  Daily OHLCV & Features   │
         │  Risk Metrics, DQ Runs   │  │  Partitioned Storage      │
         └──────────────────────────┘  └──────────────────────────┘
```

---

## 🚀 Key Modules & Capabilities

### 1. Unified Institutional CLI (`quant-platform` / `apps/cli/`)
- Complete command-line interface for research and automated headless operations:
  - `quant-platform backtest`: Runs backtests with ANSI tear sheets and optional `--export-json`.
  - `quant-platform data-quality`: Runs 10-point data quality checks on symbols.
  - `quant-platform rebalance`: Computes constrained target allocations (Equal Weight, Inverse Vol).
  - `quant-platform risk`: Audits risk limits (VaR, CVaR, Drawdown, Exposure) and displays violation logs.
  - `quant-platform version`: Displays system status and environment telemetry.

### 2. Quantitative Backtesting & FIFO Trade Analytics (`src/application/backtesting/`)
- **Next-Bar Open Execution**: Signals generated at bar $t$ are strictly filled at bar $t+1$ at Open price.
- **Institutional Friction Simulator**: Models basis points & volatility-proportional slippage + exchange commissions.
- **FIFO Round-Trip Trade Matching**: Calculates accurate `win_rate`, `profit_factor`, `avg_trade_return`, `best_trade`, `worst_trade`, and `total_trades`.
- **Formally Verified Zero Look-Ahead Bias**: Automated mathematical unit tests verify signal invariance when future data is altered.

### 3. Data Quality Engine (`src/application/data_quality.py`)
- 10 automated rules run before any dataset is ingested:
  1. **Schema**: Column and dtype verification (`timestamp`, `open`, `high`, `low`, `close`, `volume`).
  2. **Minimum Rows**: Minimum sample size threshold.
  3. **Nulls**: Missing value detection.
  4. **Duplicates**: Timestamp uniqueness enforcement.
  5. **Price Positivity**: Strict $open, high, low, close > 0$.
  6. **OHLC Consistency**: $low \le open, close \le high$ and $low \le high$.
  7. **Timestamp Monotonicity**: Ascending temporal ordering.
  8. **Temporal Gaps**: Anomaly detection for non-calendar gaps ($> 5$ days).
  9. **Abnormal Returns**: Outlier return spike detection ($|r| > 50\%$).
  10. **Volume**: Non-negative volume and illiquidity tracking.

### 4. Feature Engineering Engine (`src/features/engine.py`)
- Vectorized computation powered by Polars:
  - **Returns**: 1-day, 5-day, 20-day, 60-day simple and log returns.
  - **Volatility**: 20-day, 60-day annualized rolling volatility ($\sigma \times \sqrt{252}$).
  - **Moving Averages**: Simple (`SMA_10`, `SMA_20`, `SMA_50`, `SMA_200`), Exponential (`EMA_12`, `EMA_26`), Price-to-SMA ratios.
  - **Oscillators**: RSI (14), MACD line, MACD Signal line, MACD Histogram, Bollinger Bands.
  - **Z-Scores & Distance**: Rolling 20-day z-scores with zero-variance protection.
  - **Drawdowns**: Continuous percentage drawdown from rolling maximums.

### 5. Quantitative Strategies (`src/strategies/`)
- **Momentum (`MomentumStrategy`)**: Multi-asset time-series & cross-sectional trend following.
- **Mean Reversion (`MeanReversionStrategy`)**: Vectorized z-score deviation with zero-variance protection and overbought/oversold bands.

### 6. Systematic Portfolio Engine (`src/application/portfolio/engine.py`)
- **Allocation Schemes**:
  - `EQUAL_WEIGHT`: Equal distribution among active signals.
  - `INVERSE_VOLATILITY`: Risk parity weighting inversely proportional to asset volatility ($w_i \propto 1/\sigma_i$).
  - `VOLATILITY_TARGETING`: Scaling exposures to match a target portfolio volatility.
- **Constraints**:
  - `max_position_weight`: Clipping single-asset weights to institutional limits.
  - `max_gross_exposure`: Normalizing gross leverage ($\sum |w_i| \le \text{limit}$).
  - `max_turnover`: Turnover dampening between rebalancing cycles ($|w_t - w_{t-1}| \le \text{limit}$).

### 7. Quantitative Risk Engine (`src/application/risk/engine.py`)
- **Point-in-Time Risk Metrics**:
  - **Historical VaR (95%)**: Non-parametric empirical percentile loss.
  - **CVaR / Expected Shortfall (95%)**: Conditional mean loss beyond VaR.
  - **Annualized Volatility**: Sample standard deviation scaled by $\sqrt{252}$.
  - **Drawdown Details**: Continuous tracking of peak equity, trough equity, current drawdown, max drawdown, and recovery factor.
  - **Concentration (HHI)**: Herfindahl-Hirschman Index across asset holdings.
  - **Market Beta & Correlation**: Systematic exposure against benchmark returns.
- **Governance Limits & Audits**:
  - Evaluates `RiskLimitConfig` and generates detailed `RiskViolation` audit logs.
  - Produces deterministic `RiskVerdict.APPROVED` or `RiskVerdict.REJECTED`.

### 8. Apache Airflow Orchestration (`dags/`)
- **`market_data_pipeline`**: Ingests universe market data $\rightarrow$ validates Data Quality $\rightarrow$ computes feature lake $\rightarrow$ persists Parquet partitions.
- **`daily_quant_pipeline`**: Full daily lifecycle orchestrating data ingestion, data quality, feature generation, strategy signals, portfolio target weights, risk governance limits, and backtest benchmarks.

### 9. Superset Dashboards & SQL Analytics (`infra/superset/`)
- Pre-built analytical views:
  - `v_portfolio_overview`: Current NAV, cash balance, invested capital, position count.
  - `v_portfolio_equity_curve`: Chronological NAV time series and daily return stream.
  - `v_portfolio_holdings`: Detailed weights, unrealized PnL, sectors, and asset classes.
  - `v_risk_metrics_summary`: Point-in-time VaR, CVaR, volatility, leverage, and HHI.
  - `v_risk_violations_audit`: Real-time audit log of all risk limit breaches.
  - `v_strategy_comparison`: Side-by-side performance benchmarks (Sharpe, CAGR, Sortino, Max DD).
  - `v_data_quality_audit`: Quality inspection logs and check statuses per symbol.

---

## 🛠️ Quick Start

### 1. Local Environment Setup

```bash
# Clone repository
git clone https://github.com/adrimarquezr/quant-platform.git
cd quant-platform

# Install in editable mode with development dependencies
pip install -e ".[dev]"

# Run full 10-stage end-to-end demonstration script
python examples/end_to_end_demo.py
```

### 2. Using the CLI Tool

```bash
# Display platform version and telemetry
python -m apps.cli.main version

# Run momentum backtest on SPY and QQQ
python -m apps.cli.main backtest --strategy momentum --symbols SPY QQQ --cash 100000

# Run 10-point data quality checks
python -m apps.cli.main data-quality --symbols SPY QQQ

# Compute portfolio target weights under constraints
python -m apps.cli.main rebalance --symbols SPY QQQ AAPL MSFT --method equal_weight

# Audit portfolio risk limits
python -m apps.cli.main risk --max-vol 0.25 --max-dd 0.20 --max-var 0.05
```

### 4. Running the Web Frontend (React + Vite SPA)

```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Start development server (with HMR and backend proxy)
npm run dev

# Run frontend test suite (Vitest + Testing Library)
npm run test

# Type-check and production build
npm run build
```

### 5. Launching Full Infrastructure with Docker Compose

```bash
# Copy environment configuration
cp .env.example .env

# Start all platform microservices (Frontend, Backend API, Postgres, Redis, Airflow, Superset)
docker compose up -d

# Verify running containers
docker compose ps
```

### 6. Service Endpoints & Access

| Service | URL | Default Credentials | Purpose |
| :--- | :--- | :--- | :--- |
| **Quant Platform Web UI** | `http://localhost:3000` | None | Unified React frontend (Dashboard, Backtests, Portfolios, Explorer) |
| **FastAPI REST Docs** | `http://localhost:8000/docs` | None | Interactive Swagger API documentation |
| **Apache Airflow UI** | `http://localhost:8080` | `airflow` / `airflow` | DAG pipeline monitoring & scheduling |
| **Apache Superset BI** | `http://localhost:8088` | `admin` / `admin` | Portfolio & Risk analytical dashboards |
| **PostgreSQL Database** | `localhost:5432` | `quant_user` / *(set in .env)* | Relational metadata store |

---

## 🧪 Testing & Quality Gate

The platform enforces strict quality standards on all PRs and commits:

```bash
# 1. Run linter and formatting check
ruff check src apps tests dags
ruff format --check src apps tests dags

# 2. Strict static type analysis (67 source files)
mypy src apps tests

# 3. Full test suite with statement coverage (115 tests)
pytest -v --cov=src --cov=apps --cov-report=term-missing
```

### Quality Gate Summary
- **Mypy Type Checking**: 100% clean (0 errors across `src`, `apps`, `tests`).
- **Linter & Formatter**: 100% clean (0 Ruff violations).
- **Test Suite**: 115 tests passing, 0 failures.
- **Statement Coverage**: **91.42%** (exceeds the 85.0% CI threshold).
- **Deprecations**: 0 `datetime.utcnow()` warnings (100% migrated to Python 3.12+ `UTC`).
- **Look-Ahead Bias**: Formally tested and mathematically verified.

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.
