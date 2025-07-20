"""
Risk Calculator Module
Calculates various risk metrics for portfolios and individual positions
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging


class RiskCalculator:
    """Calculate various risk metrics for portfolios and positions"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def calculate_var(
        self, returns: pd.Series, confidence_level: float = 0.05
    ) -> float:
        """Calculate Value at Risk (VaR) using historical simulation"""
        try:
            if len(returns) == 0:
                return 0.0

            # Sort returns and find the percentile
            sorted_returns = returns.sort_values()
            index = int(confidence_level * len(sorted_returns))

            if index == 0:
                return sorted_returns.iloc[0]

            return sorted_returns.iloc[index]

        except Exception as e:
            self.logger.error(f"Error calculating VaR: {str(e)}")
            return 0.0

    def calculate_cvar(
        self, returns: pd.Series, confidence_level: float = 0.05
    ) -> float:
        """Calculate Conditional Value at Risk (CVaR)"""
        try:
            var = self.calculate_var(returns, confidence_level)
            # CVaR is the expected value of returns below VaR
            tail_returns = returns[returns <= var]

            if len(tail_returns) == 0:
                return var

            return tail_returns.mean()

        except Exception as e:
            self.logger.error(f"Error calculating CVaR: {str(e)}")
            return 0.0

    def calculate_volatility(self, returns: pd.Series, window: int = 252) -> float:
        """Calculate annualized volatility"""
        try:
            if len(returns) < 2:
                return 0.0

            # Use last 'window' observations
            recent_returns = returns.tail(window)
            return recent_returns.std() * np.sqrt(252)

        except Exception as e:
            self.logger.error(f"Error calculating volatility: {str(e)}")
            return 0.0

    def calculate_beta(
        self, asset_returns: pd.Series, market_returns: pd.Series
    ) -> float:
        """Calculate beta relative to market"""
        try:
            if len(asset_returns) != len(market_returns) or len(asset_returns) < 2:
                return 1.0

            # Align the series
            aligned_data = pd.concat([asset_returns, market_returns], axis=1).dropna()

            if len(aligned_data) < 2:
                return 1.0

            asset_aligned = aligned_data.iloc[:, 0]
            market_aligned = aligned_data.iloc[:, 1]

            covariance = np.cov(asset_aligned, market_aligned)[0, 1]
            market_variance = np.var(market_aligned)

            if market_variance == 0:
                return 1.0

            return covariance / market_variance

        except Exception as e:
            self.logger.error(f"Error calculating beta: {str(e)}")
            return 1.0

    def calculate_sharpe_ratio(
        self, returns: pd.Series, risk_free_rate: float = 0.02
    ) -> float:
        """Calculate Sharpe ratio"""
        try:
            if len(returns) < 2:
                return 0.0

            excess_returns = (
                returns.mean() - risk_free_rate / 252
            )  # Daily risk-free rate
            volatility = returns.std()

            if volatility == 0:
                return 0.0

            return (excess_returns / volatility) * np.sqrt(252)

        except Exception as e:
            self.logger.error(f"Error calculating Sharpe ratio: {str(e)}")
            return 0.0

    def calculate_maximum_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown"""
        try:
            if len(returns) == 0:
                return 0.0

            # Calculate cumulative returns
            cumulative = (1 + returns).cumprod()

            # Calculate running maximum
            running_max = cumulative.expanding().max()

            # Calculate drawdown
            drawdown = (cumulative - running_max) / running_max

            return drawdown.min()

        except Exception as e:
            self.logger.error(f"Error calculating maximum drawdown: {str(e)}")
            return 0.0

    def calculate_portfolio_risk(
        self,
        positions: Dict[str, float],
        returns_data: Dict[str, pd.Series],
        correlation_matrix: Optional[pd.DataFrame] = None,
    ) -> Dict[str, float]:
        """Calculate portfolio-level risk metrics"""
        try:
            risk_metrics = {}

            # Calculate portfolio returns
            portfolio_returns = self._calculate_portfolio_returns(
                positions, returns_data
            )

            if len(portfolio_returns) == 0:
                return {"error": "No portfolio returns data"}

            # Calculate various risk metrics
            risk_metrics["var_95"] = self.calculate_var(portfolio_returns, 0.05)
            risk_metrics["var_99"] = self.calculate_var(portfolio_returns, 0.01)
            risk_metrics["cvar_95"] = self.calculate_cvar(portfolio_returns, 0.05)
            risk_metrics["volatility"] = self.calculate_volatility(portfolio_returns)
            risk_metrics["sharpe_ratio"] = self.calculate_sharpe_ratio(
                portfolio_returns
            )
            risk_metrics["max_drawdown"] = self.calculate_maximum_drawdown(
                portfolio_returns
            )

            # Calculate concentration risk
            risk_metrics["concentration_risk"] = self._calculate_concentration_risk(
                positions
            )

            return risk_metrics

        except Exception as e:
            self.logger.error(f"Error calculating portfolio risk: {str(e)}")
            return {"error": str(e)}

    def _calculate_portfolio_returns(
        self, positions: Dict[str, float], returns_data: Dict[str, pd.Series]
    ) -> pd.Series:
        """Calculate portfolio returns from positions and individual returns"""
        try:
            # Get total portfolio value
            total_value = sum(abs(pos) for pos in positions.values())

            if total_value == 0:
                return pd.Series()

            # Calculate weights
            weights = {symbol: pos / total_value for symbol, pos in positions.items()}

            # Align all return series
            common_dates = None
            for symbol in weights.keys():
                if symbol in returns_data:
                    if common_dates is None:
                        common_dates = returns_data[symbol].index
                    else:
                        common_dates = common_dates.intersection(
                            returns_data[symbol].index
                        )

            if common_dates is None or len(common_dates) == 0:
                return pd.Series()

            # Calculate weighted portfolio returns
            portfolio_returns = pd.Series(0.0, index=common_dates)

            for symbol, weight in weights.items():
                if symbol in returns_data:
                    symbol_returns = returns_data[symbol].reindex(
                        common_dates, fill_value=0
                    )
                    portfolio_returns += weight * symbol_returns

            return portfolio_returns

        except Exception as e:
            self.logger.error(f"Error calculating portfolio returns: {str(e)}")
            return pd.Series()

    def _calculate_concentration_risk(self, positions: Dict[str, float]) -> float:
        """Calculate concentration risk using Herfindahl-Hirschman Index"""
        try:
            if not positions:
                return 0.0

            # Calculate weights (absolute values)
            total_value = sum(abs(pos) for pos in positions.values())

            if total_value == 0:
                return 0.0

            weights = [abs(pos) / total_value for pos in positions.values()]

            # Calculate HHI
            hhi = sum(w**2 for w in weights)

            return hhi

        except Exception as e:
            self.logger.error(f"Error calculating concentration risk: {str(e)}")
            return 0.0

    def calculate_stress_test(
        self, positions: Dict[str, float], stress_scenarios: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """Calculate portfolio value under stress scenarios"""
        try:
            stress_results = {}

            for scenario_name, shocks in stress_scenarios.items():
                scenario_pnl = 0.0

                for symbol, position in positions.items():
                    if symbol in shocks:
                        # Apply shock to position
                        shock_pnl = position * shocks[symbol]
                        scenario_pnl += shock_pnl

                stress_results[scenario_name] = scenario_pnl

            return stress_results

        except Exception as e:
            self.logger.error(f"Error in stress testing: {str(e)}")
            return {}
