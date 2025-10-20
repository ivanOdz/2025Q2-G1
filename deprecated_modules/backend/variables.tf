variable "project_name" { type = string }
variable "lambda_subnet_ids" { type = list(string) }
variable "dynamodb_table_arn" { type = string }
variable "sns_topic_arn" { type = string }
variable "lambda_handlers_map" { type = map(string) }
variable "tags" { type = map(string) }
variable "vpc_id" {
  description = "VPC ID where lambdas will be deployed"
  type        = string
}
variable "images_bucket_name" {
  description = "Name of the S3 bucket for image uploads"
  type        = string
}
variable "images_bucket_arn" {
  description = "ARN of the S3 bucket for image uploads"
  type        = string
}