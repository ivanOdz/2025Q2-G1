variable "project_name" {
  description = "Project name to be used as a prefix for all resources."
  type        = string
  default     = "tp-cloud"
}

variable "aws_region" {
  description = "AWS region where resources will be created."
  type        = string
  default     = "us-east-1"
}

variable "lambda_handlers" {
  description = "Map of Lambda function handlers for different functionalities."
  type        = map(string)
  default = {
    "packages"      = "packages_handler"
    "tracks"        = "tracks_handler"
    "address"       = "address_handler"
    "depots"        = "depots_handler"
    "images"        = "images_handler"
    "notifications" = "notifications_handler"
  }
}