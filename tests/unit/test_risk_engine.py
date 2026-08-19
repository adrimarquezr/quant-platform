"""
Tests for Risk Engine — VaR, CVaR, Drawdown calculations, and limit governance.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.application.risk.engine import RiskEngine
from src.domain.models import RiskLimitConfig, RiskVerdict


@pytest.mark.unit
class TestRiskEngine:
    """Test suite for RiskEngine mathematical formulas and limit checks."""

    def setup_method(self) -> None:
        self.engine = RiskEngine()

    def test_historical_var_calculation(self) -> None:
        """Historical VaR 95% on standard normal returns."""
        np.random.seed(42)
        # 1000 daily returns ~ N(0, 1%)
        returns = list(np.random.normal(0, 0.01, 1000))
        var_95 = self.engine.calculate_var(returns, confidence_level=0.95)
        # Expected 5th percentile is approx 1.645 * 0.01 = 0.01645
        assert 0.014 <= var_95 <= 0.019

    def test_cvar_greater_than_or_equal_to_var(self) -> None:
        """CVaR (Expected Shortfall) must always be >= VaR."""
        np.random.seed(42)
        returns = list(np.random.normal(0, 0.015, 500))
        var_95 = self.engine.calculate_var(returns, confidence_level=0.95)
        cvar_95 = self.engine.calculate_cvar(returns, confidence_level=0.95)
        assert cvar_95 >= var_95

    def test_drawdown_details(self) -> None:
        """Drawdown tracking: peak, trough, current, and recovery."""
        # 100 -> 120 (peak) -> 90 (trough) -> 110 -> 130 (new peak / recovered)
        equity = [100.0, 110.0, 120.0, 100.0, 90.0, 110.0, 130.0]
        dd = self.engine.calculate_drawdown_details(equity)
        # Max drawdown from 120 to 90 is (90-120)/120 = -25% -> 0.25
        assert abs(dd.max_drawdown - 0.25) < 1e-4
        assert abs(dd.peak_equity - 130.0) < 1e-4
        assert abs(dd.trough_equity - 90.0) < 1e-4
        assert dd.is_recovered is True
        assert dd.current_drawdown < 1e-4

    def test_risk_limit_approved(self) -> None:
        """A well-behaved portfolio within limits gets APPROVED."""
        equity = [100_000.0 * (1.0 + 0.001 * i) for i in range(100)]
        returns = [0.001] * 100
        weights = {"SPY": 0.20, "QQQ": 0.20, "TLT": 0.20, "GLD": 0.20}
        limits = RiskLimitConfig(
            max_position_weight=0.25,
            max_gross_exposure=1.00,
            max_volatility=0.20,
            max_drawdown=0.15,
        )
        profile = self.engine.evaluate_risk(
            equity_curve=equity,
            returns=returns,
            current_weights=weights,
            limits=limits,
        )
        assert profile.verdict == RiskVerdict.APPROVED
        assert len(profile.violations) == 0

    def test_risk_limit_rejected_on_violations(self) -> None:
        """A portfolio violating concentration and drawdown limits gets REJECTED with details."""
        # Drawdown of 30%
        equity = [100_000.0, 120_000.0, 84_000.0]
        returns = [0.20, -0.30]
        # Position weight 50% exceeds 25% limit
        weights = {"SPY": 0.50, "QQQ": 0.50, "IWM": 0.30}  # Gross = 1.30 > 1.00
        limits = RiskLimitConfig(
            max_position_weight=0.25,
            max_gross_exposure=1.00,
            max_drawdown=0.15,
        )
        profile = self.engine.evaluate_risk(
            equity_curve=equity,
            returns=returns,
            current_weights=weights,
            limits=limits,
        )
        assert profile.verdict == RiskVerdict.REJECTED
        assert len(profile.violations) >= 3
        rule_names = [v.rule_name for v in profile.violations]
        assert "max_position_weight" in rule_names
        assert "max_gross_exposure" in rule_names
        assert "max_drawdown" in rule_names

    def test_beta_calculation(self) -> None:
        """Beta against benchmark is computed accurately."""
        np.random.seed(42)
        benchmark = list(np.random.normal(0.0005, 0.01, 100))
        # Portfolio returns = 1.5 * benchmark + small noise
        portfolio = [1.5 * b + np.random.normal(0, 0.001) for b in benchmark]
        profile = self.engine.evaluate_risk(
            equity_curve=[100.0] * 100,
            returns=portfolio,
            current_weights={"SPY": 1.0},
            benchmark_returns=benchmark,
        )
        assert profile.beta is not None
        assert abs(profile.beta - 1.5) < 0.10
