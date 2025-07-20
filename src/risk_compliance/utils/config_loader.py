"""
Configuration Loader for Risk Compliance System
"""

import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """Configuration loader for risk compliance system"""

    def __init__(self, config_dir: Optional[Path] = None):
        self.logger = logging.getLogger(__name__)

        if config_dir is None:
            # Default to config directory relative to this file
            self.config_dir = Path(__file__).parent.parent.parent.parent / "config"
        else:
            self.config_dir = Path(config_dir)

        self.config_dir.mkdir(exist_ok=True)

    def load_risk_config(self) -> Dict[str, Any]:
        """Load risk monitoring configuration"""
        try:
            config_file = self.config_dir / "risk_config.yaml"

            if not config_file.exists():
                self.logger.info(
                    f"Risk config file not found at {config_file}, creating default"
                )
                default_config = self._get_default_risk_config()
                self._save_config(config_file, default_config)
                return default_config

            return self._load_yaml_file(config_file)

        except Exception as e:
            self.logger.error(f"Error loading risk config: {str(e)}")
            return self._get_default_risk_config()

    def load_compliance_config(self) -> Dict[str, Any]:
        """Load compliance checking configuration"""
        try:
            config_file = self.config_dir / "compliance_config.yaml"

            if not config_file.exists():
                self.logger.info(
                    f"Compliance config file not found at {config_file}, creating default"
                )
                default_config = self._get_default_compliance_config()
                self._save_config(config_file, default_config)
                return default_config

            return self._load_yaml_file(config_file)

        except Exception as e:
            self.logger.error(f"Error loading compliance config: {str(e)}")
            return self._get_default_compliance_config()

    def load_monitoring_config(self) -> Dict[str, Any]:
        """Load general monitoring configuration"""
        try:
            config_file = self.config_dir / "monitoring_config.yaml"

            if not config_file.exists():
                self.logger.info(
                    f"Monitoring config file not found at {config_file}, creating default"
                )
                default_config = self._get_default_monitoring_config()
                self._save_config(config_file, default_config)
                return default_config

            return self._load_yaml_file(config_file)

        except Exception as e:
            self.logger.error(f"Error loading monitoring config: {str(e)}")
            return self._get_default_monitoring_config()

    def load_expanded_universe(self) -> Dict[str, Any]:
        """Load expanded universe configuration"""
        try:
            # Try multiple locations for expanded universe
            universe_paths = [
                self.config_dir / "expanded_universe.json",
                self.config_dir.parent.parent.parent
                / "ai-trading-machine"
                / "config"
                / "expanded_universe.json",
                Path.cwd() / "config" / "expanded_universe.json",
            ]

            for universe_path in universe_paths:
                if universe_path.exists():
                    self.logger.info(f"Loading expanded universe from: {universe_path}")
                    return self._load_json_file(universe_path)

            # If not found, create a default one
            self.logger.warning("Expanded universe not found, creating default")
            default_universe = self._get_default_universe()
            universe_file = self.config_dir / "expanded_universe.json"
            self._save_json(universe_file, default_universe)
            return default_universe

        except Exception as e:
            self.logger.error(f"Error loading expanded universe: {str(e)}")
            return self._get_default_universe()

    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML configuration file"""
        try:
            with open(file_path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.error(f"Error loading YAML file {file_path}: {str(e)}")
            return {}

    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON configuration file"""
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading JSON file {file_path}: {str(e)}")
            return {}

    def _save_config(self, file_path: Path, config: Dict[str, Any]):
        """Save configuration to YAML file"""
        try:
            with open(file_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            self.logger.info(f"Saved configuration to {file_path}")
        except Exception as e:
            self.logger.error(f"Error saving config to {file_path}: {str(e)}")

    def _save_json(self, file_path: Path, data: Dict[str, Any]):
        """Save data to JSON file"""
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"Saved JSON data to {file_path}")
        except Exception as e:
            self.logger.error(f"Error saving JSON to {file_path}: {str(e)}")

    def _get_default_risk_config(self) -> Dict[str, Any]:
        """Get default risk monitoring configuration"""
        return {
            "risk_limits": {
                "portfolio_var_95": {
                    "limit_type": "var_95",
                    "threshold": -0.05,
                    "severity": "WARNING",
                    "enabled": True,
                },
                "portfolio_var_99": {
                    "limit_type": "var_99",
                    "threshold": -0.10,
                    "severity": "ERROR",
                    "enabled": True,
                },
                "portfolio_volatility": {
                    "limit_type": "volatility",
                    "threshold": 0.25,
                    "severity": "WARNING",
                    "enabled": True,
                },
                "max_drawdown": {
                    "limit_type": "max_drawdown",
                    "threshold": -0.15,
                    "severity": "ERROR",
                    "enabled": True,
                },
                "concentration_risk": {
                    "limit_type": "concentration_risk",
                    "threshold": 0.40,
                    "severity": "WARNING",
                    "enabled": True,
                },
                "position_limit": {
                    "limit_type": "position_size",
                    "threshold": 0.10,
                    "severity": "WARNING",
                    "enabled": True,
                },
            },
            "monitoring": {
                "check_interval_seconds": 60,
                "enable_real_time": True,
                "alert_cooldown_minutes": 5,
            },
            "stress_scenarios": {
                "market_crash": {
                    "description": "20% market decline",
                    "shocks": {"*": -0.20},
                },
                "sector_rotation": {
                    "description": "Tech down 15%, value up 5%",
                    "shocks": {"tech": -0.15, "value": 0.05},
                },
            },
        }

    def _get_default_compliance_config(self) -> Dict[str, Any]:
        """Get default compliance configuration"""
        return {
            "compliance_rules": {
                "position_limit": {
                    "rule_type": "position_size",
                    "parameters": {"max_position_pct": 0.05, "symbol_specific": {}},
                    "severity": "ERROR",
                    "enabled": True,
                },
                "sector_concentration": {
                    "rule_type": "concentration",
                    "parameters": {"max_sector_pct": 0.30},
                    "severity": "WARNING",
                    "enabled": True,
                },
                "daily_turnover_limit": {
                    "rule_type": "turnover",
                    "parameters": {"max_daily_turnover": 0.20},
                    "severity": "WARNING",
                    "enabled": True,
                },
                "wash_sale_detection": {
                    "rule_type": "wash_sale",
                    "parameters": {"lookback_days": 30, "threshold_pct": 0.05},
                    "severity": "ERROR",
                    "enabled": True,
                },
                "short_selling_check": {
                    "rule_type": "short_selling",
                    "parameters": {"allow_short": False, "max_short_pct": 0.0},
                    "severity": "ERROR",
                    "enabled": True,
                },
                "leverage_limit": {
                    "rule_type": "leverage",
                    "parameters": {"max_leverage": 1.0, "include_margin": True},
                    "severity": "ERROR",
                    "enabled": True,
                },
                "trading_hours": {
                    "rule_type": "trading_time",
                    "parameters": {
                        "market_open": "09:30",
                        "market_close": "16:00",
                        "timezone": "US/Eastern",
                    },
                    "severity": "WARNING",
                    "enabled": True,
                },
            },
            "enforcement": {
                "block_on_error": True,
                "warn_on_warning": True,
                "notification_channels": ["email", "slack"],
            },
        }

    def _get_default_monitoring_config(self) -> Dict[str, Any]:
        """Get default monitoring configuration"""
        return {
            "monitoring": {
                "enabled": True,
                "check_interval_seconds": 60,
                "data_retention_days": 30,
            },
            "alerts": {
                "enabled": True,
                "email_notifications": False,
                "slack_notifications": False,
                "log_alerts": True,
            },
            "reporting": {
                "daily_reports": True,
                "weekly_reports": True,
                "monthly_reports": True,
                "report_formats": ["pdf", "html"],
            },
            "data_sources": {
                "bigquery": {
                    "enabled": True,
                    "project_id": "your-project-id",
                    "dataset": "trading_data",
                },
                "local_files": {"enabled": True, "data_directory": "./data"},
            },
        }

    def _get_default_universe(self) -> Dict[str, Any]:
        """Get default trading universe"""
        return {
            "large_cap": [
                "AAPL",
                "MSFT",
                "GOOGL",
                "AMZN",
                "TSLA",
                "META",
                "NVDA",
                "BRK-B",
                "UNH",
                "JNJ",
                "V",
                "PG",
                "JPM",
                "HD",
                "MA",
                "BAC",
                "ABBV",
                "PFE",
                "KO",
                "AVGO",
                "WMT",
                "LLY",
                "TMO",
                "DIS",
                "XOM",
                "CVX",
                "NKE",
            ],
            "mid_cap": [
                "AMD",
                "CRM",
                "ORCL",
                "ACN",
                "TXN",
                "QCOM",
                "MDT",
                "COST",
                "NEE",
                "DHR",
                "VZ",
                "ADBE",
                "ABT",
                "AMGN",
                "PM",
                "UNP",
                "T",
                "BMY",
            ],
            "small_cap": [
                "ETSY",
                "ROKU",
                "PINS",
                "SNAP",
                "SPOT",
                "SQ",
                "TWLO",
                "ZM",
                "DOCU",
                "OKTA",
                "CRWD",
                "NET",
                "FSLY",
                "DBX",
                "WORK",
            ],
            "sectors": {
                "technology": [
                    "AAPL",
                    "MSFT",
                    "GOOGL",
                    "META",
                    "NVDA",
                    "AMD",
                    "CRM",
                    "ORCL",
                ],
                "healthcare": [
                    "JNJ",
                    "UNH",
                    "PFE",
                    "ABBV",
                    "LLY",
                    "TMO",
                    "DHR",
                    "MDT",
                    "ABT",
                    "AMGN",
                    "BMY",
                ],
                "financial": ["JPM", "BAC", "V", "MA", "BRK-B"],
                "consumer": ["AMZN", "WMT", "HD", "PG", "KO", "NKE", "DIS", "COST"],
                "energy": ["XOM", "CVX"],
                "communication": ["VZ", "T"],
            },
        }

    def save_risk_config(self, config: Dict[str, Any]):
        """Save risk configuration"""
        config_file = self.config_dir / "risk_config.yaml"
        self._save_config(config_file, config)

    def save_compliance_config(self, config: Dict[str, Any]):
        """Save compliance configuration"""
        config_file = self.config_dir / "compliance_config.yaml"
        self._save_config(config_file, config)

    def save_monitoring_config(self, config: Dict[str, Any]):
        """Save monitoring configuration"""
        config_file = self.config_dir / "monitoring_config.yaml"
        self._save_config(config_file, config)
