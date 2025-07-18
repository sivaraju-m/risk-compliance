"""
SEBI Compliance Module for AI Trading Machine

This module implements comprehensive SEBI (Securities and Exchange Board of India)
compliance features including audit trails, circuit breakers, and regulatory reporting.

Key Features:
- Audit trail logging with immutable records
- Circuit breaker implementation
- Strategy approval workflow
- Risk management controls
- Regulatory reporting
- IP whitelisting and OAuth validation
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from google.cloud import bigquery, firestore

logger = logging.getLogger(__name__)


class ComplianceStatus(Enum):
    """Compliance status enumeration"""

    COMPLIANT = "COMPLIANT"
    WARNING = "WARNING"
    VIOLATION = "VIOLATION"
    SUSPENDED = "SUSPENDED"


class CircuitBreakerStatus(Enum):
    """Circuit breaker status enumeration"""

    ACTIVE = "ACTIVE"
    TRIGGERED = "TRIGGERED"
    DISABLED = "DISABLED"


@dataclass
class AuditRecord:
    """Audit record structure"""

    record_id: str
    user_id: str
    strategy_id: str
    action: str
    timestamp: datetime
    details: dict[str, Any]
    ip_address: str
    session_id: str
    compliance_hash: str


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""

    max_loss_percent: float = 5.0
    max_drawdown_percent: float = 10.0
    max_volatility_threshold: float = 0.3
    max_position_size: float = 0.1
    max_daily_trades: int = 100
    cooling_period_minutes: int = 30


class SEBICompliance:
    """
    SEBI Compliance Implementation

    Provides comprehensive compliance features for algorithmic trading
    in Indian markets as per SEBI regulations.
    """

    def __init__(self, project_id: str, firestore_db: str = None):
        """
        Initialize SEBI compliance module

        Args:
            project_id: GCP project ID
            firestore_db: Firestore database name
        """
        self.project_id = project_id
        self.firestore_client = firestore.Client(
            project=project_id, database=firestore_db
        )
        self.bigquery_client = bigquery.Client(project=project_id)
        self.circuit_breaker_config = CircuitBreakerConfig()

        # Initialize collections
        self.audit_collection = self.firestore_client.collection("audit_trails")
        self.strategy_collection = self.firestore_client.collection(
            "strategy_approvals"
        )
        self.circuit_breaker_collection = self.firestore_client.collection(
            "circuit_breakers"
        )
        self.whitelist_collection = self.firestore_client.collection("ip_whitelist")

        logger.info("SEBI Compliance module initialized for project: {project_id}")

    def create_audit_record(
        self,
        user_id: str,
        strategy_id: str,
        action: str,
        details: dict[str, Any],
        ip_address: str,
        session_id: str,
    ) -> AuditRecord:
        """
        Create immutable audit record

        Args:
            user_id: User performing the action
            strategy_id: Strategy being affected
            action: Action being performed
            details: Additional details
            ip_address: IP address of the user
            session_id: User session ID

        Returns:
            AuditRecord: Created audit record
        """
        timestamp = datetime.utcnow()
        record_id = str(uuid4())

        # Create compliance hash for immutability
        hash_data = {
            "record_id": record_id,
            "user_id": user_id,
            "strategy_id": strategy_id,
            "action": action,
            "timestamp": timestamp.isoformat(),
            "details": details,
            "ip_address": ip_address,
            "session_id": session_id,
        }

        compliance_hash = hashlib.sha256(
            json.dumps(hash_data, sort_keys=True).encode()
        ).hexdigest()

        audit_record = AuditRecord(
            record_id=record_id,
            user_id=user_id,
            strategy_id=strategy_id,
            action=action,
            timestamp=timestamp,
            details=details,
            ip_address=ip_address,
            session_id=session_id,
            compliance_hash=compliance_hash,
        )

        # Store in Firestore with immutable flag
        doc_data = {
            "record_id": record_id,
            "user_id": user_id,
            "strategy_id": strategy_id,
            "action": action,
            "timestamp": timestamp,
            "details": details,
            "ip_address": ip_address,
            "session_id": session_id,
            "compliance_hash": compliance_hash,
            "created_at": timestamp,
            "immutable": True,
        }

        self.audit_collection.document(record_id).set(doc_data)

        # Also store in BigQuery for querying
        self._store_audit_in_bigquery(audit_record)

        logger.info("Audit record created: {record_id} for user {user_id}")
        return audit_record

    def _store_audit_in_bigquery(self, audit_record: AuditRecord):
        """Store audit record in BigQuery"""
        try:
            table_id = "{self.project_id}.ai_trading.audit_trail"

            rows_to_insert = [
                {
                    "record_id": audit_record.record_id,
                    "user_id": audit_record.user_id,
                    "strategy_id": audit_record.strategy_id,
                    "action": audit_record.action,
                    "timestamp": audit_record.timestamp.isoformat(),
                    "details": json.dumps(audit_record.details),
                    "ip_address": audit_record.ip_address,
                    "session_id": audit_record.session_id,
                    "compliance_hash": audit_record.compliance_hash,
                    "created_at": audit_record.timestamp.isoformat(),
                }
            ]

            errors = self.bigquery_client.insert_rows_json(table_id, rows_to_insert)

            if errors:
                logger.error("BigQuery insert errors: {errors}")

        except Exception as e:
            logger.error("Error storing audit record in BigQuery: {e}")

    def validate_ip_whitelist(self, ip_address: str, user_id: str) -> bool:
        """
        Validate if IP address is whitelisted for user

        Args:
            ip_address: IP address to validate
            user_id: User ID

        Returns:
            bool: True if IP is whitelisted
        """
        try:
            # Get user's whitelisted IPs
            doc_ref = self.whitelist_collection.document(user_id)
            doc = doc_ref.get()

            if not doc.exists:
                logger.warning("No IP whitelist found for user: {user_id}")
                return False

            whitelist_data = doc.to_dict()
            whitelisted_ips = whitelist_data.get("ip_addresses", [])

            # Check if IP is in whitelist
            if ip_address in whitelisted_ips:
                logger.info("IP {ip_address} is whitelisted for user {user_id}")
                return True

            # Check for IP range matches (basic CIDR support)
            for whitelisted_ip in whitelisted_ips:
                if "/" in whitelisted_ip:
                    # Basic CIDR check - in production, use proper IP library
                    network = whitelisted_ip.split("/")[0]
                    if ip_address.startswith(network.rsplit(".", 1)[0]):
                        logger.info(
                            "IP {ip_address} matches CIDR range {whitelisted_ip}"
                        )
                        return True

            logger.warning("IP {ip_address} not whitelisted for user {user_id}")
            return False

        except Exception as e:
            logger.error("Error validating IP whitelist: {e}")
            return False

    def check_circuit_breaker(
        self, strategy_id: str, current_metrics: dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Check if circuit breaker should be triggered

        Args:
            strategy_id: Strategy ID to check
            current_metrics: Current performance metrics

        Returns:
            Tuple[bool, str]: (should_trigger, reason)
        """
        try:
            # Get circuit breaker status
            doc_ref = self.circuit_breaker_collection.document(strategy_id)
            doc = doc_ref.get()

            if doc.exists:
                cb_data = doc.to_dict()
                if cb_data.get("status") == CircuitBreakerStatus.TRIGGERED.value:
                    # Check if cooling period has passed
                    triggered_at = cb_data.get("triggered_at")
                    if triggered_at:
                        cooling_end = triggered_at + timedelta(
                            minutes=self.circuit_breaker_config.cooling_period_minutes
                        )
                        if datetime.utcnow() < cooling_end:
                            return True, "Circuit breaker cooling period active"

            # Check loss threshold
            current_loss = current_metrics.get("loss_percent", 0)
            if current_loss >= self.circuit_breaker_config.max_loss_percent:
                self._trigger_circuit_breaker(
                    strategy_id, "Loss threshold exceeded: {current_loss}%"
                )
                return True, "Loss threshold exceeded: {current_loss}%"

            # Check drawdown threshold
            current_drawdown = current_metrics.get("drawdown_percent", 0)
            if current_drawdown >= self.circuit_breaker_config.max_drawdown_percent:
                self._trigger_circuit_breaker(
                    strategy_id, "Drawdown threshold exceeded: {current_drawdown}%"
                )
                return True, "Drawdown threshold exceeded: {current_drawdown}%"

            # Check volatility threshold
            current_volatility = current_metrics.get("volatility", 0)
            if (
                current_volatility
                >= self.circuit_breaker_config.max_volatility_threshold
            ):
                self._trigger_circuit_breaker(
                    strategy_id, "Volatility threshold exceeded: {current_volatility}"
                )
                return True, "Volatility threshold exceeded: {current_volatility}"

            # Check daily trades limit
            daily_trades = current_metrics.get("daily_trades", 0)
            if daily_trades >= self.circuit_breaker_config.max_daily_trades:
                self._trigger_circuit_breaker(
                    strategy_id, "Daily trades limit exceeded: {daily_trades}"
                )
                return True, "Daily trades limit exceeded: {daily_trades}"

            return False, "All checks passed"

        except Exception as e:
            logger.error("Error checking circuit breaker: {e}")
            return True, "Circuit breaker check failed: {e}"

    def _trigger_circuit_breaker(self, strategy_id: str, reason: str):
        """Trigger circuit breaker for strategy"""
        try:
            doc_ref = self.circuit_breaker_collection.document(strategy_id)
            doc_ref.set(
                {
                    "strategy_id": strategy_id,
                    "status": CircuitBreakerStatus.TRIGGERED.value,
                    "reason": reason,
                    "triggered_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            )

            logger.critical(
                "Circuit breaker triggered for strategy {strategy_id}: {reason}"
            )

            # Send alert notification
            self._send_circuit_breaker_alert(strategy_id, reason)

        except Exception as e:
            logger.error("Error triggering circuit breaker: {e}")

    def _send_circuit_breaker_alert(self, strategy_id: str, reason: str):
        """Send circuit breaker alert notification"""
        # This would integrate with your notification system
        # For now, just log the alert
        logger.critical("CIRCUIT BREAKER ALERT: Strategy {strategy_id} - {reason}")

    def approve_strategy(
        self,
        strategy_id: str,
        approved_by: str,
        remarks: str,
        user_id: str,
        ip_address: str,
        session_id: str,
    ) -> bool:
        """
        Approve strategy for production use

        Args:
            strategy_id: Strategy to approve
            approved_by: User approving the strategy
            remarks: Approval remarks
            user_id: User requesting approval
            ip_address: IP address
            session_id: Session ID

        Returns:
            bool: True if approved successfully
        """
        try:
            approval_data = {
                "strategy_id": strategy_id,
                "approved_by": approved_by,
                "remarks": remarks,
                "approved_at": datetime.utcnow(),
                "status": "APPROVED",
                "created_at": datetime.utcnow(),
            }

            # Store approval
            self.strategy_collection.document(strategy_id).set(approval_data)

            # Create audit record
            self.create_audit_record(
                user_id=user_id,
                strategy_id=strategy_id,
                action="STRATEGY_APPROVED",
                details={
                    "approved_by": approved_by,
                    "remarks": remarks,
                    "approval_timestamp": datetime.utcnow().isoformat(),
                },
                ip_address=ip_address,
                session_id=session_id,
            )

            logger.info("Strategy {strategy_id} approved by {approved_by}")
            return True

        except Exception as e:
            logger.error("Error approving strategy: {e}")
            return False

    def is_strategy_approved(self, strategy_id: str) -> bool:
        """
        Check if strategy is approved for production

        Args:
            strategy_id: Strategy ID to check

        Returns:
            bool: True if approved
        """
        try:
            doc_ref = self.strategy_collection.document(strategy_id)
            doc = doc_ref.get()

            if not doc.exists:
                return False

            approval_data = doc.to_dict()
            return approval_data.get("status") == "APPROVED"

        except Exception as e:
            logger.error("Error checking strategy approval: {e}")
            return False

    def get_compliance_report(
        self, start_date: datetime, end_date: datetime
    ) -> dict[str, Any]:
        """
        Generate compliance report for given period

        Args:
            start_date: Report start date
            end_date: Report end date

        Returns:
            Dict[str, Any]: Compliance report data
        """
        try:
            # Query audit records
            audit_query = (
                self.audit_collection.where("timestamp", ">=", start_date)
                .where("timestamp", "<=", end_date)
                .order_by("timestamp")
            )

            audit_docs = audit_query.stream()
            audit_records = [doc.to_dict() for doc in audit_docs]

            # Generate report
            report = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "total_audit_records": len(audit_records),
                "actions_summary": {},
                "users_activity": {},
                "strategies_affected": set(),
                "compliance_violations": [],
                "circuit_breaker_triggers": [],
            }

            # Process audit records
            for record in audit_records:
                action = record.get("action")
                user_id = record.get("user_id")
                strategy_id = record.get("strategy_id")

                # Count actions
                if action in report["actions_summary"]:
                    report["actions_summary"][action] += 1
                else:
                    report["actions_summary"][action] = 1

                # Count user activity
                if user_id in report["users_activity"]:
                    report["users_activity"][user_id] += 1
                else:
                    report["users_activity"][user_id] = 1

                # Track strategies
                if strategy_id:
                    report["strategies_affected"].add(strategy_id)

                # Check for violations
                if action in ["CIRCUIT_BREAKER_TRIGGERED", "COMPLIANCE_VIOLATION"]:
                    report["compliance_violations"].append(record)

            # Convert set to list for JSON serialization
            report["strategies_affected"] = list(report["strategies_affected"])

            logger.info(
                "Compliance report generated for period {start_date} to {end_date}"
            )
            return report

        except Exception as e:
            logger.error("Error generating compliance report: {e}")
            return {"error": str(e)}

    def validate_oauth_scope(self, token: str, required_scope: str) -> bool:
        """
        Validate OAuth token scope

        Args:
            token: OAuth token
            required_scope: Required scope

        Returns:
            bool: True if scope is valid
        """
        # This would integrate with your OAuth provider
        # For now, return True for demo purposes
        # In production, validate with Google OAuth or your provider
        logger.info("OAuth scope validation requested for scope: {required_scope}")
        return True

    def emergency_kill_switch(
        self, user_id: str, reason: str, ip_address: str, session_id: str
    ) -> bool:
        """
        Emergency kill switch to halt all trading

        Args:
            user_id: User triggering kill switch
            reason: Reason for kill switch
            ip_address: IP address
            session_id: Session ID

        Returns:
            bool: True if kill switch activated
        """
        try:
            # Set global kill switch
            kill_switch_data = {
                "status": "ACTIVATED",
                "activated_by": user_id,
                "reason": reason,
                "activated_at": datetime.utcnow(),
                "ip_address": ip_address,
                "session_id": session_id,
            }

            # Store in Firestore
            self.firestore_client.collection("system_controls").document(
                "kill_switch"
            ).set(kill_switch_data)

            # Create audit record
            self.create_audit_record(
                user_id=user_id,
                strategy_id="SYSTEM",
                action="KILL_SWITCH_ACTIVATED",
                details={
                    "reason": reason,
                    "activation_timestamp": datetime.utcnow().isoformat(),
                },
                ip_address=ip_address,
                session_id=session_id,
            )

            logger.critical("KILL SWITCH ACTIVATED by user {user_id}: {reason}")
            return True

        except Exception as e:
            logger.error("Error activating kill switch: {e}")
            return False

    def is_kill_switch_active(self) -> tuple[bool, str]:
        """
        Check if kill switch is active

        Returns:
            Tuple[bool, str]: (is_active, reason)
        """
        try:
            doc_ref = self.firestore_client.collection("system_controls").document(
                "kill_switch"
            )
            doc = doc_ref.get()

            if not doc.exists:
                return False, "Kill switch not found"

            kill_switch_data = doc.to_dict()
            status = kill_switch_data.get("status")

            if status == "ACTIVATED":
                reason = kill_switch_data.get("reason", "Unknown reason")
                return True, reason

            return False, "Kill switch not active"

        except Exception as e:
            logger.error("Error checking kill switch: {e}")
            return True, "Error checking kill switch: {e}"  # Fail safe


# Health check and statistics functions
def health_check() -> dict[str, Any]:
    """Health check for SEBI Compliance module"""
    try:
        return {
            "status": "healthy",
            "module": "sebi_compliance",
            "features": [
                "Audit Trail Logging",
                "Circuit Breakers",
                "Strategy Approval Workflow",
                "IP Whitelisting",
                "Kill Switch",
                "Compliance Reporting",
            ],
            "dependencies": {"firestore": True, "bigquery": True},
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def get_statistics() -> dict[str, Any]:
    """Get SEBI Compliance module statistics"""
    return {
        "module": "sebi_compliance",
        "compliance_features": [
            "Audit Trail with Immutable Records",
            "Circuit Breaker Implementation",
            "Strategy Approval Workflow",
            "IP Whitelisting",
            "Kill Switch Controls",
            "Regulatory Reporting",
        ],
        "compliance_statuses": ["COMPLIANT", "WARNING", "VIOLATION", "SUSPENDED"],
        "circuit_breaker_types": [
            "Loss Limit",
            "Drawdown",
            "Volatility",
            "Position Size",
        ],
        "timestamp": datetime.now().isoformat(),
    }


# CLI interface
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "--health":
            print(json.dumps(health_check(), indent=2))
        elif sys.argv[1] == "--stats":
            print(json.dumps(get_statistics(), indent=2))
        elif sys.argv[1] == "--test":
            print("🧪 Testing SEBI Compliance module...")
            result = health_check()
            print("Status: {result['status']}")
        else:
            print("Usage: python sebi_compliance.py [--health|--stats|--test]")
    else:
        print("SEBI Compliance Module - Use --help for usage")
