# Risk Compliance Terraform Outputs

output "service_account_email" {
  description = "Email of the Risk Compliance service account"
  value       = google_service_account.risk_compliance.email
}

output "cloud_run_service_url" {
  description = "URL of the Risk Compliance Cloud Run service"
  value       = google_cloud_run_v2_service.risk_compliance.uri
}

output "cloud_run_service_name" {
  description = "Name of the Risk Compliance Cloud Run service"
  value       = google_cloud_run_v2_service.risk_compliance.name
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository for Docker images"
  value       = google_artifact_registry_repository.risk_compliance.name
}

output "artifact_registry_url" {
  description = "Artifact Registry repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.risk_compliance.repository_id}"
}

output "bigquery_datasets" {
  description = "BigQuery dataset IDs"
  value = {
    compliance_data = google_bigquery_dataset.compliance_data.dataset_id
    audit_logs     = google_bigquery_dataset.audit_logs.dataset_id
  }
}

output "bigquery_dataset_location" {
  description = "BigQuery dataset location"
  value       = google_bigquery_dataset.compliance_data.location
}

output "scheduler_job_names" {
  description = "Names of Cloud Scheduler jobs"
  value = [
    google_cloud_scheduler_job.daily_risk_assessment.name,
    google_cloud_scheduler_job.compliance_reporting.name
  ]
}

output "monitoring_alert_policy_name" {
  description = "Name of the monitoring alert policy"
  value       = google_monitoring_alert_policy.compliance_violations.name
}

output "budget_name" {
  description = "Name of the budget alert (if enabled)"
  value       = var.enable_budget_alerts ? google_billing_budget.risk_compliance_budget[0].display_name : null
}

# Configuration outputs for other services
output "risk_compliance_config" {
  description = "Risk Compliance configuration for other services"
  value = {
    service_url                   = google_cloud_run_v2_service.risk_compliance.uri
    service_account_email         = google_service_account.risk_compliance.email
    compliance_dataset_id         = google_bigquery_dataset.compliance_data.dataset_id
    audit_logs_dataset_id        = google_bigquery_dataset.audit_logs.dataset_id
    risk_assessment_schedule     = var.risk_assessment_schedule
    compliance_reporting_schedule = var.compliance_reporting_schedule
  }
  sensitive = false
}

# Deployment information
output "deployment_info" {
  description = "Deployment information and next steps"
  value = {
    docker_image_url = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.risk_compliance.repository_id}/risk-compliance:latest"
    health_check_url = "${google_cloud_run_v2_service.risk_compliance.uri}/health"
    risk_assessment_endpoint = "${google_cloud_run_v2_service.risk_compliance.uri}/assess-risk"
    compliance_reports_endpoint = "${google_cloud_run_v2_service.risk_compliance.uri}/generate-reports"
    audit_endpoint = "${google_cloud_run_v2_service.risk_compliance.uri}/audit"
  }
}
