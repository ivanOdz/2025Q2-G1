output "function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.this.function_name
}

output "function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.this.arn
}

output "function_version" {
  description = "Published version of the Lambda function (if publish = true)"
  value       = aws_lambda_function.this.version
}

output "function_invoke_arn" {
  description = "Invoke ARN of the Lambda function (for API Gateway integration)"
  value       = aws_lambda_function.this.invoke_arn
}

output "function_qualified_arn" {
  description = "Qualified ARN of the Lambda function (includes version)"
  value       = aws_lambda_function.this.qualified_arn
}

output "function_last_modified" {
  description = "Date the Lambda function was last modified"
  value       = aws_lambda_function.this.last_modified
}

output "function_source_code_hash" {
  description = "Base64-encoded SHA256 hash of the deployed package"
  value       = aws_lambda_function.this.source_code_hash
}

output "function_source_code_size" {
  description = "Size in bytes of the function's deployment package"
  value       = aws_lambda_function.this.source_code_size
}

output "function_memory_size" {
  description = "Memory size allocated to the Lambda function"
  value       = aws_lambda_function.this.memory_size
}

output "function_timeout" {
  description = "Timeout of the Lambda function in seconds"
  value       = aws_lambda_function.this.timeout
}

output "function_runtime" {
  description = "Runtime of the Lambda function"
  value       = aws_lambda_function.this.runtime
}

output "function_handler" {
  description = "Handler of the Lambda function"
  value       = aws_lambda_function.this.handler
}

output "function_architectures" {
  description = "Architecture of the Lambda function"
  value       = aws_lambda_function.this.architectures
}

output "log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.lg.name
}

output "log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.lg.arn
}

output "log_group_retention_in_days" {
  description = "Log retention period in days"
  value       = aws_cloudwatch_log_group.lg.retention_in_days
}
