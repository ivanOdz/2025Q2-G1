# Variables del stack del entorno dev
variable "env" {
  description = "Environment name (dev|prod|...)"
  type        = string
}

variable "project_name" {
  description = "Project name to be used as a prefix for all resources."
  type        = string
}

variable "aws_region" {
  description = "AWS region where resources will be created."
  type        = string
}

variable "code_bucket" {
  description = "S3 bucket (with versioning) where Lambda ZIP artifacts are published."
  type        = string
}

variable "extra_tags" {
  description = "Extra tags to attach to all resources."
  type        = map(string)
  default     = {}
}

variable "lambda_handlers" {
  description = "Map<lambda_key, python_module> (el handler real será <python_module>.main)"
  type        = map(string)
  default = {
    packages      = "packages_handler"
    tracks        = "tracks_handler"
    address       = "address_handler"
    depots        = "depots_handler"
    images        = "images_handler"
    notifications = "notifications_handler"
  }
}
