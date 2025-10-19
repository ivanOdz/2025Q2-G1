output "images_bucket_name" {
  description = "Name of the S3 bucket for images"
  value       = aws_s3_bucket.images.id
}

output "images_bucket_arn" {
  description = "ARN of the S3 bucket for images"
  value       = aws_s3_bucket.images.arn
}

output "images_bucket_domain_name" {
  description = "Domain name of the S3 bucket"
  value       = aws_s3_bucket.images.bucket_domain_name
}