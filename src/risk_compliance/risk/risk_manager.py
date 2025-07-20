"""
Advanced Risk Management Module
===============================
Implements VaR, CVaR, and position sizing algorithms for the AI Trading Machine.

This module provides comprehensive risk management capabilities:
1. Value at Risk (VaR) calculation using historical and parametric methods
2. Conditional Value at Risk (CVaR) for tail risk assessment
3. Position sizing algorithms based on risk metrics
4. Portfolio-level risk monitoring and constraints

Author: AI Trading Machine
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PositionSizingResult:
    """Result of position sizing calculation"""

    symbol: str
    position_size: int
    position_value: float
    risk_amount: float
    risk_percentage: float
    confidence_level: float
    risk_metrics: Dict[str, float]


@dataclass
class RiskMetrics:
    """Collection of risk metrics for a portfolio or position"""

    var_95: float
    cvar_95: float
    var_99: float
    cvar_99: float
    daily_volatility: float
    annualized_volatility: float
    max_drawdown: float
    downside_deviation: float
    beta: Optional[float] = None
    correlation_matrix: Optional[pd.DataFrame] = None


@dataclass
class RiskCheckResult:
    """Result of a risk check operation"""

    approved: bool
    message: str
    adjusted_position_size: Optional[float] = None
    risk_metrics: Optional[Dict[str, float]] = None


class RiskManager:
    """
    Advanced Risk Management Module implementing VaR, CVaR and position sizing

    Key Features:
    1. Multiple VaR calculation methods (historical, parametric)
    2. CVaR (Expected Shortfall) for tail risk assessment
    3. Position sizing based on risk tolerance
    4. Portfolio-level risk aggregation
    """

    def __init__(
        self,
        risk_free_rate: float = 0.05,
        confidence_level: float = 0.95,
        max_portfolio_var: float = 0.02,  # 2% daily VaR limit
        max_position_size_pct: float = 0.05,  # 5% max position size
        volatility_lookback: int = 252,
        var_lookback: int = 252,
        **kwargs,
    ):
        """
        Initialize the Risk Manager

        Args:
            risk_free_rate: Annual risk-free rate (default: 5%)
            confidence_level: Confidence level for VaR calculation (default: 95%)
            max_portfolio_var: Maximum portfolio VaR as percentage (default: 2%)
            max_position_size_pct: Maximum position size as % of portfolio (default: 5%)
            volatility_lookback: Lookback period for volatility calculation (default: 252 days)
            var_lookback: Lookback period for VaR calculation (default: 252 days)
        """
        self.risk_free_rate = risk_free_rate
        self.confidence_level = confidence_level
        self.max_portfolio_var = max_portfolio_var
        self.max_position_size_pct = max_position_size_pct
        self.volatility_lookback = volatility_lookback
        self.var_lookback = var_lookback

        # Additional parameters from kwargs
        self.use_correlation = kwargs.get("use_correlation", True)
        self.stress_test_scenarios = kwargs.get(
            "stress_test_scenarios", ["2008_crisis", "2020_covid"]
        )
        self.rebalance_threshold = kwargs.get(
            "rebalance_threshold", 0.1
        )  # 10% deviation triggers rebalance

        logger.info(
            f"Risk Manager initialized with confidence level: {confidence_level*100}%, "
            f"max portfolio VaR: {max_portfolio_var*100}%"
        )

    def check_position_risk(
        self,
        symbol: str,
        position_size: float,
        portfolio_value: float,
        current_positions: Dict[str, Any],
        action: str,
    ) -> RiskCheckResult:
        """
        Check if a new position meets risk criteria

        Args:
            symbol: Trading symbol
            position_size: Size of position in currency
            portfolio_value: Total portfolio value
            current_positions: Dictionary of current positions
            action: Trade action (BUY or SELL)

        Returns:
            RiskCheckResult with approval status and potentially adjusted position size
        """
        # Basic position size check
        position_pct = position_size / portfolio_value

        if position_pct > self.max_position_size_pct:
            adjusted_size = portfolio_value * self.max_position_size_pct
            return RiskCheckResult(
                approved=True,
                message=f"Position size reduced from {position_pct:.2%} to {self.max_position_size_pct:.2%}",
                adjusted_position_size=adjusted_size,
                risk_metrics={"position_pct": position_pct},
            )

        # Calculate concentration in similar assets (e.g., same sector)
        # This would require sector information, using a simplified version
        similar_exposure = 0
        for pos in current_positions.values():
            if (
                pos.get("sector") == symbol.split("_")[0]
            ):  # Simple sector check based on prefix
                similar_exposure += pos.get("value", 0)

        sector_exposure_pct = (similar_exposure + position_size) / portfolio_value
        max_sector_exposure = 0.25  # 25% max in one sector

        if sector_exposure_pct > max_sector_exposure:
            return RiskCheckResult(
                approved=False,
                message=f"Sector exposure would exceed {max_sector_exposure:.2%}",
                risk_metrics={"sector_exposure": sector_exposure_pct},
            )

        # Check overall portfolio concentration
        total_positions = len(current_positions)
        max_positions = 20  # Maximum number of positions

        if (
            action == "BUY"
            and symbol not in current_positions
            and total_positions >= max_positions
        ):
            return RiskCheckResult(
                approved=False,
                message=f"Maximum number of positions ({max_positions}) reached",
                risk_metrics={"total_positions": total_positions},
            )

        # All checks passed
        return RiskCheckResult(
            approved=True,
            message="Position meets risk criteria",
            risk_metrics={
                "position_pct": position_pct,
                "sector_exposure": (
                    sector_exposure_pct if "similar_exposure" in locals() else 0
                ),
            },
        )

    def check_trade_risk(
        self,
        symbol: str,
        quantity: int,
        price: float,
        action: str,
        portfolio_value: float,
        historical_data: Optional[pd.DataFrame] = None,
    ) -> RiskCheckResult:
        """
        Check if a trade meets risk criteria based on historical data

        Args:
            symbol: Trading symbol
            quantity: Number of shares/contracts
            price: Current price
            action: Trade action (BUY or SELL)
            portfolio_value: Total portfolio value
            historical_data: Historical price data for VaR calculation

        Returns:
            RiskCheckResult with approval status and risk metrics
        """
        position_value = quantity * price
        position_pct = position_value / portfolio_value

        # Basic position size check
        if position_pct > self.max_position_size_pct:
            adjusted_size = portfolio_value * self.max_position_size_pct
            adjusted_quantity = int(adjusted_size / price)
            return RiskCheckResult(
                approved=True,
                message=f"Position size reduced from {position_pct:.2%} to {self.max_position_size_pct:.2%}",
                adjusted_position_size=adjusted_size,
                risk_metrics={"position_pct": position_pct},
            )

        # If we have historical data, calculate VaR
        risk_metrics = {}
        if historical_data is not None:
            # Calculate daily returns
            if "close" in historical_data.columns:
                returns = historical_data["close"].pct_change().dropna()

                if len(returns) > 30:  # Need sufficient data
                    daily_volatility = returns.std()
                    var_95 = self.calculate_parametric_var(
                        position_value=position_value,
                        volatility=daily_volatility,
                        confidence_level=0.95,
                    )
                    var_pct = var_95 / portfolio_value

                    risk_metrics.update(
                        {
                            "daily_volatility": daily_volatility,
                            "var_95": var_95,
                            "var_95_pct": var_pct,
                        }
                    )

                    # Check if VaR exceeds limits
                    max_position_var_pct = 0.01  # 1% max VaR for individual position
                    if var_pct > max_position_var_pct:
                        # Calculate position size that would meet VaR limit
                        adjusted_position_value = (
                            max_position_var_pct / var_pct
                        ) * position_value
                        adjusted_quantity = int(adjusted_position_value / price)

                        return RiskCheckResult(
                            approved=True,
                            message=f"Position VaR reduced from {var_pct:.2%} to {max_position_var_pct:.2%}",
                            adjusted_position_size=adjusted_position_value,
                            risk_metrics=risk_metrics,
                        )

        # All checks passed
        return RiskCheckResult(
            approved=True,
            message="Trade meets risk criteria",
            risk_metrics=risk_metrics,
        )

    def calculate_historical_var(
        self,
        returns: np.ndarray,
        confidence_level: Optional[float] = None,
        investment_value: float = 1.0,
    ) -> float:
        """
        Calculate Value at Risk using historical method

        Args:
            returns: Array of historical returns
            confidence_level: Confidence level (default: instance value)
            investment_value: Value of the investment (default: 1.0)

        Returns:
            Value at Risk as a positive number
        """
        if confidence_level is None:
            confidence_level = self.confidence_level

        if len(returns) < 30:
            logger.warning(
                f"Insufficient data for VaR calculation: {len(returns)} data points"
            )
            return 0.0

        # Sort returns from worst to best
        sorted_returns = np.sort(returns)

        # Find the index corresponding to the confidence level
        index = int(np.ceil(len(sorted_returns) * (1 - confidence_level)) - 1)
        index = max(0, index)  # Ensure index is not negative

        # Get the return at that index
        var_return = abs(sorted_returns[index])

        # Convert to investment value
        var = var_return * investment_value

        return var

    def calculate_parametric_var(
        self,
        returns: np.ndarray,
        confidence_level: Optional[float] = None,
        investment_value: float = 1.0,
    ) -> float:
        """
        Calculate Value at Risk using parametric (variance-covariance) method

        Args:
            returns: Array of historical returns
            confidence_level: Confidence level (default: instance value)
            investment_value: Value of the investment (default: 1.0)

        Returns:
            Value at Risk as a positive number
        """
        if confidence_level is None:
            confidence_level = self.confidence_level

        if len(returns) < 30:
            logger.warning(
                f"Insufficient data for parametric VaR: {len(returns)} data points"
            )
            return 0.0

        # Calculate mean and standard deviation of returns
        mean_return = np.mean(returns)
        std_dev = np.std(returns, ddof=1)

        # Calculate Z-score for the confidence level
        z_score = stats.norm.ppf(1 - confidence_level)

        # Calculate VaR
        var = -(mean_return + z_score * std_dev) * investment_value

        # Return as positive number
        return max(0, var)

    def calculate_cvar(
        self,
        returns: np.ndarray,
        confidence_level: Optional[float] = None,
        investment_value: float = 1.0,
    ) -> float:
        """
        Calculate Conditional Value at Risk (Expected Shortfall)

        Args:
            returns: Array of historical returns
            confidence_level: Confidence level (default: instance value)
            investment_value: Value of the investment (default: 1.0)

        Returns:
            CVaR as a positive number
        """
        if confidence_level is None:
            confidence_level = self.confidence_level

        if len(returns) < 30:
            logger.warning(
                f"Insufficient data for CVaR calculation: {len(returns)} data points"
            )
            return 0.0

        # Sort returns from worst to best
        sorted_returns = np.sort(returns)

        # Find the index corresponding to the confidence level
        var_index = int(np.ceil(len(sorted_returns) * (1 - confidence_level)) - 1)
        var_index = max(0, var_index)

        # Get all returns worse than VaR
        worst_returns = sorted_returns[: var_index + 1]

        # Calculate CVaR as the average of the worst returns
        cvar = np.mean(worst_returns) * investment_value

        # Return as positive number
        return abs(cvar)

    def calculate_portfolio_var(
        self,
        positions: Dict[str, Dict[str, Any]],
        returns_data: Dict[str, np.ndarray],
        method: str = "historical",
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate portfolio VaR taking into account correlations

        Args:
            positions: Dictionary of positions with keys as symbols and values as position details
            returns_data: Dictionary of returns arrays with keys as symbols
            method: VaR calculation method ('historical' or 'parametric')

        Returns:
            Tuple of (portfolio_var, component_vars)
        """
        if not positions:
            return 0.0, {}

        # Extract position values and create weights
        total_value = sum(pos["value"] for pos in positions.values())
        if total_value == 0:
            return 0.0, {}

        weights = {
            symbol: pos["value"] / total_value for symbol, pos in positions.items()
        }

        # Calculate individual VaRs
        component_vars = {}
        for symbol, pos in positions.items():
            if symbol in returns_data:
                if method == "historical":
                    var = self.calculate_historical_var(
                        returns_data[symbol], investment_value=pos["value"]
                    )
                else:
                    var = self.calculate_parametric_var(
                        returns_data[symbol], investment_value=pos["value"]
                    )
                component_vars[symbol] = var
            else:
                logger.warning(
                    f"No returns data for {symbol}, skipping in VaR calculation"
                )
                component_vars[symbol] = 0.0

        if self.use_correlation and len(positions) > 1:
            # Create returns DataFrame for correlation calculation
            symbols = list(positions.keys())
            returns_df = pd.DataFrame(
                {s: returns_data[s] for s in symbols if s in returns_data}
            )

            if len(returns_df.columns) > 1:
                # Calculate correlation matrix
                corr_matrix = returns_df.corr()

                # Calculate covariance matrix
                volatilities = returns_df.std()
                cov_matrix = np.outer(volatilities, volatilities) * corr_matrix

                # Calculate portfolio variance
                portfolio_variance = 0.0
                for i, symbol_i in enumerate(returns_df.columns):
                    for j, symbol_j in enumerate(returns_df.columns):
                        portfolio_variance += (
                            weights[symbol_i]
                            * weights[symbol_j]
                            * cov_matrix.iloc[i, j]
                        )

                # Calculate portfolio VaR
                z_score = stats.norm.ppf(self.confidence_level)
                portfolio_var = z_score * np.sqrt(portfolio_variance) * total_value

                return portfolio_var, component_vars

        # Fallback to simple sum of component VaRs if correlation can't be used
        portfolio_var = sum(component_vars.values())
        return portfolio_var, component_vars

    def calculate_position_size(
        self,
        symbol: str,
        price: float,
        returns: np.ndarray,
        portfolio_value: float,
        risk_per_trade: float = 0.01,  # 1% risk per trade
        max_var_contribution: float = 0.002,  # 0.2% max VaR contribution
    ) -> PositionSizingResult:
        """
        Calculate optimal position size based on risk parameters

        Args:
            symbol: Trading symbol
            price: Current price
            returns: Historical returns
            portfolio_value: Total portfolio value
            risk_per_trade: Maximum risk per trade as percentage of portfolio
            max_var_contribution: Maximum VaR contribution as percentage of portfolio

        Returns:
            PositionSizingResult with position size and risk metrics
        """
        # Calculate maximum risk amount
        max_risk_amount = portfolio_value * risk_per_trade

        # Calculate daily volatility
        if len(returns) > 30:
            volatility = np.std(returns, ddof=1)
        else:
            volatility = 0.02  # Default volatility if insufficient data

        # Calculate VaR for $1 investment
        var_per_dollar = self.calculate_historical_var(returns, investment_value=1.0)

        # Calculate position size based on VaR
        max_var_amount = portfolio_value * max_var_contribution
        max_position_var = max_position_size = (
            portfolio_value * self.max_position_size_pct
        )

        if var_per_dollar > 0:
            var_based_size = max_var_amount / var_per_dollar
        else:
            var_based_size = max_position_var

        # Position size based on volatility
        if volatility > 0:
            volatility_based_size = max_risk_amount / (price * volatility)
        else:
            volatility_based_size = max_position_var / price

        # Take the more conservative approach
        position_value = min(var_based_size, volatility_based_size, max_position_var)

        # Calculate shares
        shares = int(position_value / price)
        actual_position_value = shares * price

        # Calculate risk metrics
        risk_amount = actual_position_value * var_per_dollar
        risk_percentage = risk_amount / portfolio_value

        # Calculate additional risk metrics
        var_95 = self.calculate_historical_var(
            returns, confidence_level=0.95, investment_value=actual_position_value
        )
        var_99 = self.calculate_historical_var(
            returns, confidence_level=0.99, investment_value=actual_position_value
        )
        cvar_95 = self.calculate_cvar(
            returns, confidence_level=0.95, investment_value=actual_position_value
        )
        cvar_99 = self.calculate_cvar(
            returns, confidence_level=0.99, investment_value=actual_position_value
        )

        risk_metrics = {
            "var_95": var_95,
            "cvar_95": cvar_95,
            "var_99": var_99,
            "cvar_99": cvar_99,
            "daily_volatility": volatility,
            "annualized_volatility": volatility * np.sqrt(252),
            "position_to_portfolio": actual_position_value / portfolio_value,
        }

        return PositionSizingResult(
            symbol=symbol,
            position_size=shares,
            position_value=actual_position_value,
            risk_amount=risk_amount,
            risk_percentage=risk_percentage,
            confidence_level=self.confidence_level,
            risk_metrics=risk_metrics,
        )

    def calculate_complete_risk_metrics(
        self, returns: pd.DataFrame
    ) -> Dict[str, RiskMetrics]:
        """
        Calculate comprehensive risk metrics for multiple assets

        Args:
            returns: DataFrame of returns with assets as columns

        Returns:
            Dictionary of RiskMetrics objects by symbol
        """
        risk_metrics = {}

        # Calculate market returns if provided
        if "MARKET" in returns.columns:
            market_returns = returns["MARKET"]
        else:
            market_returns = None

        # Calculate risk metrics for each asset
        for symbol in returns.columns:
            if symbol == "MARKET":
                continue

            asset_returns = returns[symbol].dropna().values

            if len(asset_returns) < 30:
                logger.warning(
                    f"Insufficient data for {symbol}, skipping risk metrics calculation"
                )
                continue

            # Calculate VaR and CVaR
            var_95 = self.calculate_historical_var(asset_returns, confidence_level=0.95)
            cvar_95 = self.calculate_cvar(asset_returns, confidence_level=0.95)
            var_99 = self.calculate_historical_var(asset_returns, confidence_level=0.99)
            cvar_99 = self.calculate_cvar(asset_returns, confidence_level=0.99)

            # Calculate volatility
            daily_volatility = np.std(asset_returns, ddof=1)
            annualized_volatility = daily_volatility * np.sqrt(252)

            # Calculate maximum drawdown
            cumulative_returns = (1 + pd.Series(asset_returns)).cumprod()
            running_max = cumulative_returns.cummax()
            drawdown = (cumulative_returns / running_max) - 1
            max_drawdown = abs(drawdown.min())

            # Calculate downside deviation (semi-deviation)
            negative_returns = asset_returns[asset_returns < 0]
            downside_deviation = (
                np.std(negative_returns, ddof=1) if len(negative_returns) > 0 else 0
            )

            # Calculate beta if market returns are available
            beta = None
            if market_returns is not None:
                # Align asset returns with market returns
                aligned_data = pd.DataFrame(
                    {"asset": asset_returns, "market": market_returns}
                )
                aligned_data = aligned_data.dropna()

                if len(aligned_data) > 30:
                    cov = np.cov(aligned_data["asset"], aligned_data["market"])[0, 1]
                    market_var = np.var(aligned_data["market"])
                    beta = cov / market_var if market_var > 0 else None

            # Store metrics
            risk_metrics[symbol] = RiskMetrics(
                var_95=var_95,
                cvar_95=cvar_95,
                var_99=var_99,
                cvar_99=cvar_99,
                daily_volatility=daily_volatility,
                annualized_volatility=annualized_volatility,
                max_drawdown=max_drawdown,
                downside_deviation=downside_deviation,
                beta=beta,
                correlation_matrix=None,
            )

        # Add correlation matrix if multiple assets
        if len(returns.columns) > 1:
            correlation_matrix = returns.corr()
            for symbol in risk_metrics:
                risk_metrics[symbol].correlation_matrix = correlation_matrix

        return risk_metrics
