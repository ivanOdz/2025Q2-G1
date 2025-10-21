# DynamoDB Table Outputs

output "table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.main.name
}

output "table_arn" {
  description = "ARN of the DynamoDB table"
  value       = aws_dynamodb_table.main.arn
}

output "table_id" {
  description = "ID of the DynamoDB table"
  value       = aws_dynamodb_table.main.id
}

output "table_stream_arn" {
  description = "ARN of the DynamoDB stream (if enabled)"
  value       = aws_dynamodb_table.main.stream_arn
}

output "table_stream_label" {
  description = "Label of the DynamoDB stream (if enabled)"
  value       = aws_dynamodb_table.main.stream_label
}

output "table_hash_key" {
  description = "Hash key attribute name"
  value       = aws_dynamodb_table.main.hash_key
}

output "table_range_key" {
  description = "Range key attribute name"
  value       = aws_dynamodb_table.main.range_key
}

output "table_billing_mode" {
  description = "Billing mode of the DynamoDB table"
  value       = aws_dynamodb_table.main.billing_mode
}

output "table_read_capacity" {
  description = "Read capacity units (if using PROVISIONED billing)"
  value       = aws_dynamodb_table.main.read_capacity
}

output "table_write_capacity" {
  description = "Write capacity units (if using PROVISIONED billing)"
  value       = aws_dynamodb_table.main.write_capacity
}

output "global_secondary_index_names" {
  description = "List of global secondary index names"
  value       = aws_dynamodb_table.main.global_secondary_index
}

output "local_secondary_index_names" {
  description = "List of local secondary index names"
  value       = aws_dynamodb_table.main.local_secondary_index
}

output "kms_key_id" {
  description = "KMS key ID used for encryption (if created by this module)"
  value       = var.encryption_enabled && var.kms_key_id == null ? aws_kms_key.dynamodb[0].key_id : var.kms_key_id
}

output "kms_key_arn" {
  description = "KMS key ARN used for encryption (if created by this module)"
  value       = var.encryption_enabled && var.kms_key_id == null ? aws_kms_key.dynamodb[0].arn : null
}

output "kms_alias_name" {
  description = "KMS alias name (if created by this module)"
  value       = var.encryption_enabled && var.kms_key_id == null ? aws_kms_alias.dynamodb[0].name : null
}

# Useful for Lambda functions and other AWS services
output "table_endpoint" {
  description = "DynamoDB table endpoint URL"
  value       = "https://dynamodb.${data.aws_region.current.id}.amazonaws.com"
}

# Data source for current region (needed for endpoint)
data "aws_region" "current" {}
