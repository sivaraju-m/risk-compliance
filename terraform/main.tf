# Risk Compliance Terraform Infrastructure
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  
  backend "gcs" {
    bucket = "ai-trading-terraform-state"
    prefix = "risk-compliance"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Artifact Registry for Docker images
resource "google_artifact_registry_repository" "risk_compliance" {
  location      = var.region
  repository_id = "risk-compliance"
  description   = "Risk Compliance Docker repository"
  format        = "DOCKER"

  labels = {
    component   = "risk-compliance"
    environment = var.environment
    managed-by  = "terraform"
  }
}

# Service Account for Risk Compliance
resource "google_service_account" "risk_compliance" {
  account_id   = "risk-compliance-sa"
  display_name = "Risk Compliance Service Account"
  description  = "Service account for Risk Compliance service"
}

# IAM bindings for service account
resource "google_project_iam_member" "risk_compliance_bigquery_user" {
  project = var.project_id
  role    = "roles/bigquery.user"
  member  = "serviceAccount:${google_service_account.risk_compliance.email}"
}

resource "google_project_iam_member" "risk_compliance_bigquery_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.risk_compliance.email}"
}

resource "google_project_iam_member" "risk_compliance_storage_object_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.risk_compliance.email}"
}

resource "google_project_iam_member" "risk_compliance_monitoring_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.risk_compliance.email}"
}

resource "google_project_iam_member" "risk_compliance_logging_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.risk_compliance.email}"
}

# Cloud Run service
resource "google_cloud_run_v2_service" "risk_compliance" {
  name     = "risk-compliance"
  location = var.region
  
  deletion_protection = false

  template {
    service_account = google_service_account.risk_compliance.email
    
    timeout = "3600s"
    
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/risk-compliance/risk-compliance:latest"
      
      ports {
        container_port = 8080
      }
      
      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }
      
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      
      env {
        name  = "REGION"
        value = var.region
      }

      resources {
        limits = {
          cpu    = var.cloud_run_cpu
          memory = var.cloud_run_memory
        }
      }
      
      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 30
        timeout_seconds       = 10
        period_seconds        = 10
        failure_threshold     = 3
      }
      
      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 60
        timeout_seconds       = 10
        period_seconds        = 30
        failure_threshold     = 3
      }
    }
    
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }
    
    labels = {
      component   = "risk-compliance"
      environment = var.environment
      managed-by  = "terraform"
    }
  }
  
  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  depends_on = [google_artifact_registry_repository.risk_compliance]
}

# IAM policy for Cloud Run service
resource "google_cloud_run_service_iam_member" "risk_compliance_invoker" {
  service  = google_cloud_run_v2_service.risk_compliance.name
  location = google_cloud_run_v2_service.risk_compliance.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.risk_compliance.email}"
}

# BigQuery dataset for compliance data
resource "google_bigquery_dataset" "compliance_data" {
  dataset_id    = "compliance_data"
  friendly_name = "Compliance Data"
  description   = "Dataset for storing compliance reports and risk assessments"
  location      = var.bigquery_location

  labels = {
    component   = "risk-compliance"
    environment = var.environment
    managed-by  = "terraform"
  }

  delete_contents_on_destroy = false

  access {
    role          = "OWNER"
    user_by_email = google_service_account.risk_compliance.email
  }
}

# BigQuery dataset for audit logs
resource "google_bigquery_dataset" "audit_logs" {
  dataset_id    = "audit_logs"
  friendly_name = "Audit Logs"
  description   = "Dataset for storing audit logs and compliance tracking"
  location      = var.bigquery_location

  labels = {
    component   = "risk-compliance"
    environment = var.environment
    managed-by  = "terraform"
  }

  delete_contents_on_destroy = false

  access {
    role          = "OWNER"
    user_by_email = google_service_account.risk_compliance.email
  }
}

# Cloud Scheduler job for daily risk assessment
resource "google_cloud_scheduler_job" "daily_risk_assessment" {
  name        = "daily-risk-assessment-job"
  description = "Daily risk assessment and reporting"
  schedule    = var.risk_assessment_schedule
  time_zone   = var.timezone
  region      = var.region

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.risk_compliance.uri}/assess-risk"
    
    oidc_token {
      service_account_email = google_service_account.risk_compliance.email
    }
    
    headers = {
      "Content-Type" = "application/json"
    }
    
    body = base64encode(jsonencode({
      assessment_type = "daily_comprehensive"
      include_portfolio = true
      include_market_risk = true
    }))
  }
}

# Cloud Scheduler job for compliance reporting
resource "google_cloud_scheduler_job" "compliance_reporting" {
  name        = "compliance-reporting-job"
  description = "Generate compliance reports"
  schedule    = var.compliance_reporting_schedule
  time_zone   = var.timezone
  region      = var.region

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.risk_compliance.uri}/generate-reports"
    
    oidc_token {
      service_account_email = google_service_account.risk_compliance.email
    }
    
    headers = {
      "Content-Type" = "application/json"
    }
    
    body = base64encode(jsonencode({
      report_type = "regulatory_compliance"
      period = "daily"
    }))
  }
}

# Monitoring alert policy for compliance violations
resource "google_monitoring_alert_policy" "compliance_violations" {
  display_name = "Compliance Violations"
  combiner     = "OR"
  
  conditions {
    display_name = "Risk Compliance Service Errors"
    
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"risk-compliance\""
      duration        = "300s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0.01
      
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_MEAN"
        group_by_fields = ["resource.labels.service_name"]
      }
    }
  }
  
  notification_channels = var.notification_channels
  
  alert_strategy {
    auto_close = "86400s"
  }
}

# Budget alert for risk compliance costs
resource "google_billing_budget" "risk_compliance_budget" {
  count = var.enable_budget_alerts ? 1 : 0
  
  billing_account = var.billing_account_id
  display_name    = "Risk Compliance Budget"

  budget_filter {
    projects = ["projects/${var.project_id}"]
    labels = {
      component = "risk-compliance"
    }
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.monthly_budget)
    }
  }

  threshold_rules {
    threshold_percent = 0.8
    spend_basis      = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis      = "CURRENT_SPEND"
  }
}
