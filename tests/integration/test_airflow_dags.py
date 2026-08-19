"""
Integration tests for Airflow DAGs structure and syntax integrity.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

DAG_DIR = Path("dags")


@pytest.mark.integration
class TestAirflowDAGs:
    """Validate that DAG files are syntactically valid and contain expected tasks."""

    def test_dags_directory_exists(self) -> None:
        assert DAG_DIR.exists()
        dag_files = list(DAG_DIR.glob("*.py"))
        assert len(dag_files) >= 2

    def test_market_data_pipeline_ast(self) -> None:
        path = DAG_DIR / "market_data_pipeline.py"
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        parsed = ast.parse(content)
        assert isinstance(parsed, ast.Module)
        assert "ingest_market_data" in content
        assert "validate_data_quality" in content
        assert "compute_features" in content

    def test_daily_quant_pipeline_ast(self) -> None:
        path = DAG_DIR / "daily_quant_pipeline.py"
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        parsed = ast.parse(content)
        assert isinstance(parsed, ast.Module)
        assert "stage_market_data_ingest" in content
        assert "stage_data_quality" in content
        assert "stage_feature_generation" in content
        assert "stage_strategy_signals" in content
        assert "stage_portfolio_construction" in content
        assert "stage_risk_audit" in content
        assert "stage_backtest_benchmark" in content
