# Lambda API Module

A comprehensive, reusable Terraform module for creating AWS Lambda functions with S3-based code deployment, designed for API endpoints and microservices.

## Features

- **S3-Based Deployment**: Deploy Lambda functions from ZIP files stored in S3
- **Flexible Configuration**: Support for various runtimes, memory sizes, and timeouts
- **VPC Support**: Optional VPC configuration for network isolation
- **Environment Variables**: Configurable environment variables
- **Lambda Layers**: Support for Lambda layers
- **CloudWatch Integration**: Automatic log group creation with configurable retention
- **Version Control**: S3 object versioning support
- **Change Detection**: Source code hash for efficient deployments
- **Architecture Support**: ARM64 and x86_64 architectures
- **Comprehensive Outputs**: All necessary attributes for integration

## Usage

### Basic Usage

```hcl
module "api_lambda" {
  source = "../../modules/lambda-api"

  name_prefix  = "myapp"
  function_key = "api"
  runtime      = "python3.12"
  handler      = "lambda_function.main"
  role_arn     = aws_iam_role.lambda_role.arn

  # S3 deployment configuration
  code_bucket         = "my-lambda-deployments"
  s3_key             = "api-function-v1.0.0.zip"
  s3_object_version  = "abc123def456"
  source_code_hash_b64 = "base64encodedhash..."

  tags = {
    Environment = "dev"
    Project     = "my-project"
  }
}
```

### Advanced Usage with VPC

```hcl
module "api_lambda" {
  source = "../../modules/lambda-api"

  name_prefix  = "myapp"
  function_key = "api"
  runtime      = "python3.12"
  handler      = "lambda_function.main"
  role_arn     = aws_iam_role.lambda_role.arn

  # Performance configuration
  memory_mb    = 512
  timeout_s    = 30
  architectures = ["arm64"]

  # S3 deployment
  code_bucket         = "my-lambda-deployments"
  s3_key             = "api-function-v1.0.0.zip"
  source_code_hash_b64 = "base64encodedhash..."

  # VPC configuration
  subnet_ids = ["subnet-12345", "subnet-67890"]
  sg_ids     = ["sg-12345"]

  # Environment variables
  env = {
    DYNAMODB_TABLE = "my-table"
    SNS_TOPIC_ARN  = "arn:aws:sns:us-east-1:123456789012:my-topic"
    LOG_LEVEL      = "INFO"
  }

  # Lambda layers
  layers = [
    "arn:aws:lambda:us-east-1:123456789012:layer:common-utils:1"
  ]

  # Logging configuration
  log_retention_in_days = 30

  tags = {
    Environment = "prod"
    Project     = "my-project"
    Owner       = "api-team"
  }
}
```

### Multiple Functions

```hcl
# Packages API
module "packages_lambda" {
  source = "../../modules/lambda-api"

  name_prefix  = "myapp"
  function_key = "packages"
  runtime      = "python3.12"
  handler      = "packages_handler.main"
  role_arn     = aws_iam_role.lambda_role.arn

  code_bucket         = "my-lambda-deployments"
  s3_key             = "packages-function-v1.0.0.zip"
  source_code_hash_b64 = "packages_hash..."

  env = {
    DYNAMODB_TABLE = module.dynamodb_table.table_name
  }
}

# Tracks API
module "tracks_lambda" {
  source = "../../modules/lambda-api"

  name_prefix  = "myapp"
  function_key = "tracks"
  runtime      = "python3.12"
  handler      = "tracks_handler.main"
  role_arn     = aws_iam_role.lambda_role.arn

  code_bucket         = "my-lambda-deployments"
  s3_key             = "tracks-function-v1.0.0.zip"
  source_code_hash_b64 = "tracks_hash..."

  env = {
    DYNAMODB_TABLE = module.dynamodb_table.table_name
  }
}
```

## Variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| name_prefix | Prefix for naming the Lambda function | `string` | n/a | yes |
| function_key | Short key for the function (concatenated with prefix) | `string` | n/a | yes |
| runtime | Lambda runtime (e.g., python3.12, nodejs20.x) | `string` | n/a | yes |
| handler | Lambda handler (e.g., handler.main) | `string` | n/a | yes |
| role_arn | IAM role ARN for Lambda execution | `string` | n/a | yes |
| code_bucket | S3 bucket containing the ZIP artifact | `string` | n/a | yes |
| s3_key | S3 object key for the ZIP file | `string` | n/a | yes |
| source_code_hash_b64 | Base64-encoded SHA256 hash of the ZIP file | `string` | n/a | yes |
| memory_mb | Memory allocation in MB | `number` | `256` | no |
| timeout_s | Timeout in seconds | `number` | `15` | no |
| env | Environment variables | `map(string)` | `{}` | no |
| subnet_ids | Subnet IDs for VPC configuration | `list(string)` | `[]` | no |
| sg_ids | Security group IDs for VPC configuration | `list(string)` | `[]` | no |
| layers | Lambda layer ARNs | `list(string)` | `[]` | no |
| architectures | Lambda architectures | `list(string)` | `["arm64"]` | no |
| publish | Publish new version on each change | `bool` | `true` | no |
| log_retention_in_days | CloudWatch log retention in days | `number` | `14` | no |
| s3_object_version | S3 object version ID (optional) | `string` | `null` | no |

## Outputs

| Name | Description |
|------|-------------|
| function_name | Name of the Lambda function |
| function_arn | ARN of the Lambda function |
| function_version | Published version of the Lambda function |
| function_invoke_arn | Invoke ARN (for API Gateway integration) |
| function_qualified_arn | Qualified ARN (includes version) |
| function_last_modified | Date the function was last modified |
| function_source_code_hash | SHA256 hash of the deployed package |
| function_source_code_size | Size of the deployment package in bytes |
| function_memory_size | Memory size allocated to the function |
| function_timeout | Timeout of the function in seconds |
| function_runtime | Runtime of the Lambda function |
| function_handler | Handler of the Lambda function |
| function_architectures | Architecture of the Lambda function |
| log_group_name | Name of the CloudWatch log group |
| log_group_arn | ARN of the CloudWatch log group |
| log_group_retention_in_days | Log retention period in days |

## Validation Rules

The module includes validation rules to ensure proper configuration:

- **Required S3 parameters**: `code_bucket`, `s3_key`, and `source_code_hash_b64` must be provided
- **Memory limits**: Memory size must be between 128 MB and 10240 MB
- **Timeout limits**: Timeout must be between 1 and 900 seconds
- **Runtime validation**: Runtime must be a supported AWS Lambda runtime

## Examples

### API Gateway Integration

```hcl
# Lambda function
module "api_lambda" {
  source = "../../modules/lambda-api"
  
  name_prefix  = "myapp"
  function_key = "api"
  runtime      = "python3.12"
  handler      = "lambda_function.main"
  role_arn     = aws_iam_role.lambda_role.arn
  
  code_bucket         = "my-lambda-deployments"
  s3_key             = "api-function-v1.0.0.zip"
  source_code_hash_b64 = "hash..."
}

# API Gateway integration
resource "aws_api_gateway_integration" "lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.proxy.id
  http_method = aws_api_gateway_method.proxy.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = module.api_lambda.function_invoke_arn
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.api_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}
```

### DynamoDB Integration

```hcl
# DynamoDB table
module "dynamodb_table" {
  source = "../../modules/dynamodb"
  table_name = "my-data-table"
}

# Lambda function with DynamoDB access
module "data_lambda" {
  source = "../../modules/lambda-api"
  
  name_prefix  = "myapp"
  function_key = "data-processor"
  runtime      = "python3.12"
  handler      = "lambda_function.main"
  role_arn     = aws_iam_role.lambda_role.arn
  
  code_bucket         = "my-lambda-deployments"
  s3_key             = "data-processor-v1.0.0.zip"
  source_code_hash_b64 = "hash..."
  
  env = {
    DYNAMODB_TABLE = module.dynamodb_table.table_name
    DYNAMODB_TABLE_ARN = module.dynamodb_table.table_arn
  }
}

# IAM policy for DynamoDB access
resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "lambda-dynamodb-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          module.dynamodb_table.table_arn,
          "${module.dynamodb_table.table_arn}/index/*"
        ]
      }
    ]
  })
}
```

### Event-Driven Architecture

```hcl
# SNS topic
resource "aws_sns_topic" "events" {
  name = "my-events-topic"
}

# Lambda function triggered by SNS
module "event_processor" {
  source = "../../modules/lambda-api"
  
  name_prefix  = "myapp"
  function_key = "event-processor"
  runtime      = "python3.12"
  handler      = "lambda_function.main"
  role_arn     = aws_iam_role.lambda_role.arn
  
  code_bucket         = "my-lambda-deployments"
  s3_key             = "event-processor-v1.0.0.zip"
  source_code_hash_b64 = "hash..."
  
  env = {
    SNS_TOPIC_ARN = aws_sns_topic.events.arn
  }
}

# SNS subscription
resource "aws_sns_topic_subscription" "lambda" {
  topic_arn = aws_sns_topic.events.arn
  protocol  = "lambda"
  endpoint  = module.event_processor.function_arn
}

# Lambda permission for SNS
resource "aws_lambda_permission" "sns" {
  statement_id  = "AllowSNSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.event_processor.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.events.arn
}
```

## Best Practices

1. **Use ARM64 architecture** for better price/performance ratio
2. **Set appropriate memory and timeout** based on your function's needs
3. **Enable VPC configuration** for functions that need to access private resources
4. **Use environment variables** for configuration instead of hardcoding values
5. **Implement proper error handling** in your Lambda functions
6. **Use Lambda layers** for shared dependencies
7. **Monitor function performance** using CloudWatch metrics
8. **Set appropriate log retention** to manage costs
9. **Use IAM roles with least privilege** for security
10. **Test functions locally** before deployment

## Migration from Deprecated Modules

If migrating from deprecated backend modules:

```hcl
# Old way (deprecated)
module "backend" {
  source = "../../deprecated_modules/backend"
  # ... configuration
}

# New way
module "api_lambda" {
  source = "../../modules/lambda-api"
  
  name_prefix  = var.project_name
  function_key = "api"
  runtime      = "python3.12"
  handler      = "lambda_function.main"
  role_arn     = aws_iam_role.lambda_role.arn
  
  # S3 deployment
  code_bucket         = var.code_bucket
  s3_key             = var.s3_key
  source_code_hash_b64 = var.source_code_hash_b64
  
  # VPC configuration
  subnet_ids = var.lambda_subnet_ids
  sg_ids     = [aws_security_group.lambda_sg.id]
  
  # Environment variables
  env = {
    DYNAMODB_TABLE = module.dynamodb_table.table_name
    SNS_TOPIC_ARN  = module.sns_topic.arn
  }
}
```

## Troubleshooting

### Common Issues

1. **S3 access denied**: Ensure the Lambda execution role has S3 read permissions
2. **VPC connectivity issues**: Check security group rules and subnet configuration
3. **Timeout errors**: Increase timeout or optimize function performance
4. **Memory errors**: Increase memory allocation or optimize memory usage
5. **Cold start issues**: Use provisioned concurrency for critical functions

### Debugging

- Check CloudWatch logs for function execution details
- Use AWS X-Ray for distributed tracing
- Monitor CloudWatch metrics for performance insights
- Test functions locally using AWS SAM or similar tools
