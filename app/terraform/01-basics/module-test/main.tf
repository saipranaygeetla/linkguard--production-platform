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

module "project_info" {
  source = "../modules/project-info"

  project_name = "LinkGuard"
  environment  = "development"
}

output "project_file" {
  value = module.project_info.file_path
}