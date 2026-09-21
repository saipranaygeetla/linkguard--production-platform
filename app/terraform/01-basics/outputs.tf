output "project_file" {
  description = "Path of the generated project file"
  value       = local_file.project_info.filename
}

output "existing_project_content" {
  description = "Content read from the existing project file"
  value       = data.local_file.existing_project.content
}