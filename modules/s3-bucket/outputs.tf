# S3 Bucket Information
output "bucket_id" {
  description = "The name of the bucket"
  value       = aws_s3_bucket.this.id
}

output "bucket_arn" {
  description = "The ARN of the bucket"
  value       = aws_s3_bucket.this.arn
}

output "bucket_domain_name" {
  description = "The bucket domain name"
  value       = aws_s3_bucket.this.bucket_domain_name
}

output "bucket_regional_domain_name" {
  description = "The bucket region-specific domain name"
  value       = aws_s3_bucket.this.bucket_regional_domain_name
}

output "bucket_hosted_zone_id" {
  description = "The Route 53 Hosted Zone ID for this bucket's region"
  value       = aws_s3_bucket.this.hosted_zone_id
}

output "bucket_region" {
  description = "The AWS region this bucket resides in"
  value       = aws_s3_bucket.this.region
}

output "bucket_website_endpoint" {
  description = "The website endpoint, if the bucket is configured with a website"
  value       = aws_s3_bucket.this.website_endpoint
}

output "bucket_website_domain" {
  description = "The domain of the website endpoint, if the bucket is configured with a website"
  value       = aws_s3_bucket.this.website_domain
}

# Versioning Information
output "versioning_status" {
  description = "The versioning state of the bucket"
  value       = aws_s3_bucket_versioning.this.versioning_configuration[0].status
}

# Encryption Information
output "encryption_algorithm" {
  description = "The server-side encryption algorithm used"
  value       = aws_s3_bucket_server_side_encryption_configuration.this.rule[0].apply_server_side_encryption_by_default[0].sse_algorithm
}

output "kms_key_id" {
  description = "The KMS key ID used for encryption"
  value       = aws_s3_bucket_server_side_encryption_configuration.this.rule[0].apply_server_side_encryption_by_default[0].kms_master_key_id
}

# Public Access Block Information
output "public_access_block_configuration" {
  description = "The public access block configuration"
  value = {
    block_public_acls       = aws_s3_bucket_public_access_block.this.block_public_acls
    block_public_policy     = aws_s3_bucket_public_access_block.this.block_public_policy
    ignore_public_acls      = aws_s3_bucket_public_access_block.this.ignore_public_acls
    restrict_public_buckets = aws_s3_bucket_public_access_block.this.restrict_public_buckets
  }
}

# Website Configuration Information
output "website_configuration" {
  description = "The website configuration"
  value = var.website_configuration != null ? {
    index_document = aws_s3_bucket_website_configuration.this[0].index_document[0].suffix
    error_document = try(aws_s3_bucket_website_configuration.this[0].error_document[0].key, null)
    website_endpoint = aws_s3_bucket_website_configuration.this[0].website_endpoint
    website_domain   = aws_s3_bucket_website_configuration.this[0].website_domain
  } : null
}

# Logging Configuration Information
output "logging_configuration" {
  description = "The logging configuration"
  value = var.logging_configuration != null ? {
    target_bucket = aws_s3_bucket_logging.this[0].target_bucket
    target_prefix = aws_s3_bucket_logging.this[0].target_prefix
  } : null
}

# ACL Information
output "acl" {
  description = "The ACL applied to the bucket"
  value       = var.acl != null ? aws_s3_bucket_acl.this[0].acl : null
}

output "object_ownership" {
  description = "The object ownership setting"
  value       = var.acl != null ? aws_s3_bucket_ownership_controls.this[0].rule[0].object_ownership : null
}
