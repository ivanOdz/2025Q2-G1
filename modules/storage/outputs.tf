output "images_bucket_name" {
  description = "The name/ID of the S3 bucket for images."
  value       = module.images_bucket.s3_bucket_id
}

output "images_bucket_arn" {
  description = "The ARN of the S3 bucket for images."
  value       = module.images_bucket.s3_bucket_arn
}

output "images_bucket_domain_name" {
  description = "The generic domain name of the S3 bucket."
  value       = module.images_bucket.s3_bucket_bucket_domain_name 
}