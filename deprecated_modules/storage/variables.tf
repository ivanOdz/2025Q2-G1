variable "project_name" {
  description = "Project name used as prefix for bucket names"
  type        = string
}
variable "tags" {
  description = "Common tags for all storage resources"
  type        = map(string)
}