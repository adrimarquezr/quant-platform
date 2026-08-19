"""
Unit tests for the Quant Platform CLI (`apps/cli/main.py`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.cli.main import main


@pytest.mark.unit
class TestCLI:
    """Test CLI commands and argument handling."""

    def test_version_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        ret = main(["version"])
        assert ret == 0
        captured = capsys.readouterr().out
        assert "Production Quantitative Trading Platform" in captured
        assert "1.0.0" in captured

    def test_help_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0

    def test_backtest_command(self, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
        json_out = str(tmp_path / "bt_out.json")
        ret = main(
            [
                "backtest",
                "--strategy",
                "momentum",
                "--symbols",
                "SPY",
                "QQQ",
                "--cash",
                "100000",
                "--export-json",
                json_out,
            ]
        )
        assert ret == 0
        captured = capsys.readouterr().out
        assert "BACKTEST PERFORMANCE TEAR SHEET" in captured
        assert Path(json_out).exists()

    def test_data_quality_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        ret = main(["data-quality", "--symbols", "SPY", "QQQ"])
        assert ret == 0
        captured = capsys.readouterr().out
        assert "Data Quality Audit Result: ALL PASSED" in captured

    def test_rebalance_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        ret = main(["rebalance", "--symbols", "SPY", "QQQ", "AAPL", "--method", "equal_weight"])
        assert ret == 0
        captured = capsys.readouterr().out
        assert "CONSTRAINED PORTFOLIO TARGET WEIGHTS" in captured

    def test_risk_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        ret = main(["risk", "--max-vol", "0.30", "--max-dd", "0.25", "--max-var", "0.10"])
        assert ret == 0
        captured = capsys.readouterr().out
        assert "RISK GOVERNANCE PROFILE" in captured
