"""
Risk Monitor Module
Real-time risk monitoring with alerts and limit checking
"""

import asyncio
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import logging
import json

from .calculator import RiskCalculator

class RiskLimit:
    """Risk limit definition"""
    
    def __init__(self, name: str, limit_type: str, threshold: float, 
                 severity: str = "WARNING", enabled: bool = True):
        self.name = name
        self.limit_type = limit_type  # var, volatility, concentration, etc.
        self.threshold = threshold
        self.severity = severity  # WARNING, ERROR, CRITICAL
        self.enabled = enabled
        self.breach_count = 0
        self.last_breach = None

class RiskAlert:
    """Risk alert data structure"""
    
    def __init__(self, limit_name: str, current_value: float, threshold: float,
                 severity: str, timestamp: datetime, message: str):
        self.limit_name = limit_name
        self.current_value = current_value
        self.threshold = threshold
        self.severity = severity
        self.timestamp = timestamp
        self.message = message
        self.acknowledged = False

class RealTimeRiskMonitor:
    """Real-time risk monitoring system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.risk_calculator = RiskCalculator()
        
        # Risk limits
        self.risk_limits: Dict[str, RiskLimit] = {}
        self.active_alerts: List[RiskAlert] = []
        
        # Callbacks for alerts
        self.alert_callbacks: List[Callable] = []
        
        # Monitoring state
        self.is_monitoring = False
        self.last_check = None
        
        # Default risk limits
        self._setup_default_limits()
    
    def _setup_default_limits(self):
        """Setup default risk limits"""
        default_limits = [
            RiskLimit("portfolio_var_95", "var_95", -0.05, "WARNING"),
            RiskLimit("portfolio_var_99", "var_99", -0.10, "ERROR"),
            RiskLimit("portfolio_volatility", "volatility", 0.25, "WARNING"),
            RiskLimit("max_drawdown", "max_drawdown", -0.15, "ERROR"),
            RiskLimit("concentration_risk", "concentration_risk", 0.40, "WARNING"),
            RiskLimit("position_limit", "position_size", 0.10, "WARNING"),
        ]
        
        for limit in default_limits:
            self.risk_limits[limit.name] = limit
    
    def add_risk_limit(self, limit: RiskLimit):
        """Add a risk limit"""
        self.risk_limits[limit.name] = limit
        self.logger.info(f"Added risk limit: {limit.name}")
    
    def remove_risk_limit(self, limit_name: str):
        """Remove a risk limit"""
        if limit_name in self.risk_limits:
            del self.risk_limits[limit_name]
            self.logger.info(f"Removed risk limit: {limit_name}")
    
    def add_alert_callback(self, callback: Callable):
        """Add callback function for alerts"""
        self.alert_callbacks.append(callback)
    
    def check_portfolio_risk(self, positions: Dict[str, float], 
                           returns_data: Dict[str, pd.Series],
                           market_data: Optional[Dict[str, float]] = None) -> List[RiskAlert]:
        """Check portfolio against all risk limits"""
        try:
            alerts = []
            
            # Calculate portfolio risk metrics
            risk_metrics = self.risk_calculator.calculate_portfolio_risk(positions, returns_data)
            
            if "error" in risk_metrics:
                self.logger.error(f"Error calculating risk metrics: {risk_metrics['error']}")
                return alerts
            
            # Check each risk limit
            for limit_name, limit in self.risk_limits.items():
                if not limit.enabled:
                    continue
                
                alert = self._check_limit(limit, risk_metrics, positions, market_data)
                if alert:
                    alerts.append(alert)
                    limit.breach_count += 1
                    limit.last_breach = datetime.now()
            
            # Update active alerts
            self.active_alerts.extend(alerts)
            self.last_check = datetime.now()
            
            # Trigger callbacks for new alerts
            for alert in alerts:
                self._trigger_alert_callbacks(alert)
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error checking portfolio risk: {str(e)}")
            return []
    
    def _check_limit(self, limit: RiskLimit, risk_metrics: Dict[str, float],
                    positions: Dict[str, float], market_data: Optional[Dict[str, float]]) -> Optional[RiskAlert]:
        """Check a specific risk limit"""
        try:
            current_value = None
            
            # Get current value based on limit type
            if limit.limit_type in risk_metrics:
                current_value = risk_metrics[limit.limit_type]
            elif limit.limit_type == "position_size":
                # Check individual position sizes
                max_position = self._check_position_limits(positions)
                current_value = max_position
            else:
                self.logger.warning(f"Unknown limit type: {limit.limit_type}")
                return None
            
            if current_value is None:
                return None
            
            # Check if limit is breached
            is_breached = False
            
            if limit.limit_type in ["var_95", "var_99", "max_drawdown"]:
                # For negative metrics (losses), breach if current < threshold
                is_breached = current_value < limit.threshold
            else:
                # For positive metrics, breach if current > threshold
                is_breached = current_value > limit.threshold
            
            if is_breached:
                message = (f"Risk limit '{limit.name}' breached: "
                          f"current={current_value:.4f}, limit={limit.threshold:.4f}")
                
                return RiskAlert(
                    limit_name=limit.name,
                    current_value=current_value,
                    threshold=limit.threshold,
                    severity=limit.severity,
                    timestamp=datetime.now(),
                    message=message
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking limit {limit.name}: {str(e)}")
            return None
    
    def _check_position_limits(self, positions: Dict[str, float]) -> float:
        """Check individual position size limits"""
        try:
            if not positions:
                return 0.0
            
            total_value = sum(abs(pos) for pos in positions.values())
            
            if total_value == 0:
                return 0.0
            
            # Return maximum position as percentage of total
            max_position = max(abs(pos) for pos in positions.values())
            return max_position / total_value
            
        except Exception as e:
            self.logger.error(f"Error checking position limits: {str(e)}")
            return 0.0
    
    def _trigger_alert_callbacks(self, alert: RiskAlert):
        """Trigger all registered alert callbacks"""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {str(e)}")
    
    async def start_monitoring(self, positions_source: Callable, 
                             returns_data_source: Callable,
                             check_interval: int = 60):
        """Start real-time monitoring"""
        self.is_monitoring = True
        self.logger.info("Starting real-time risk monitoring...")
        
        while self.is_monitoring:
            try:
                # Get current positions and returns data
                positions = await self._get_data_async(positions_source)
                returns_data = await self._get_data_async(returns_data_source)
                
                if positions and returns_data:
                    # Check risk limits
                    alerts = self.check_portfolio_risk(positions, returns_data)
                    
                    if alerts:
                        self.logger.warning(f"Generated {len(alerts)} risk alerts")
                
                # Wait for next check
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(check_interval)
    
    def stop_monitoring(self):
        """Stop real-time monitoring"""
        self.is_monitoring = False
        self.logger.info("Stopped real-time risk monitoring")
    
    async def _get_data_async(self, data_source: Callable) -> Any:
        """Get data from async or sync source"""
        try:
            if asyncio.iscoroutinefunction(data_source):
                return await data_source()
            else:
                return data_source()
        except Exception as e:
            self.logger.error(f"Error getting data from source: {str(e)}")
            return None
    
    def get_active_alerts(self, severity: Optional[str] = None) -> List[RiskAlert]:
        """Get active alerts, optionally filtered by severity"""
        if severity:
            return [alert for alert in self.active_alerts 
                   if alert.severity == severity and not alert.acknowledged]
        return [alert for alert in self.active_alerts if not alert.acknowledged]
    
    def acknowledge_alert(self, alert_index: int):
        """Acknowledge an alert"""
        if 0 <= alert_index < len(self.active_alerts):
            self.active_alerts[alert_index].acknowledged = True
            self.logger.info(f"Acknowledged alert: {self.active_alerts[alert_index].limit_name}")
    
    def clear_acknowledged_alerts(self):
        """Remove acknowledged alerts"""
        self.active_alerts = [alert for alert in self.active_alerts if not alert.acknowledged]
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get risk monitoring summary"""
        return {
            "monitoring_status": self.is_monitoring,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "active_limits": len([l for l in self.risk_limits.values() if l.enabled]),
            "total_limits": len(self.risk_limits),
            "active_alerts": len(self.get_active_alerts()),
            "critical_alerts": len(self.get_active_alerts("CRITICAL")),
            "error_alerts": len(self.get_active_alerts("ERROR")),
            "warning_alerts": len(self.get_active_alerts("WARNING")),
        }
    
    def export_limits_config(self) -> Dict[str, Any]:
        """Export risk limits configuration"""
        return {
            limit_name: {
                "limit_type": limit.limit_type,
                "threshold": limit.threshold,
                "severity": limit.severity,
                "enabled": limit.enabled,
                "breach_count": limit.breach_count,
                "last_breach": limit.last_breach.isoformat() if limit.last_breach else None
            }
            for limit_name, limit in self.risk_limits.items()
        }
    
    def import_limits_config(self, config: Dict[str, Any]):
        """Import risk limits configuration"""
        try:
            for limit_name, limit_config in config.items():
                limit = RiskLimit(
                    name=limit_name,
                    limit_type=limit_config["limit_type"],
                    threshold=limit_config["threshold"],
                    severity=limit_config.get("severity", "WARNING"),
                    enabled=limit_config.get("enabled", True)
                )
                
                # Restore breach history if available
                if "breach_count" in limit_config:
                    limit.breach_count = limit_config["breach_count"]
                
                if "last_breach" in limit_config and limit_config["last_breach"]:
                    limit.last_breach = datetime.fromisoformat(limit_config["last_breach"])
                
                self.risk_limits[limit_name] = limit
            
            self.logger.info(f"Imported {len(config)} risk limits")
            
        except Exception as e:
            self.logger.error(f"Error importing limits config: {str(e)}")
