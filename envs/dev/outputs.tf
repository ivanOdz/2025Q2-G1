# Outputs del ambiente

# Events module outputs
output "sns_topic_arn" {
  description = "ARN of the SNS notifications topic"
  value       = aws_sns_topic.notifications.arn
}

output "sqs_queue_arn" {
  description = "ARN of the SQS notifications queue"
  value       = aws_sqs_queue.notifications_queue.arn
}

# Storage outputs
output "images_bucket_name" {
  description = "The name/ID of the S3 bucket for images."
  value       = module.images_bucket.bucket_id
}

output "images_bucket_arn" {
  description = "The ARN of the S3 bucket for images."
  value       = module.images_bucket.bucket_arn
}

output "images_bucket_domain_name" {
  description = "The generic domain name of the S3 bucket."
  value       = module.images_bucket.bucket_domain_name
}

# Frontend outputs
output "frontend_bucket_name" {
  description = "The name/ID of the S3 bucket for frontend."
  value       = module.frontend_bucket.bucket_id
}

output "frontend_website_url" {
  description = "URL del sitio web estático (HTTP)."
  value       = module.frontend_bucket.website_configuration.website_endpoint
}