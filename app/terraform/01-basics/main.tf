terraform {
  required_version = ">= 1.6.0"

  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

provider "local" {}

resource "local_file" "project_info" {
  filename = "${path.module}/project-info.txt"

  content = <<-EOT
    Project: ${var.project_name}
    Environment: ${var.environment}
    Managed by: Terraform
  EOT
}

resource "local_file" "environment_info" {
  filename = "${path.module}/environment.txt"

  content = <<-EOT
    Project file: ${local_file.project_info.filename}
    Environment: ${var.environment}
  EOT
}

data "local_file" "existing_project" {
  filename = "${path.module}/project-info.txt"
}