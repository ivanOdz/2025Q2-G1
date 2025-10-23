# Outputs del ambiente

# VPC outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnets" {
  description = "List of IDs of private subnets"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "List of IDs of public subnets"
  value       = module.vpc.public_subnets
}

# Database outputs
output "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  value       = module.dynamodb_table.table_name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table"
  value       = module.dynamodb_table.table_arn
}

# Events module outputs
output "sns_topic_arn" {
  description = "ARN of the SNS notifications topic"
  value       = aws_sns_topic.notifications.arn
}

output "sqs_queue_arn" {
  description = "ARN of the SQS notifications queue"
  value       = aws_sqs_queue.notifications_queue.arn
}

# Authentication outputs
output "cognito_user_pool_id" {
  description = "ID of the Cognito User Pool"
  value       = aws_cognito_user_pool.pool.id
}

output "cognito_user_pool_arn" {
  description = "ARN of the Cognito User Pool"
  value       = aws_cognito_user_pool.pool.arn
}

output "cognito_user_pool_client_id" {
  description = "ID of the Cognito User Pool Client"
  value       = aws_cognito_user_pool_client.client.id
}

# Lambda outputs
output "lambda_function_names" {
  description = "Map of Lambda function names"
  value       = { for k, m in module.lambdas : k => m.function_name }
}

output "lambda_function_arns" {
  description = "Map of Lambda function ARNs"
  value       = { for k, m in module.lambdas : k => m.function_arn }
}

# API Gateway outputs
output "api_gateway_id" {
  description = "ID of the API Gateway"
  value       = aws_api_gateway_rest_api.api.id
}

output "api_gateway_arn" {
  description = "ARN of the API Gateway"
  value       = aws_api_gateway_rest_api.api.arn
}

output "api_gateway_execution_arn" {
  description = "Execution ARN of the API Gateway"
  value       = aws_api_gateway_rest_api.api.execution_arn
}

output "api_gateway_deployment_id" {
  description = "ID of the API Gateway deployment"
  value       = aws_api_gateway_deployment.api_deploy.id
}

# WebSocket API outputs
output "websocket_api_id" {
  description = "ID of the WebSocket API Gateway"
  value       = aws_apigatewayv2_api.websocket_api.id
}

output "websocket_api_arn" {
  description = "ARN of the WebSocket API Gateway"
  value       = aws_apigatewayv2_api.websocket_api.arn
}

output "websocket_api_execution_arn" {
  description = "Execution ARN of the WebSocket API Gateway"
  value       = aws_apigatewayv2_api.websocket_api.execution_arn
}

output "websocket_api_endpoint" {
  description = "WebSocket API endpoint URL"
  value       = "wss://${aws_apigatewayv2_api.websocket_api.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${aws_apigatewayv2_stage.websocket_stage.name}"
}

output "websocket_api_http_endpoint" {
  description = "WebSocket API HTTP endpoint URL"
  value       = "https://${aws_apigatewayv2_api.websocket_api.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${aws_apigatewayv2_stage.websocket_stage.name}"
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
  value       = module.frontend_bucket.bucket_website_endpoint
}