"""
Comprehensive Audit Trail System for AI Trading Machine

Implements enterprise-grade audit trail with:
- Trade decision logging with full context
- Signal generation audit trail
- Model inference tracking
- Configuration change tracking
- User action logging
- SEBI compliance reporting
"""

import hashlib
import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Audit event types for categorization"""

    TRADE_EXECUTION = "trade_execution"
    SIGNAL_GENERATION = "signal_generation"
    MODEL_INFERENCE = "model_inference"
    CONFIGURATION_CHANGE = "configuration_change"
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"
    DATA_ACCESS = "data_access"
    RISK_OVERRIDE = "risk_override"
    COMPLIANCE_CHECK = "compliance_check"
    ERROR_EVENT = "error_event"


class AuditSeverity(Enum):
    """Audit event severity levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class AuditEvent:
    """Structured audit event"""

    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[str]
    session_id: Optional[str]
    component: str
    action: str
    description: str
    context: dict[str, Any]
    input_data: Optional[dict[str, Any]]
    output_data: Optional[dict[str, Any]]
    execution_time_ms: Optional[float]
    error_details: Optional[dict[str, Any]]
    compliance_tags: list[str]
    data_sensitivity: str  # public, internal, confidential, restricted
    checksum: str


class AuditTrail:
    """
    Enterprise-grade audit trail system with comprehensive logging,
    immutable records, and compliance reporting
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize audit trail system"""
        self.config = self._load_config(config_path)
        self.session_id = str(uuid.uuid4())
        self.audit_buffer = []
        self._setup_storage()

    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load audit trail configuration"""
        default_config = {
            "storage": {
                "primary_store": "bigquery",
                "backup_store": "local_files",
                "table_name": "ai_trading_machine.audit.audit_trail",
                "local_path": "logs/audit_trail/",
                "batch_size": 100,
                "flush_interval": 300,  # 5 minutes
            },
            "retention": {
                "trade_events": "7_years",  # SEBI requirement
                "system_events": "2_years",
                "user_actions": "5_years",
                "error_events": "3_years",
            },
            "compliance": {
                "sebi_enabled": True,
                "data_protection_enabled": True,
                "encryption_enabled": True,
                "anonymization_rules": {
                    "user_data": "hash",
                    "financial_data": "encrypt",
                    "system_data": "none",
                },
            },
            "alerts": {
                "critical_events_immediate": True,
                "compliance_violations": True,
                "unauthorized_access": True,
                "data_integrity_issues": True,
            },
            "performance": {
                "async_logging": True,
                "compression_enabled": True,
                "indexing_strategy": "time_based",
            },
        }

        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    def _setup_storage(self):
        """Setup audit trail storage systems"""
        try:
            # Create local storage directory
            local_path = Path(self.config["storage"]["local_path"])
            local_path.mkdir(parents=True, exist_ok=True)

            # Initialize BigQuery table if needed
            if self.config["storage"]["primary_store"] == "bigquery":
                self._ensure_bigquery_table()

            logger.info("Audit trail storage initialized successfully")

        except Exception as e:
            logger.error("Error setting up audit trail storage: {e}")

    def _ensure_bigquery_table(self):
        """Ensure BigQuery audit table exists with proper schema"""
        try:
            # Import BigQuery here to handle optional dependency
            from google.cloud import bigquery

            client = bigquery.Client()
            table_id = self.config["storage"]["table_name"]

            # Define audit table schema
            schema = [
                bigquery.SchemaField("event_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
                bigquery.SchemaField("event_type", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("severity", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("user_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("session_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("component", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("action", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("description", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("context", "JSON", mode="NULLABLE"),
                bigquery.SchemaField("input_data", "JSON", mode="NULLABLE"),
                bigquery.SchemaField("output_data", "JSON", mode="NULLABLE"),
                bigquery.SchemaField("execution_time_ms", "FLOAT", mode="NULLABLE"),
                bigquery.SchemaField("error_details", "JSON", mode="NULLABLE"),
                bigquery.SchemaField("compliance_tags", "STRING", mode="REPEATED"),
                bigquery.SchemaField("data_sensitivity", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("checksum", "STRING", mode="REQUIRED"),
                bigquery.SchemaField(
                    "ingestion_timestamp", "TIMESTAMP", mode="REQUIRED"
                ),
            ]

            table = bigquery.Table(table_id, schema=schema)
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY, field="timestamp"
            )

            # Create table if it doesn't exist
            try:
                client.get_table(table_id)
                logger.info("Audit table {table_id} already exists")
            except Exception:
                table = client.create_table(table)
                logger.info("Created audit table {table_id}")

        except ImportError:
            logger.warning("BigQuery not available, using local storage only")
        except Exception as e:
            logger.error("Error setting up BigQuery audit table: {e}")

    def log_trade_execution(
        self, trade_data: dict[str, Any], user_id: Optional[str] = None
    ) -> str:
        """Log trade execution with full audit trail"""
        return self._create_audit_event(
            event_type=AuditEventType.TRADE_EXECUTION,
            severity=AuditSeverity.HIGH,
            user_id=user_id,
            component="trading_engine",
            action="execute_trade",
            description="Trade executed: {trade_data.get('symbol')} "
            "{trade_data.get('quantity')} @ {trade_data.get('price')}",
            context={
                "strategy": trade_data.get("strategy"),
                "order_type": trade_data.get("order_type"),
                "market_conditions": trade_data.get("market_conditions"),
            },
            input_data=trade_data,
            compliance_tags=["sebi_trade_log", "transaction_record"],
            data_sensitivity="confidential",
        )

    def log_signal_generation(
        self,
        signal_data: dict[str, Any],
        model_info: dict[str, Any],
        execution_time: float,
    ) -> str:
        """Log signal generation with model details"""
        return self._create_audit_event(
            event_type=AuditEventType.SIGNAL_GENERATION,
            severity=AuditSeverity.MEDIUM,
            component="signal_generator",
            action="generate_signal",
            description="Signal generated for {signal_data.get('symbol')}: "
            "{signal_data.get('action')} (confidence: {signal_data.get('confidence')})",
            context={
                "model_version": model_info.get("version"),
                "model_type": model_info.get("type"),
                "feature_count": model_info.get("feature_count"),
                "data_quality_score": signal_data.get("data_quality_score"),
            },
            input_data={
                "features": signal_data.get("features", {}),
                "market_data": signal_data.get("market_data", {}),
            },
            output_data={
                "signal": signal_data.get("signal"),
                "confidence": signal_data.get("confidence"),
                "reasoning": signal_data.get("reasoning"),
            },
            execution_time_ms=execution_time,
            compliance_tags=["algorithm_decision", "model_output"],
            data_sensitivity="internal",
        )

    def log_model_inference(
        self,
        model_name: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        execution_time: float,
    ) -> str:
        """Log model inference with full context"""
        return self._create_audit_event(
            event_type=AuditEventType.MODEL_INFERENCE,
            severity=AuditSeverity.INFO,
            component="ml_engine",
            action="model_inference",
            description="Model inference: {model_name}",
            context={
                "model_name": model_name,
                "input_shape": str(len(input_data)),
                "prediction_type": output_data.get("type"),
            },
            input_data=self._sanitize_sensitive_data(input_data),
            output_data=self._sanitize_sensitive_data(output_data),
            execution_time_ms=execution_time,
            compliance_tags=["ml_inference", "algorithm_execution"],
            data_sensitivity="internal",
        )

    def log_configuration_change(
        self,
        component: str,
        old_config: dict[str, Any],
        new_config: dict[str, Any],
        user_id: str,
        reason: str,
    ) -> str:
        """Log configuration changes with di"""
        config_diff = self._calculate_config_diff(old_config, new_config)

        return self._create_audit_event(
            event_type=AuditEventType.CONFIGURATION_CHANGE,
            severity=AuditSeverity.HIGH,
            user_id=user_id,
            component=component,
            action="update_configuration",
            description="Configuration updated for {component}: {reason}",
            context={
                "change_reason": reason,
                "fields_changed": len(config_diff["changed"]),
                "fields_added": len(config_diff["added"]),
                "fields_removed": len(config_diff["removed"]),
            },
            input_data={"config_dif": config_diff},
            compliance_tags=["config_change", "system_modification"],
            data_sensitivity="internal",
        )

    def log_user_action(
        self, user_id: str, action: str, details: dict[str, Any]
    ) -> str:
        """Log user actions for accountability"""
        return self._create_audit_event(
            event_type=AuditEventType.USER_ACTION,
            severity=AuditSeverity.MEDIUM,
            user_id=user_id,
            component="user_interface",
            action=action,
            description="User action: {action}",
            context=details,
            compliance_tags=["user_activity", "access_log"],
            data_sensitivity="internal",
        )

    def log_compliance_check(
        self, check_type: str, result: dict[str, Any], violations: list[dict[str, Any]]
    ) -> str:
        """Log compliance checks and violations"""
        severity = AuditSeverity.CRITICAL if violations else AuditSeverity.INFO

        return self._create_audit_event(
            event_type=AuditEventType.COMPLIANCE_CHECK,
            severity=severity,
            component="compliance_engine",
            action=check_type,
            description="Compliance check: {check_type} "
            "({'FAILED' if violations else 'PASSED'})",
            context={
                "check_type": check_type,
                "violations_count": len(violations),
                "compliance_score": result.get("score"),
            },
            output_data={"result": result, "violations": violations},
            compliance_tags=["sebi_compliance", "regulatory_check"],
            data_sensitivity="confidential",
        )

    def log_error_event(
        self, component: str, error: Exception, context: dict[str, Any]
    ) -> str:
        """Log error events with full context"""
        return self._create_audit_event(
            event_type=AuditEventType.ERROR_EVENT,
            severity=AuditSeverity.HIGH,
            component=component,
            action="error_occurred",
            description="Error in {component}: {str(error)}",
            context=context,
            error_details={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "stack_trace": (
                    str(error.__traceback__) if error.__traceback__ else None
                ),
            },
            compliance_tags=["error_log", "system_fault"],
            data_sensitivity="internal",
        )

    def _create_audit_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        component: str,
        action: str,
        description: str,
        context: Optional[dict[str, Any]] = None,
        input_data: Optional[dict[str, Any]] = None,
        output_data: Optional[dict[str, Any]] = None,
        execution_time_ms: Optional[float] = None,
        error_details: Optional[dict[str, Any]] = None,
        compliance_tags: Optional[list[str]] = None,
        data_sensitivity: str = "internal",
        user_id: Optional[str] = None,
    ) -> str:
        """Create and store audit event"""

        event_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        # Create audit event
        event = AuditEvent(
            event_id=event_id,
            timestamp=timestamp,
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            session_id=self.session_id,
            component=component,
            action=action,
            description=description,
            context=context or {},
            input_data=input_data,
            output_data=output_data,
            execution_time_ms=execution_time_ms,
            error_details=error_details,
            compliance_tags=compliance_tags or [],
            data_sensitivity=data_sensitivity,
            checksum="",  # Will be calculated
        )

        # Calculate checksum for integrity
        event.checksum = self._calculate_checksum(event)

        # Store event
        self._store_event(event)

        # Handle critical events immediately
        if severity == AuditSeverity.CRITICAL:
            self._handle_critical_event(event)

        logger.debug("Audit event created: {event_id}")
        return event_id

    def _store_event(self, event: AuditEvent):
        """Store audit event in configured storage"""
        try:
            # Add to buffer for batch processing
            self.audit_buffer.append(event)

            # Flush buffer if it's full
            if len(self.audit_buffer) >= self.config["storage"]["batch_size"]:
                self._flush_buffer()

            # Store locally immediately for critical events
            if event.severity == AuditSeverity.CRITICAL:
                self._store_local(event)

        except Exception as e:
            logger.error("Error storing audit event: {e}")
            # Fallback to local storage
            self._store_local(event)

    def _flush_buffer(self):
        """Flush audit buffer to primary storage"""
        if not self.audit_buffer:
            return

        try:
            if self.config["storage"]["primary_store"] == "bigquery":
                self._store_bigquery_batch(self.audit_buffer)
            else:
                self._store_local_batch(self.audit_buffer)

            # Clear buffer after successful storage
            self.audit_buffer.clear()

        except Exception as e:
            logger.error("Error flushing audit buffer: {e}")
            # Fallback to local storage
            self._store_local_batch(self.audit_buffer)
            self.audit_buffer.clear()

    def _store_bigquery_batch(self, events: list[AuditEvent]):
        """Store events batch to BigQuery"""
        try:
            from google.cloud import bigquery

            client = bigquery.Client()
            table_id = self.config["storage"]["table_name"]

            # Convert events to BigQuery rows
            rows = []
            for event in events:
                row = asdict(event)
                row["timestamp"] = event.timestamp.isoformat()
                row["event_type"] = event.event_type.value
                row["severity"] = event.severity.value
                row["ingestion_timestamp"] = datetime.now(timezone.utc).isoformat()
                rows.append(row)

            # Insert rows
            errors = client.insert_rows_json(table_id, rows)

            if errors:
                logger.error("BigQuery insert errors: {errors}")
                # Fallback to local storage
                self._store_local_batch(events)
            else:
                logger.debug("Stored {len(events)} audit events to BigQuery")

        except Exception as e:
            logger.error("Error storing to BigQuery: {e}")
            # Fallback to local storage
            self._store_local_batch(events)

    def _store_local_batch(self, events: list[AuditEvent]):
        """Store events batch to local files"""
        try:
            local_path = Path(self.config["storage"]["local_path"])
            date_str = datetime.now().strftime("%Y%m%d")
            file_path = local_path / "audit_trail_{date_str}.jsonl"

            with open(file_path, "a") as f:
                for event in events:
                    event_dict = asdict(event)
                    event_dict["timestamp"] = event.timestamp.isoformat()
                    event_dict["event_type"] = event.event_type.value
                    event_dict["severity"] = event.severity.value
                    f.write(json.dumps(event_dict) + "\n")

            logger.debug("Stored {len(events)} audit events locally")

        except Exception as e:
            logger.error("Error storing audit events locally: {e}")

    def _store_local(self, event: AuditEvent):
        """Store single event locally"""
        self._store_local_batch([event])

    def _calculate_checksum(self, event: AuditEvent) -> str:
        """Calculate checksum for audit event integrity"""
        # Create deterministic string representation
        event_copy = asdict(event)
        event_copy.pop("checksum", None)  # Remove checksum field

        # Convert to sorted JSON string
        event_str = json.dumps(event_copy, sort_keys=True, default=str)

        # Calculate SHA-256 hash
        return hashlib.sha256(event_str.encode()).hexdigest()

    def _sanitize_sensitive_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Sanitize sensitive data based on configuration"""
        if not self.config["compliance"]["data_protection_enabled"]:
            return data

        sanitized = data.copy()

        # Apply anonymization rules
        for field, rule in self.config["compliance"]["anonymization_rules"].items():
            if field in sanitized:
                if rule == "hash":
                    sanitized[field] = hashlib.sha256(
                        str(sanitized[field]).encode()
                    ).hexdigest()[:16]
                elif rule == "encrypt":
                    # In production, use proper encryption
                    sanitized[field] = "***ENCRYPTED***"
                elif rule == "remove":
                    sanitized.pop(field, None)

        return sanitized

    def _calculate_config_diff(
        self, old_config: dict[str, Any], new_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate configuration differences"""
        diff = {"changed": {}, "added": {}, "removed": {}}

        # Find changed and removed fields
        for key, old_value in old_config.items():
            if key in new_config:
                if old_value != new_config[key]:
                    diff["changed"][key] = {"old": old_value, "new": new_config[key]}
            else:
                diff["removed"][key] = old_value

        # Find added fields
        for key, new_value in new_config.items():
            if key not in old_config:
                diff["added"][key] = new_value

        return diff

    def _handle_critical_event(self, event: AuditEvent):
        """Handle critical events with immediate alerts"""
        try:
            if self.config["alerts"]["critical_events_immediate"]:
                # In production, integrate with alerting system
                logger.critical("CRITICAL AUDIT EVENT: {event.description}")

                # Store immediately to ensure persistence
                self._store_local(event)

        except Exception as e:
            logger.error("Error handling critical audit event: {e}")

    def get_audit_trail(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_types: Optional[list[AuditEventType]] = None,
        user_id: Optional[str] = None,
        component: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
    ) -> list[dict[str, Any]]:
        """Retrieve audit trail with filtering"""
        try:
            # Query BigQuery if available
            if self.config["storage"]["primary_store"] == "bigquery":
                return self._query_bigquery_audit_trail(
                    start_date, end_date, event_types, user_id, component, severity
                )
            else:
                return self._query_local_audit_trail(
                    start_date, end_date, event_types, user_id, component, severity
                )

        except Exception as e:
            logger.error("Error retrieving audit trail: {e}")
            return []

    def _query_bigquery_audit_trail(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        event_types: Optional[list[AuditEventType]],
        user_id: Optional[str],
        component: Optional[str],
        severity: Optional[AuditSeverity],
    ) -> list[dict[str, Any]]:
        """Query audit trail from BigQuery"""
        try:
            from google.cloud import bigquery

            client = bigquery.Client()

            # Build query
            query = "SELECT * FROM `{self.config['storage']['table_name']}` WHERE 1=1"

            if start_date:
                query += " AND timestamp >= '{start_date.isoformat()}'"
            if end_date:
                query += " AND timestamp <= '{end_date.isoformat()}'"
            if event_types:
                types_str = "', '".join([et.value for et in event_types])
                query += " AND event_type IN ('{types_str}')"
            if user_id:
                query += " AND user_id = '{user_id}'"
            if component:
                query += " AND component = '{component}'"
            if severity:
                query += " AND severity = '{severity.value}'"

            query += " ORDER BY timestamp DESC LIMIT 1000"

            # Execute query
            results = client.query(query)
            return [dict(row) for row in results]

        except Exception as e:
            logger.error("Error querying BigQuery audit trail: {e}")
            return []

    def _query_local_audit_trail(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        event_types: Optional[list[AuditEventType]],
        user_id: Optional[str],
        component: Optional[str],
        severity: Optional[AuditSeverity],
    ) -> list[dict[str, Any]]:
        """Query audit trail from local files"""
        try:
            local_path = Path(self.config["storage"]["local_path"])
            events = []

            # Read all local audit files
            for file_path in local_path.glob("audit_trail_*.jsonl"):
                with open(file_path) as f:
                    for line in f:
                        try:
                            event = json.loads(line.strip())

                            # Apply filters
                            if (
                                start_date
                                and datetime.fromisoformat(event["timestamp"])
                                < start_date
                            ):
                                continue
                            if (
                                end_date
                                and datetime.fromisoformat(event["timestamp"])
                                > end_date
                            ):
                                continue
                            if event_types and event["event_type"] not in [
                                et.value for et in event_types
                            ]:
                                continue
                            if user_id and event.get("user_id") != user_id:
                                continue
                            if component and event.get("component") != component:
                                continue
                            if severity and event.get("severity") != severity.value:
                                continue

                            events.append(event)

                        except json.JSONDecodeError:
                            continue

            # Sort by timestamp (newest first) and limit
            events.sort(key=lambda x: x["timestamp"], reverse=True)
            return events[:1000]

        except Exception as e:
            logger.error("Error querying local audit trail: {e}")
            return []

    def generate_compliance_report(
        self, start_date: datetime, end_date: datetime, report_type: str = "sebi"
    ) -> dict[str, Any]:
        """Generate compliance report for regulatory requirements"""
        try:
            # Get relevant audit events
            compliance_events = self.get_audit_trail(
                start_date=start_date,
                end_date=end_date,
                event_types=[
                    AuditEventType.TRADE_EXECUTION,
                    AuditEventType.COMPLIANCE_CHECK,
                    AuditEventType.RISK_OVERRIDE,
                ],
            )

            report = {
                "report_id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc),
                "report_type": report_type,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "summary": {
                    "total_events": len(compliance_events),
                    "trade_executions": 0,
                    "compliance_checks": 0,
                    "violations": 0,
                    "risk_overrides": 0,
                },
                "events": compliance_events,
                "violations": [],
                "recommendations": [],
            }

            # Analyze events
            for event in compliance_events:
                if event["event_type"] == AuditEventType.TRADE_EXECUTION.value:
                    report["summary"]["trade_executions"] += 1
                elif event["event_type"] == AuditEventType.COMPLIANCE_CHECK.value:
                    report["summary"]["compliance_checks"] += 1
                    if event.get("output_data", {}).get("violations"):
                        report["summary"]["violations"] += 1
                        report["violations"].extend(event["output_data"]["violations"])
                elif event["event_type"] == AuditEventType.RISK_OVERRIDE.value:
                    report["summary"]["risk_overrides"] += 1

            # Generate recommendations
            if report["summary"]["violations"] > 0:
                report["recommendations"].append(
                    "Investigate and address compliance violations"
                )
            if report["summary"]["risk_overrides"] > 10:
                report["recommendations"].append("Review risk override procedures")

            logger.info("Generated compliance report: {report['report_id']}")
            return report

        except Exception as e:
            logger.error("Error generating compliance report: {e}")
            return {"error": str(e)}

    def verify_audit_integrity(
        self, start_date: datetime, end_date: datetime
    ) -> dict[str, Any]:
        """Verify audit trail integrity using checksums"""
        try:
            events = self.get_audit_trail(start_date=start_date, end_date=end_date)

            integrity_report = {
                "timestamp": datetime.now(timezone.utc),
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "total_events": len(events),
                "verified_events": 0,
                "corrupted_events": 0,
                "missing_checksums": 0,
                "integrity_score": 0.0,
                "corrupted_event_ids": [],
            }

            # Verify each event
            for event in events:
                if "checksum" not in event or not event["checksum"]:
                    integrity_report["missing_checksums"] += 1
                    continue

                # Reconstruct event and verify checksum
                event_copy = event.copy()
                original_checksum = event_copy.pop("checksum")
                event_copy.pop(
                    "ingestion_timestamp", None
                )  # Remove auto-generated fields

                # Calculate expected checksum
                event_str = json.dumps(event_copy, sort_keys=True, default=str)
                expected_checksum = hashlib.sha256(event_str.encode()).hexdigest()

                if original_checksum == expected_checksum:
                    integrity_report["verified_events"] += 1
                else:
                    integrity_report["corrupted_events"] += 1
                    integrity_report["corrupted_event_ids"].append(event["event_id"])

            # Calculate integrity score
            if integrity_report["total_events"] > 0:
                integrity_report["integrity_score"] = (
                    integrity_report["verified_events"]
                    / integrity_report["total_events"]
                )

            logger.info(
                "Audit integrity verification completed. "
                "Score: {integrity_report['integrity_score']:.3f}"
            )

            return integrity_report

        except Exception as e:
            logger.error("Error verifying audit integrity: {e}")
            return {"error": str(e)}

    def __del__(self):
        """Flush remaining events on cleanup"""
        try:
            if hasattr(self, "audit_buffer") and self.audit_buffer:
                self._flush_buffer()
        except Exception:
            pass


# Factory function for easy initialization
def create_audit_trail(config_path: Optional[str] = None) -> AuditTrail:
    """Create and return a configured audit trail system"""
    return AuditTrail(config_path)


if __name__ == "__main__":
    # Example usage
    audit = create_audit_trail()

    # Log a sample trade
    trade_id = audit.log_trade_execution(
        {
            "symbol": "RELIANCE.NS",
            "quantity": 100,
            "price": 2500.0,
            "order_type": "MARKET",
            "strategy": "momentum_strategy",
        },
        user_id="trader_001",
    )

    print("Trade logged with audit ID: {trade_id}")
