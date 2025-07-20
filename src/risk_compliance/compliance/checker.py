"""
Compliance Checker Module
Checks trading compliance rules and regulations
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
import json


class ComplianceRule:
    """Compliance rule definition"""

    def __init__(
        self,
        name: str,
        rule_type: str,
        parameters: Dict[str, Any],
        severity: str = "WARNING",
        enabled: bool = True,
    ):
        self.name = name
        self.rule_type = rule_type
        self.parameters = parameters
        self.severity = severity
        self.enabled = enabled
        self.violation_count = 0
        self.last_violation = None


class ComplianceViolation:
    """Compliance violation data structure"""

    def __init__(
        self,
        rule_name: str,
        violation_type: str,
        details: Dict[str, Any],
        severity: str,
        timestamp: datetime,
        message: str,
    ):
        self.rule_name = rule_name
        self.violation_type = violation_type
        self.details = details
        self.severity = severity
        self.timestamp = timestamp
        self.message = message
        self.resolved = False


class ComplianceChecker:
    """Trading compliance checker"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Compliance rules
        self.compliance_rules: Dict[str, ComplianceRule] = {}
        self.violations: List[ComplianceViolation] = []

        # Setup default compliance rules
        self._setup_default_rules()

    def _setup_default_rules(self):
        """Setup default compliance rules"""
        default_rules = [
            ComplianceRule(
                "position_limit",
                "position_size",
                {"max_position_pct": 0.05, "symbol_specific": {}},
                "ERROR",
            ),
            ComplianceRule(
                "sector_concentration",
                "concentration",
                {"max_sector_pct": 0.30},
                "WARNING",
            ),
            ComplianceRule(
                "daily_turnover_limit",
                "turnover",
                {"max_daily_turnover": 0.20},
                "WARNING",
            ),
            ComplianceRule(
                "wash_sale_detection",
                "wash_sale",
                {"lookback_days": 30, "threshold_pct": 0.05},
                "ERROR",
            ),
            ComplianceRule(
                "short_selling_check",
                "short_selling",
                {"allow_short": False, "max_short_pct": 0.0},
                "ERROR",
            ),
            ComplianceRule(
                "leverage_limit",
                "leverage",
                {"max_leverage": 1.0, "include_margin": True},
                "ERROR",
            ),
            ComplianceRule(
                "trading_hours",
                "trading_time",
                {
                    "market_open": "09:30",
                    "market_close": "16:00",
                    "timezone": "US/Eastern",
                },
                "WARNING",
            ),
        ]

        for rule in default_rules:
            self.compliance_rules[rule.name] = rule

    def add_compliance_rule(self, rule: ComplianceRule):
        """Add a compliance rule"""
        self.compliance_rules[rule.name] = rule
        self.logger.info(f"Added compliance rule: {rule.name}")

    def remove_compliance_rule(self, rule_name: str):
        """Remove a compliance rule"""
        if rule_name in self.compliance_rules:
            del self.compliance_rules[rule_name]
            self.logger.info(f"Removed compliance rule: {rule_name}")

    def check_trade_compliance(
        self,
        trade_order: Dict[str, Any],
        current_positions: Dict[str, float],
        market_data: Optional[Dict[str, Any]] = None,
    ) -> List[ComplianceViolation]:
        """Check a trade order against all compliance rules"""
        try:
            violations = []

            for rule_name, rule in self.compliance_rules.items():
                if not rule.enabled:
                    continue

                violation = self._check_rule(
                    rule, trade_order, current_positions, market_data
                )
                if violation:
                    violations.append(violation)
                    rule.violation_count += 1
                    rule.last_violation = datetime.now()

            # Add to violation history
            self.violations.extend(violations)

            return violations

        except Exception as e:
            self.logger.error(f"Error checking trade compliance: {str(e)}")
            return []

    def _check_rule(
        self,
        rule: ComplianceRule,
        trade_order: Dict[str, Any],
        current_positions: Dict[str, float],
        market_data: Optional[Dict[str, Any]],
    ) -> Optional[ComplianceViolation]:
        """Check a specific compliance rule"""
        try:
            if rule.rule_type == "position_size":
                return self._check_position_size(rule, trade_order, current_positions)
            elif rule.rule_type == "concentration":
                return self._check_concentration(
                    rule, trade_order, current_positions, market_data
                )
            elif rule.rule_type == "turnover":
                return self._check_turnover(rule, trade_order, current_positions)
            elif rule.rule_type == "wash_sale":
                return self._check_wash_sale(rule, trade_order, current_positions)
            elif rule.rule_type == "short_selling":
                return self._check_short_selling(rule, trade_order)
            elif rule.rule_type == "leverage":
                return self._check_leverage(rule, trade_order, current_positions)
            elif rule.rule_type == "trading_time":
                return self._check_trading_hours(rule, trade_order)
            else:
                self.logger.warning(f"Unknown rule type: {rule.rule_type}")
                return None

        except Exception as e:
            self.logger.error(f"Error checking rule {rule.name}: {str(e)}")
            return None

    def _check_position_size(
        self,
        rule: ComplianceRule,
        trade_order: Dict[str, Any],
        current_positions: Dict[str, float],
    ) -> Optional[ComplianceViolation]:
        """Check position size limits"""
        try:
            symbol = trade_order.get("symbol")
            quantity = trade_order.get("quantity", 0)

            if not symbol:
                return None

            # Calculate new position after trade
            current_pos = current_positions.get(symbol, 0)
            new_position = current_pos + quantity

            # Calculate portfolio value
            total_value = sum(abs(pos) for pos in current_positions.values())

            if total_value == 0:
                return None

            # Check position as percentage of portfolio
            position_pct = abs(new_position) / total_value
            max_pct = rule.parameters.get("max_position_pct", 0.05)

            # Check symbol-specific limits
            symbol_limits = rule.parameters.get("symbol_specific", {})
            if symbol in symbol_limits:
                max_pct = symbol_limits[symbol]

            if position_pct > max_pct:
                return ComplianceViolation(
                    rule_name=rule.name,
                    violation_type="position_size",
                    details={
                        "symbol": symbol,
                        "current_position_pct": position_pct,
                        "max_allowed_pct": max_pct,
                        "trade_quantity": quantity,
                    },
                    severity=rule.severity,
                    timestamp=datetime.now(),
                    message=f"Position size limit exceeded for {symbol}: {position_pct:.2%} > {max_pct:.2%}",
                )

            return None

        except Exception as e:
            self.logger.error(f"Error checking position size: {str(e)}")
            return None

    def _check_concentration(
        self,
        rule: ComplianceRule,
        trade_order: Dict[str, Any],
        current_positions: Dict[str, float],
        market_data: Optional[Dict[str, Any]],
    ) -> Optional[ComplianceViolation]:
        """Check sector/industry concentration limits"""
        try:
            # This is a simplified check - in practice, you'd need sector mapping data
            symbol = trade_order.get("symbol")

            if not symbol or not market_data:
                return None

            # Get sector information (simplified)
            sector_map = market_data.get("sector_map", {})
            symbol_sector = sector_map.get(symbol)

            if not symbol_sector:
                return None

            # Calculate sector exposure after trade
            sector_exposure = 0
            total_value = sum(abs(pos) for pos in current_positions.values())

            for pos_symbol, position in current_positions.items():
                if sector_map.get(pos_symbol) == symbol_sector:
                    sector_exposure += abs(position)

            # Add trade impact
            quantity = trade_order.get("quantity", 0)
            sector_exposure += abs(quantity)

            if total_value > 0:
                sector_pct = sector_exposure / total_value
                max_sector_pct = rule.parameters.get("max_sector_pct", 0.30)

                if sector_pct > max_sector_pct:
                    return ComplianceViolation(
                        rule_name=rule.name,
                        violation_type="concentration",
                        details={
                            "sector": symbol_sector,
                            "sector_exposure_pct": sector_pct,
                            "max_allowed_pct": max_sector_pct,
                        },
                        severity=rule.severity,
                        timestamp=datetime.now(),
                        message=f"Sector concentration limit exceeded for {symbol_sector}: {sector_pct:.2%} > {max_sector_pct:.2%}",
                    )

            return None

        except Exception as e:
            self.logger.error(f"Error checking concentration: {str(e)}")
            return None

    def _check_turnover(
        self,
        rule: ComplianceRule,
        trade_order: Dict[str, Any],
        current_positions: Dict[str, float],
    ) -> Optional[ComplianceViolation]:
        """Check daily turnover limits"""
        try:
            # Simplified turnover check
            quantity = abs(trade_order.get("quantity", 0))
            total_value = sum(abs(pos) for pos in current_positions.values())

            if total_value == 0:
                return None

            turnover_pct = quantity / total_value
            max_turnover = rule.parameters.get("max_daily_turnover", 0.20)

            if turnover_pct > max_turnover:
                return ComplianceViolation(
                    rule_name=rule.name,
                    violation_type="turnover",
                    details={
                        "trade_turnover_pct": turnover_pct,
                        "max_allowed_pct": max_turnover,
                        "trade_quantity": quantity,
                    },
                    severity=rule.severity,
                    timestamp=datetime.now(),
                    message=f"Daily turnover limit exceeded: {turnover_pct:.2%} > {max_turnover:.2%}",
                )

            return None

        except Exception as e:
            self.logger.error(f"Error checking turnover: {str(e)}")
            return None

    def _check_wash_sale(
        self,
        rule: ComplianceRule,
        trade_order: Dict[str, Any],
        current_positions: Dict[str, float],
    ) -> Optional[ComplianceViolation]:
        """Check for potential wash sale violations"""
        try:
            # Simplified wash sale check
            # In practice, you'd need historical trade data
            symbol = trade_order.get("symbol")
            quantity = trade_order.get("quantity", 0)

            # Check if this is a buy after a recent sell (wash sale pattern)
            if quantity > 0:  # Buying
                # This would need historical trade data to implement properly
                pass

            return None

        except Exception as e:
            self.logger.error(f"Error checking wash sale: {str(e)}")
            return None

    def _check_short_selling(
        self, rule: ComplianceRule, trade_order: Dict[str, Any]
    ) -> Optional[ComplianceViolation]:
        """Check short selling compliance"""
        try:
            quantity = trade_order.get("quantity", 0)
            allow_short = rule.parameters.get("allow_short", False)

            if quantity < 0 and not allow_short:
                return ComplianceViolation(
                    rule_name=rule.name,
                    violation_type="short_selling",
                    details={
                        "symbol": trade_order.get("symbol"),
                        "quantity": quantity,
                        "short_allowed": allow_short,
                    },
                    severity=rule.severity,
                    timestamp=datetime.now(),
                    message=f"Short selling not allowed: {trade_order.get('symbol')} quantity={quantity}",
                )

            return None

        except Exception as e:
            self.logger.error(f"Error checking short selling: {str(e)}")
            return None

    def _check_leverage(
        self,
        rule: ComplianceRule,
        trade_order: Dict[str, Any],
        current_positions: Dict[str, float],
    ) -> Optional[ComplianceViolation]:
        """Check leverage limits"""
        try:
            # Simplified leverage check
            total_long = sum(pos for pos in current_positions.values() if pos > 0)
            total_short = sum(abs(pos) for pos in current_positions.values() if pos < 0)

            # Add trade impact
            quantity = trade_order.get("quantity", 0)
            if quantity > 0:
                total_long += quantity
            else:
                total_short += abs(quantity)

            # Calculate gross leverage (simplified)
            total_exposure = total_long + total_short
            # Assume total capital = total long positions (simplified)
            leverage = total_exposure / max(total_long, 1) if total_long > 0 else 0

            max_leverage = rule.parameters.get("max_leverage", 1.0)

            if leverage > max_leverage:
                return ComplianceViolation(
                    rule_name=rule.name,
                    violation_type="leverage",
                    details={
                        "current_leverage": leverage,
                        "max_allowed_leverage": max_leverage,
                        "total_exposure": total_exposure,
                    },
                    severity=rule.severity,
                    timestamp=datetime.now(),
                    message=f"Leverage limit exceeded: {leverage:.2f}x > {max_leverage:.2f}x",
                )

            return None

        except Exception as e:
            self.logger.error(f"Error checking leverage: {str(e)}")
            return None

    def _check_trading_hours(
        self, rule: ComplianceRule, trade_order: Dict[str, Any]
    ) -> Optional[ComplianceViolation]:
        """Check trading hours compliance"""
        try:
            from datetime import time
            import pytz

            # Get current time in market timezone
            timezone = rule.parameters.get("timezone", "US/Eastern")
            tz = pytz.timezone(timezone)
            current_time = datetime.now(tz).time()

            # Parse market hours
            market_open = time.fromisoformat(
                rule.parameters.get("market_open", "09:30")
            )
            market_close = time.fromisoformat(
                rule.parameters.get("market_close", "16:00")
            )

            # Check if trading outside market hours
            if not (market_open <= current_time <= market_close):
                return ComplianceViolation(
                    rule_name=rule.name,
                    violation_type="trading_time",
                    details={
                        "current_time": current_time.isoformat(),
                        "market_open": market_open.isoformat(),
                        "market_close": market_close.isoformat(),
                        "timezone": timezone,
                    },
                    severity=rule.severity,
                    timestamp=datetime.now(),
                    message=f"Trading outside market hours: {current_time} not in {market_open}-{market_close} {timezone}",
                )

            return None

        except Exception as e:
            self.logger.error(f"Error checking trading hours: {str(e)}")
            return None

    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get compliance summary"""
        return {
            "active_rules": len(
                [r for r in self.compliance_rules.values() if r.enabled]
            ),
            "total_rules": len(self.compliance_rules),
            "total_violations": len(self.violations),
            "unresolved_violations": len(
                [v for v in self.violations if not v.resolved]
            ),
            "critical_violations": len(
                [
                    v
                    for v in self.violations
                    if v.severity == "CRITICAL" and not v.resolved
                ]
            ),
            "error_violations": len(
                [v for v in self.violations if v.severity == "ERROR" and not v.resolved]
            ),
            "warning_violations": len(
                [
                    v
                    for v in self.violations
                    if v.severity == "WARNING" and not v.resolved
                ]
            ),
        }

    def get_violations(
        self, severity: Optional[str] = None, resolved: Optional[bool] = None
    ) -> List[ComplianceViolation]:
        """Get violations with optional filtering"""
        violations = self.violations

        if severity:
            violations = [v for v in violations if v.severity == severity]

        if resolved is not None:
            violations = [v for v in violations if v.resolved == resolved]

        return violations

    def resolve_violation(self, violation_index: int):
        """Mark a violation as resolved"""
        if 0 <= violation_index < len(self.violations):
            self.violations[violation_index].resolved = True
            self.logger.info(
                f"Resolved violation: {self.violations[violation_index].rule_name}"
            )

    def export_rules_config(self) -> Dict[str, Any]:
        """Export compliance rules configuration"""
        return {
            rule_name: {
                "rule_type": rule.rule_type,
                "parameters": rule.parameters,
                "severity": rule.severity,
                "enabled": rule.enabled,
                "violation_count": rule.violation_count,
                "last_violation": (
                    rule.last_violation.isoformat() if rule.last_violation else None
                ),
            }
            for rule_name, rule in self.compliance_rules.items()
        }

    def import_rules_config(self, config: Dict[str, Any]):
        """Import compliance rules configuration"""
        try:
            for rule_name, rule_config in config.items():
                rule = ComplianceRule(
                    name=rule_name,
                    rule_type=rule_config["rule_type"],
                    parameters=rule_config["parameters"],
                    severity=rule_config.get("severity", "WARNING"),
                    enabled=rule_config.get("enabled", True),
                )

                # Restore violation history if available
                if "violation_count" in rule_config:
                    rule.violation_count = rule_config["violation_count"]

                if "last_violation" in rule_config and rule_config["last_violation"]:
                    rule.last_violation = datetime.fromisoformat(
                        rule_config["last_violation"]
                    )

                self.compliance_rules[rule_name] = rule

            self.logger.info(f"Imported {len(config)} compliance rules")

        except Exception as e:
            self.logger.error(f"Error importing rules config: {str(e)}")
