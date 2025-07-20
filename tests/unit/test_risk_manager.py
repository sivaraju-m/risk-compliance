import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from risk_compliance.risk.risk_manager import PositionSizingResult, RiskMetrics


def test_position_sizing_result():
    """Test the PositionSizingResult dataclass"""
    # Create a position sizing result
    result = PositionSizingResult(
        symbol="AAPL",
        position_size=100,
        position_value=15000.0,
        risk_amount=450.0,
        risk_percentage=3.0,
        confidence_level=0.95,
        risk_metrics={"var": 0.02, "cvar": 0.03, "drawdown": 0.05},
    )

    # Verify the attributes
    assert result.symbol == "AAPL"
    assert result.position_size == 100
    assert result.position_value == 15000.0
    assert result.risk_amount == 450.0
    assert result.risk_percentage == 3.0
    assert result.confidence_level == 0.95
    assert "var" in result.risk_metrics
    assert result.risk_metrics["var"] == 0.02


def test_risk_metrics():
    """Test the RiskMetrics dataclass"""
    # Create risk metrics
    metrics = RiskMetrics(
        var_95=0.02,
        cvar_95=0.03,
        var_99=0.04,
        cvar_99=0.05,
        daily_volatility=0.015,
        annualized_volatility=0.25,
        max_drawdown=0.35,
        downside_deviation=0.018,
    )

    # Verify the attributes
    assert metrics.var_95 == 0.02
    assert metrics.cvar_95 == 0.03
    assert metrics.var_99 == 0.04
    assert metrics.cvar_99 == 0.05
    assert metrics.daily_volatility == 0.015
    assert metrics.annualized_volatility == 0.25
    assert metrics.max_drawdown == 0.35
    assert metrics.downside_deviation == 0.018
