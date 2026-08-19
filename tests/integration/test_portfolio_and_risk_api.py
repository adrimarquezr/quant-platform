"""
Integration tests for Phase 2 API routers: Portfolios, Risk, Data Quality, and Strategies.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import polars as pl
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestPortfoliosRouter:
    """Test /portfolios endpoints."""

    def test_create_and_get_portfolio(self, client: TestClient) -> None:
        payload = {
            "name": "Tech Momentum Fund",
            "description": "Cross-sectional momentum portfolio",
            "initial_cash": 250_000.0,
        }
        res = client.post("/portfolios", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Tech Momentum Fund"
        assert data["cash"] == 250_000.0
        portfolio_id = data["id"]

        # List portfolios
        list_res = client.get("/portfolios")
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1

        # Get specific portfolio
        get_res = client.get(f"/portfolios/{portfolio_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == portfolio_id

        # Get positions
        pos_res = client.get(f"/portfolios/{portfolio_id}/positions")
        assert pos_res.status_code == 200
        assert isinstance(pos_res.json(), list)

        # Get performance
        perf_res = client.get(f"/portfolios/{portfolio_id}/performance")
        assert perf_res.status_code == 200
        assert perf_res.json()["portfolio_id"] == portfolio_id


@pytest.mark.integration
class TestRiskRouter:
    """Test /risk endpoints."""

    def test_evaluate_risk_endpoint(self, client: TestClient) -> None:
        payload = {
            "equity_curve": [100.0, 100.5, 100.2, 100.8, 101.0, 101.5],
            "returns": [0.005, -0.003, 0.006, 0.002, 0.005],
            "current_weights": {"SPY": 0.20, "QQQ": 0.20, "TLT": 0.20},
            "max_position_weight": 0.25,
            "max_gross_exposure": 1.00,
            "max_volatility": 0.30,
            "max_drawdown": 0.15,
            "max_var_95": 0.05,
        }
        res = client.post("/risk/evaluate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "var_95" in data
        assert "cvar_95" in data
        assert "volatility" in data
        assert "verdict" in data
        assert data["verdict"] == "APPROVED"

        # List risk metrics
        metrics_res = client.get("/risk")
        assert metrics_res.status_code == 200
        assert len(metrics_res.json()) >= 1

    def test_risk_violations_endpoint(self, client: TestClient) -> None:
        # Submit portfolio with position exceeding limits
        payload = {
            "equity_curve": [100.0, 70.0],
            "returns": [-0.30],
            "current_weights": {"SPY": 0.60, "QQQ": 0.60},
            "max_position_weight": 0.25,
            "max_gross_exposure": 1.00,
            "max_drawdown": 0.15,
        }
        res = client.post("/risk/evaluate", json=payload)
        assert res.status_code == 200
        assert res.json()["verdict"] == "REJECTED"

        # Query violations
        viol_res = client.get("/risk/violations")
        assert viol_res.status_code == 200
        assert len(viol_res.json()) >= 1


@pytest.mark.integration
class TestDataQualityRouter:
    """Test /data-quality endpoints."""

    @patch("apps.api.routers.data_quality.storage.exists", return_value=True)
    @patch("apps.api.routers.data_quality.storage.load_ohlcv")
    def test_validate_symbol_and_list_runs(
        self,
        mock_load: MagicMock,
        mock_exists: MagicMock,
        client: TestClient,
        sample_ohlcv_df: pl.DataFrame,
    ) -> None:
        mock_load.return_value = sample_ohlcv_df

        res = client.post("/data-quality/validate/SPY")
        assert res.status_code == 200
        data = res.json()
        assert data["symbol"] == "SPY"
        assert data["is_valid"] is True
        assert len(data["checks"]) >= 5

        # List runs
        list_res = client.get("/data-quality")
        assert list_res.status_code == 200
        runs = list_res.json()
        assert len(runs) >= 1
        run_id = runs[0]["id"]

        # Get run details
        run_detail = client.get(f"/data-quality/{run_id}")
        assert run_detail.status_code == 200
        assert run_detail.json()["id"] == run_id


@pytest.mark.integration
class TestStrategiesRouter:
    """Test /strategies discovery endpoints."""

    def test_list_strategies(self, client: TestClient) -> None:
        res = client.get("/strategies")
        assert res.status_code == 200
        strategies = res.json()
        names = [s["name"] for s in strategies]
        assert "momentum" in names
        assert "mean_reversion" in names

    def test_get_strategy_schema(self, client: TestClient) -> None:
        res = client.get("/strategies/mean_reversion/schema")
        assert res.status_code == 200
        schema = res.json()
        assert schema["strategy_name"] == "mean_reversion"
        assert "lookback_period" in schema["parameters"]
