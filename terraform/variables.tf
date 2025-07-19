# Risk Compliance Terraform Variables

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "bigquery_location" {
  description = "BigQuery dataset location"
  type        = string
  default     = "US"
}

variable "timezone" {
  description = "Timezone for scheduled jobs"
  type        = string
  default     = "America/New_York"
}

# Cloud Run Configuration
variable "cloud_run_cpu" {
  description = "CPU allocation for Cloud Run"
  type        = string
  default     = "2"
}

variable "cloud_run_memory" {
  description = "Memory allocation for Cloud Run"
  type        = string
  default     = "4Gi"
}

variable "min_instances" {
  description = "Minimum number of Cloud Run instances"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 5
}

# Scheduling Configuration
variable "risk_assessment_schedule" {
  description = "Cron schedule for daily risk assessment"
  type        = string
  default     = "0 18 * * 1-5"  # 6 PM EST on weekdays
}

variable "compliance_reporting_schedule" {
  description = "Cron schedule for compliance reporting"
  type        = string
  default     = "0 20 * * 1-5"  # 8 PM EST on weekdays
}

# Monitoring Configuration
variable "notification_channels" {
  description = "List of notification channel IDs for alerts"
  type        = list(string)
  default     = []
}

# Budget Configuration
variable "enable_budget_alerts" {
  description = "Enable budget alerts"
  type        = bool
  default     = true
}

variable "billing_account_id" {
  description = "Billing account ID for budget alerts"
  type        = string
  default     = ""
}

variable "monthly_budget" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 300
}

# Security Configuration
variable "allowed_ingress" {
  description = "Allowed ingress configuration for Cloud Run"
  type        = string
  default     = "INGRESS_TRAFFIC_INTERNAL_ONLY"
}

variable "vpc_connector" {
  description = "VPC connector for private networking"
  type        = string
  default     = ""
}

# Performance Configuration
variable "concurrency" {
  description = "Maximum concurrent requests per instance"
  type        = number
  default     = 100
}

variable "execution_environment" {
  description = "Execution environment (EXECUTION_ENVIRONMENT_GEN1 or EXECUTION_ENVIRONMENT_GEN2)"
  type        = string
  default     = "EXECUTION_ENVIRONMENT_GEN2"
}

# Risk Management Configuration
variable "risk_limits" {
  description = "Risk limit thresholds"
  type = object({
    max_var_95         = number  # Value at Risk 95%
    max_expected_shortfall = number
    max_leverage       = number
    max_concentration  = number
  })
  default = {
    max_var_95         = 50000   # $50K daily VaR
    max_expected_shortfall = 75000
    max_leverage       = 2.0
    max_concentration  = 0.1     # 10% max single position
  }
}

# Compliance Configuration
variable "regulatory_frameworks" {
  description = "List of regulatory frameworks to comply with"
  type        = list(string)
  default     = ["SEC", "FINRA", "CFTC", "SOX", "GDPR"]
}

variable "audit_retention_days" {
  description = "Audit log retention period in days"
  type        = number
  default     = 2555  # ~7 years for financial records
}

variable "compliance_reporting_frequency" {
  description = "Frequency of compliance reporting"
  type        = string
  default     = "daily"
}

# Data Configuration
variable "data_classification_levels" {
  description = "Data classification levels for compliance"
  type        = list(string)
  default     = ["public", "internal", "confidential", "restricted"]
}

variable "data_retention_policies" {
  description = "Data retention policies by type"
  type = object({
    trade_data      = number
    personal_data   = number
    audit_logs      = number
    risk_reports    = number
  })
  default = {
    trade_data      = 2555  # 7 years
    personal_data   = 2190  # 6 years
    audit_logs      = 2555  # 7 years
    risk_reports    = 1825  # 5 years
  }
}

# Alert Configuration
variable "compliance_alert_thresholds" {
  description = "Compliance alert threshold configurations"
  type = object({
    risk_limit_breach     = number
    audit_failure_rate    = number
    data_quality_score    = number
    regulatory_deadline   = number  # days before deadline
  })
  default = {
    risk_limit_breach     = 0.95  # 95% of limit
    audit_failure_rate    = 0.05  # 5% failure rate
    data_quality_score    = 0.95  # 95% quality score
    regulatory_deadline   = 7     # 7 days warning
  }
}

# External Integration Configuration
variable "external_services" {
  description = "External service configurations"
  type = object({
    risk_data_vendor     = string
    compliance_platform  = string
    audit_service        = string
  })
  default = {
    risk_data_vendor     = "bloomberg"
    compliance_platform  = "charles_river"
    audit_service        = "protiviti"
  }
}

# Reporting Configuration
variable "report_formats" {
  description = "Supported report output formats"
  type        = list(string)
  default     = ["pdf", "excel", "json", "csv"]
}

variable "report_distribution" {
  description = "Report distribution configuration"
  type = object({
    email_recipients = list(string)
    sftp_endpoints  = list(string)
    api_webhooks    = list(string)
  })
  default = {
    email_recipients = []
    sftp_endpoints  = []
    api_webhooks    = []
  }
}
