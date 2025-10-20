output "function_name" {
  description = "Nombre de la función Lambda."
  value       = aws_lambda_function.this.function_name
}

output "function_arn" {
  description = "ARN de la función Lambda."
  value       = aws_lambda_function.this.arn
}

output "function_version" {
  description = "Versión publicada (si publish = true)."
  value       = aws_lambda_function.this.version
}

output "log_group_name" {
  description = "Log group de CloudWatch."
  value       = aws_cloudwatch_log_group.lg.name
}
