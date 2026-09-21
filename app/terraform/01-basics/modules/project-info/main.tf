resource "local_file" "info" {
  filename = "${path.module}/project-info.txt"

  content = <<-EOT
    Project: ${var.project_name}
    Environment: ${var.environment}
    Managed by: Terraform
  EOT
}