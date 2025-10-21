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

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.0.0/24", "10.0.1.0/24"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.100.0/24", "10.0.101.0/24"]
}

variable "single_nat_gateway" {
  description = "Use single NAT Gateway for cost optimization"
  type        = bool
  default     = true
}

# DynamoDB Configuration
variable "dynamodb_encryption_enabled" {
  description = "Enable encryption for DynamoDB table"
  type        = bool
  default     = true
}

variable "dynamodb_point_in_time_recovery" {
  description = "Enable point-in-time recovery for DynamoDB table"
  type        = bool
  default     = true
}

variable "dynamodb_deletion_protection" {
  description = "Enable deletion protection for DynamoDB table"
  type        = bool
  default     = false
}