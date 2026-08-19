"""
Integration tests for FastAPI REST API endpoints.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import polars as pl
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.integration
class TestHealthRouter:
    """Test /health endpoint."""

    def test_health_check(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


@pytest.mark.integration
class TestMarketDataRouter:
    """Test /market-data endpoints."""

    def test_list_symbols_empty(self, client: TestClient) -> None:
        response = client.get("/market-data/symbols")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @patch("apps.api.routers.market_data.provider.fetch_ohlcv")
    @patch("apps.api.routers.market_data.storage")
    def test_ingest_market_data(
        self,
        mock_storage: MagicMock,
        mock_fetch: MagicMock,
        client: TestClient,
        sample_ohlcv_df: pl.DataFrame,
    ) -> None:
        mock_fetch.return_value = sample_ohlcv_df
        mock_storage.save_ohlcv.return_value = Path("data/raw/1d/SPY/data.parquet")

        payload = {
            "symbol": "SPY",
            "start_date": "2023-01-01",
            "end_date": "2023-03-01",
            "frequency": "1d",
            "provider": "yahoo_finance",
        }
        response = client.post("/market-data/ingest", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "SPY"
        assert data["row_count"] > 0


@pytest.mark.integration
class TestBacktestsRouter:
    """Test /backtests endpoints."""

    def test_list_available_strategies(self, client: TestClient) -> None:
        response = client.get("/backtests/strategies/available")
        assert response.status_code == 200
        strategies = response.json()
        assert "momentum" in strategies
        assert "mean_reversion" in strategies

    @patch("apps.api.routers.backtests.storage.exists", return_value=False)
    @patch("apps.api.routers.backtests.provider.fetch_ohlcv")
    def test_run_backtest(
        self,
        mock_fetch: MagicMock,
        mock_exists: MagicMock,
        client: TestClient,
        sample_ohlcv_df: pl.DataFrame,
    ) -> None:
        mock_fetch.return_value = sample_ohlcv_df

        payload = {
            "strategy_name": "momentum",
            "parameters": {"lookback_period": 10, "threshold": 0.0},
            "universe": ["SPY"],
            "start_date": "2023-01-02",
            "end_date": "2023-03-14",
            "initial_cash": 100000.0,
        }
        response = client.post("/backtests", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["strategy_name"] == "momentum"
        assert data["status"] == "completed"
        assert "metrics" in data
        assert len(data["equity_curve"]) > 0

        # Retrieve backtest summary
        list_resp = client.get("/backtests")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 1

        # Retrieve specific backtest
        bt_id = data["id"]
        detail_resp = client.get(f"/backtests/{bt_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["id"] == bt_id

    def test_run_unknown_strategy_returns_404(self, client: TestClient) -> None:
        payload = {
            "strategy_name": "non_existent_strategy",
            "parameters": {},
            "universe": ["SPY"],
            "start_date": "2023-01-02",
            "end_date": "2023-03-14",
        }
        response = client.post("/backtests", json=payload)
        assert response.status_code == 404
