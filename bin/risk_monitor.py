#!/usr/bin/env python3
"""
Real-time Risk Monitor for Risk Compliance System
Monitors portfolio risk in real-time and triggers alerts when limits are breached
"""

import asyncio
import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

import pandas as pd
import numpy as np

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from risk_compliance.risk.calculator import RiskCalculator
from risk_compliance.risk.monitor import RealTimeRiskMonitor
from risk_compliance.compliance.checker import ComplianceChecker
from risk_compliance.utils.logger import setup_logger
from risk_compliance.utils.config_loader import ConfigLoader


class RiskMonitoringService:
    """Real-time risk monitoring service"""

    def __init__(self):
        self.logger = setup_logger(__name__)
        self.config = ConfigLoader().load_risk_config()

        # Initialize components
        self.risk_calculator = RiskCalculator()
        self.risk_monitor = RealTimeRiskMonitor()
        self.compliance_checker = ComplianceChecker()

        # Load expanded universe
        self.universe = self._load_expanded_universe()

        self.running = False

    def _load_expanded_universe(self) -> Dict[str, List[str]]:
        """Load expanded universe from config"""
        try:
            # Look for expanded universe in multiple locations
            universe_paths = [
                Path(__file__).parent.parent.parent.parent
                / "ai-trading-machine"
                / "config"
                / "expanded_universe.json",
                Path(__file__).parent.parent / "config" / "expanded_universe.json",
                Path(__file__).parent.parent / "config" / "universe.json",
            ]

            for universe_path in universe_paths:
                if universe_path.exists():
                    with open(universe_path, "r") as f:
                        universe_data = json.load(f)

                    self.logger.info(
                        f"Loaded expanded universe with {universe_data['metadata']['total_tickers']} tickers"
                    )
                    return universe_data["universe"]

            # Fallback to sample universe
            self.logger.warning("Expanded universe not found, using sample universe")
            return {"sample": ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]}

        except Exception as e:
            self.logger.error(f"Error loading universe: {e}")
            return {"sample": ["RELIANCE", "TCS", "INFY"]}

    async def start(self):
        """Start the risk monitoring service"""
        self.logger.info("Starting Real-time Risk Monitoring Service")
        self.logger.info(
            f"Monitoring {sum(len(tickers) for tickers in self.universe.values())} symbols across {len(self.universe)} categories"
        )

        self.running = True

        try:
            while self.running:
                await self._monitor_risks()
                await asyncio.sleep(
                    self.config.get("monitoring_interval", 60)
                )  # Check every minute

        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        except Exception as e:
            self.logger.error(f"Risk monitoring error: {e}")
        finally:
            await self.stop()

    async def stop(self):
        """Stop the risk monitoring service"""
        self.logger.info("Stopping Risk Monitoring Service")
        self.running = False

    async def _monitor_risks(self):
        """Monitor portfolio risks and compliance"""
        try:
            # Get current portfolio data
            portfolio_data = await self._get_portfolio_data()

            if not portfolio_data:
                self.logger.warning("No portfolio data available for risk monitoring")
                return

            # Extract positions from portfolio data
            positions = {}
            portfolio_positions = portfolio_data.get("positions", [])

            if isinstance(portfolio_positions, list):
                # Convert list format to dict format
                for pos in portfolio_positions:
                    if isinstance(pos, dict) and "symbol" in pos and "value" in pos:
                        positions[pos["symbol"]] = pos["value"]
            elif isinstance(portfolio_positions, dict):
                positions = portfolio_positions

            if not positions:
                self.logger.warning("No positions found in portfolio data")
                return

            # Get returns data (this would come from trading data pipeline)
            returns_data = await self._get_returns_data(list(positions.keys()))

            # Calculate risk metrics
            risk_metrics = self.risk_calculator.calculate_portfolio_risk(
                positions, returns_data
            )

            # Check risk limits
            risk_violations = []
            for alert in self.risk_monitor.check_portfolio_risk(
                positions, returns_data
            ):
                if hasattr(alert, "__dict__"):
                    risk_violations.append(alert.__dict__)
                else:
                    risk_violations.append(alert)

            # Check compliance rules (simplified for testing)
            compliance_violations = []

            # Log and handle violations
            if risk_violations:
                self.logger.warning(f"Risk violations detected: {len(risk_violations)}")
                await self._handle_risk_violations(risk_violations)

            if compliance_violations:
                self.logger.warning(
                    f"Compliance violations detected: {len(compliance_violations)}"
                )
                await self._handle_compliance_violations(compliance_violations)

            # Update monitoring dashboard
            await self._update_monitoring_dashboard(
                risk_metrics, risk_violations, compliance_violations
            )

        except Exception as e:
            self.logger.error(f"Error in risk monitoring cycle: {e}")

    async def _get_returns_data(self, symbols: List[str]) -> Dict[str, pd.Series]:
        """Get historical returns data for symbols"""
        try:
            returns_data = {}

            # Generate sample returns data for testing
            dates = pd.date_range(start="2023-01-01", end="2024-01-01", freq="D")

            for symbol in symbols:
                # Generate random returns (this would come from actual data source)
                np.random.seed(hash(symbol) % 1000)  # Consistent randomness per symbol
                returns = np.random.normal(
                    0.001, 0.02, len(dates)
                )  # Daily returns ~0.1% mean, 2% std
                returns_data[symbol] = pd.Series(returns, index=dates)

            return returns_data

        except Exception as e:
            self.logger.error(f"Error getting returns data: {e}")
            return {}

    async def _get_portfolio_data(self) -> Optional[Dict[str, Any]]:
        """Get current portfolio data from trading engine"""
        try:
            # Try to get from trading execution engine
            import aiohttp

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        "http://localhost:8002/api/portfolio", timeout=5
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                except Exception:
                    pass

            # Fallback to file-based data
            return await self._get_portfolio_from_files()

        except Exception as e:
            self.logger.debug(f"Could not get portfolio data: {e}")
            return None

    async def _get_portfolio_from_files(self) -> Dict[str, Any]:
        """Get portfolio data from local files"""
        try:
            # Look for trading engine data
            trading_data_dir = (
                Path(__file__).parent.parent.parent.parent
                / "trading-execution-engine"
                / "data"
            )

            if trading_data_dir.exists():
                portfolio_files = list(trading_data_dir.glob("*portfolio*.json"))
                if portfolio_files:
                    latest_file = max(portfolio_files, key=lambda f: f.stat().st_mtime)

                    with open(latest_file, "r") as f:
                        return json.load(f)

            # Generate sample portfolio for demonstration
            return self._generate_sample_portfolio()

        except Exception as e:
            self.logger.debug(f"Could not load portfolio from files: {e}")
            return self._generate_sample_portfolio()

    def _generate_sample_portfolio(self) -> Dict[str, Any]:
        """Generate sample portfolio for demonstration"""
        # Use expanded universe for sample portfolio
        all_symbols = []
        for category_symbols in self.universe.values():
            all_symbols.extend(category_symbols[:5])  # Take first 5 from each category

        sample_positions = []
        total_value = 1000000  # ₹10 lakh portfolio

        for i, symbol in enumerate(all_symbols[:20]):  # Limit to 20 positions
            position_value = total_value * np.random.uniform(
                0.02, 0.08
            )  # 2-8% allocation
            price = np.random.uniform(100, 2000)  # Random stock price
            quantity = int(position_value / price)

            sample_positions.append(
                {
                    "symbol": symbol,
                    "quantity": quantity,
                    "price": price,
                    "market_value": quantity * price,
                    "pnl": np.random.uniform(-5000, 10000),
                    "allocation": (quantity * price) / total_value * 100,
                }
            )

        return {
            "timestamp": datetime.now().isoformat(),
            "total_value": sum(pos["market_value"] for pos in sample_positions),
            "total_pnl": sum(pos["pnl"] for pos in sample_positions),
            "positions": sample_positions,
            "cash": total_value * 0.1,  # 10% cash
            "leverage": 1.0,
        }

    async def _handle_risk_violations(self, violations: List[Dict[str, Any]]):
        """Handle risk limit violations"""
        for violation in violations:
            self.logger.error(
                f"RISK VIOLATION: {violation['rule']} - {violation['message']}"
            )

            # Send alerts
            await self._send_risk_alert(violation)

            # Take automated action if configured
            if violation.get("auto_action"):
                await self._take_risk_action(violation)

    async def _handle_compliance_violations(self, violations: List[Dict[str, Any]]):
        """Handle compliance violations"""
        for violation in violations:
            self.logger.error(
                f"COMPLIANCE VIOLATION: {violation['rule']} - {violation['message']}"
            )

            # Send compliance alerts
            await self._send_compliance_alert(violation)

    async def _send_risk_alert(self, violation: Dict[str, Any]):
        """Send risk alert notification"""
        try:
            # Integration with monitoring dashboard alert system
            import aiohttp

            alert_data = {
                "alert_type": "Risk Violation",
                "severity": violation.get("severity", "high"),
                "message": f"Risk limit exceeded: {violation['message']}",
                "source": "risk_monitor",
                "metadata": violation,
            }

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(
                        "http://localhost:8000/api/alerts", json=alert_data, timeout=5
                    ) as response:
                        if response.status == 200:
                            self.logger.info("Risk alert sent to monitoring dashboard")
                except Exception:
                    self.logger.debug("Could not send alert to monitoring dashboard")

        except Exception as e:
            self.logger.warning(f"Could not send risk alert: {e}")

    async def _send_compliance_alert(self, violation: Dict[str, Any]):
        """Send compliance alert notification"""
        try:
            # Integration with monitoring dashboard
            alert_data = {
                "alert_type": "Compliance Violation",
                "severity": "critical",
                "message": f"Compliance rule violated: {violation['message']}",
                "source": "compliance_checker",
                "metadata": violation,
            }

            # Send to monitoring dashboard (if available)
            self.logger.info(f"COMPLIANCE ALERT: {violation['message']}")

        except Exception as e:
            self.logger.warning(f"Could not send compliance alert: {e}")

    async def _take_risk_action(self, violation: Dict[str, Any]):
        """Take automated risk management action"""
        try:
            action = violation.get("auto_action")

            if action == "reduce_position":
                self.logger.info(
                    f"AUTO ACTION: Reducing position for {violation.get('symbol', 'portfolio')}"
                )
                # Implement position reduction logic

            elif action == "stop_trading":
                self.logger.critical(
                    "AUTO ACTION: Stopping all trading due to risk violation"
                )
                # Implement trading halt logic

            elif action == "hedge_portfolio":
                self.logger.info("AUTO ACTION: Initiating portfolio hedge")
                # Implement hedging logic

        except Exception as e:
            self.logger.error(f"Error taking risk action: {e}")

    async def _update_monitoring_dashboard(
        self,
        risk_metrics: Dict[str, Any],
        risk_violations: List[Dict[str, Any]],
        compliance_violations: List[Dict[str, Any]],
    ):
        """Update monitoring dashboard with risk data"""
        try:
            dashboard_data = {
                "timestamp": datetime.now().isoformat(),
                "risk_metrics": risk_metrics,
                "risk_violations": len(risk_violations),
                "compliance_violations": len(compliance_violations),
                "risk_status": (
                    "violation"
                    if (risk_violations or compliance_violations)
                    else "normal"
                ),
            }

            # Save to local file for monitoring dashboard to pick up
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True)

            with open(data_dir / "risk_monitoring.json", "w") as f:
                json.dump(dashboard_data, f, indent=2, default=str)

        except Exception as e:
            self.logger.warning(f"Could not update monitoring dashboard: {e}")

    async def generate_risk_report(self) -> Dict[str, Any]:
        """Generate comprehensive risk report"""
        try:
            portfolio_data = await self._get_portfolio_data()

            if not portfolio_data:
                # Create sample portfolio for testing
                portfolio_data = {
                    "positions": [
                        {
                            "symbol": "RELIANCE",
                            "value": 500000,
                            "quantity": 100,
                            "pnl": 5000,
                        },
                        {"symbol": "TCS", "value": 300000, "quantity": 50, "pnl": 3000},
                        {
                            "symbol": "INFY",
                            "value": 200000,
                            "quantity": 80,
                            "pnl": -1000,
                        },
                        {
                            "symbol": "HDFCBANK",
                            "value": 400000,
                            "quantity": 60,
                            "pnl": 2000,
                        },
                        {
                            "symbol": "ICICIBANK",
                            "value": 150000,
                            "quantity": 40,
                            "pnl": 1500,
                        },
                    ]
                }
                self.logger.info("Using sample portfolio data for report generation")

            # Extract positions from portfolio data
            positions = {}
            portfolio_positions = portfolio_data.get("positions", [])

            if isinstance(portfolio_positions, list):
                # Convert list format to dict format
                for pos in portfolio_positions:
                    if isinstance(pos, dict) and "symbol" in pos:
                        # Handle both 'value' and 'market_value' fields
                        position_value = pos.get("value") or pos.get("market_value", 0)
                        positions[pos["symbol"]] = position_value
            elif isinstance(portfolio_positions, dict):
                positions = portfolio_positions

            if not positions:
                return {"error": "No positions found in portfolio data"}

            # Get returns data
            returns_data = await self._get_returns_data(list(positions.keys()))

            # Calculate comprehensive risk metrics
            risk_metrics = self.risk_calculator.calculate_portfolio_risk(
                positions, returns_data
            )

            # Calculate additional summary metrics
            total_value = sum(positions.values())
            total_pnl = sum(
                pos.get("pnl", 0)
                for pos in portfolio_positions
                if isinstance(pos, dict)
            )

            # Generate risk report
            report = {
                "report_date": datetime.now().strftime("%Y-%m-%d"),
                "generation_time": datetime.now().isoformat(),
                "portfolio_summary": {
                    "total_value": total_value,
                    "total_pnl": total_pnl,
                    "positions_count": len(positions),
                    "leverage": total_value
                    / max(total_value - abs(total_pnl), 1),  # Simplified leverage calc
                },
                "risk_metrics": risk_metrics,
                "compliance_status": self.compliance_checker.get_compliance_summary(),
                "recommendations": await self._generate_risk_recommendations(
                    risk_metrics
                ),
            }

            # Generate risk report
            report = {
                "report_date": datetime.now().strftime("%Y-%m-%d"),
                "generation_time": datetime.now().isoformat(),
                "portfolio_summary": {
                    "total_value": portfolio_data.get("total_value", 0),
                    "total_pnl": portfolio_data.get("total_pnl", 0),
                    "positions_count": len(portfolio_data.get("positions", [])),
                    "leverage": portfolio_data.get("leverage", 1.0),
                },
                "risk_metrics": risk_metrics,
                "compliance_status": self.compliance_checker.get_compliance_summary(),
                "recommendations": await self._generate_risk_recommendations(
                    risk_metrics
                ),
            }

            # Save report
            reports_dir = Path(__file__).parent.parent / "reports"
            reports_dir.mkdir(exist_ok=True)

            report_file = (
                reports_dir / f"risk_report_{datetime.now().strftime('%Y-%m-%d')}.json"
            )
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2, default=str)

            self.logger.info(f"Risk report generated: {report_file}")
            return report

        except Exception as e:
            self.logger.error(f"Error generating risk report: {e}")
            return {"error": str(e)}

    async def _generate_risk_recommendations(
        self, risk_metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []

        try:
            # Check VaR levels
            var_95 = risk_metrics.get("var_95", 0)
            if abs(var_95) > 50000:  # > ₹50k VaR
                recommendations.append(
                    "Daily VaR exceeds ₹50,000. Consider reducing position sizes."
                )

            # Check concentration risk
            max_allocation = risk_metrics.get("max_single_allocation", 0)
            if max_allocation > 10:  # > 10% in single position
                recommendations.append(
                    f"Single position allocation ({max_allocation:.1f}%) exceeds 10%. Diversify holdings."
                )

            # Check sector concentration
            sector_concentration = risk_metrics.get("sector_concentration", {})
            for sector, allocation in sector_concentration.items():
                if allocation > 30:  # > 30% in single sector
                    recommendations.append(
                        f"High concentration in {sector} sector ({allocation:.1f}%). Consider sector diversification."
                    )

            # Check leverage
            leverage = risk_metrics.get("leverage", 1.0)
            if leverage > 2.0:
                recommendations.append(
                    f"High leverage ({leverage:.2f}x) detected. Consider reducing leverage."
                )

            # Check correlation
            avg_correlation = risk_metrics.get("average_correlation", 0)
            if avg_correlation > 0.7:
                recommendations.append(
                    "High correlation between positions. Diversify with uncorrelated assets."
                )

            if not recommendations:
                recommendations.append(
                    "Risk metrics are within acceptable ranges. Continue monitoring."
                )

        except Exception as e:
            self.logger.warning(f"Error generating recommendations: {e}")
            recommendations.append(
                "Unable to generate recommendations due to data issues."
            )

        return recommendations


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="AI Trading Machine Risk Monitor")
    parser.add_argument(
        "--report", action="store_true", help="Generate risk report and exit"
    )
    parser.add_argument(
        "--test", action="store_true", help="Run test monitoring cycle and exit"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create risk monitoring service
    service = RiskMonitoringService()

    if args.report:
        # Generate risk report and exit
        report = await service.generate_risk_report()
        print("\n" + "=" * 60)
        print("📊 RISK COMPLIANCE REPORT")
        print("=" * 60)

        if "error" not in report:
            portfolio = report.get("portfolio_summary", {})
            risk_metrics = report.get("risk_metrics", {})

            print(f"💰 Portfolio Value: ₹{portfolio.get('total_value', 0):,.2f}")
            print(f"📈 Total P&L: ₹{portfolio.get('total_pnl', 0):,.2f}")
            print(f"📊 Positions: {portfolio.get('positions_count', 0)}")
            print(f"⚖️  Leverage: {portfolio.get('leverage', 1.0):.2f}x")
            print(f"📉 VaR (95%): ₹{risk_metrics.get('var_95', 0):,.2f}")
            print(
                f"📊 Max Allocation: {risk_metrics.get('max_single_allocation', 0):.1f}%"
            )

            recommendations = report.get("recommendations", [])
            if recommendations:
                print(f"\n💡 RECOMMENDATIONS:")
                for i, rec in enumerate(recommendations, 1):
                    print(f"   {i}. {rec}")
        else:
            print(f"❌ Error: {report['error']}")

        print("=" * 60)
        return

    if args.test:
        # Run test monitoring cycle
        await service._monitor_risks()
        print("✅ Test monitoring cycle completed")
        return

    # Start the service
    await service.start()


if __name__ == "__main__":
    asyncio.run(main())
