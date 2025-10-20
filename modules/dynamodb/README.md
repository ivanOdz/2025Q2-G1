# DynamoDB Module

A comprehensive, reusable Terraform module for creating AWS DynamoDB tables with flexible configuration options.

## Features

- **Flexible Billing Modes**: Support for both PAY_PER_REQUEST and PROVISIONED billing
- **Configurable Indexes**: Support for Global Secondary Indexes (GSI) and Local Secondary Indexes (LSI)
- **Encryption**: Built-in KMS encryption with optional custom KMS keys
- **Backup & Recovery**: Point-in-time recovery support
- **TTL Support**: Time-to-live functionality for automatic item expiration
- **DynamoDB Streams**: Optional stream configuration
- **Deletion Protection**: Optional deletion protection for production tables
- **Comprehensive Outputs**: All necessary attributes for integration with other services

## Usage

### Basic Usage (Pay-per-request)

```hcl
module "dynamodb_table" {
  source = "../../modules/dynamodb"

  table_name = "my-application-table"
  tags = {
    Environment = "dev"
    Project     = "my-project"
  }
}
```

### Advanced Usage (Provisioned with Custom Indexes)

```hcl
module "dynamodb_table" {
  source = "../../modules/dynamodb"

  table_name    = "my-application-table"
  billing_mode  = "PROVISIONED"
  read_capacity = 10
  write_capacity = 10

  # Custom attributes
  attributes = [
    {
      name = "PK"
      type = "S"
    },
    {
      name = "SK"
      type = "S"
    },
    {
      name = "GSI1PK"
      type = "S"
    },
    {
      name = "GSI1SK"
      type = "S"
    },
    {
      name = "GSI2PK"
      type = "S"
    },
    {
      name = "GSI2SK"
      type = "N"
    }
  ]

  # Multiple Global Secondary Indexes
  global_secondary_indexes = [
    {
      name            = "GSI1"
      hash_key        = "GSI1PK"
      range_key       = "GSI1SK"
      projection_type = "ALL"
      read_capacity   = 5
      write_capacity  = 5
    },
    {
      name            = "GSI2"
      hash_key        = "GSI2PK"
      range_key       = "GSI2SK"
      projection_type = "INCLUDE"
      read_capacity   = 3
      write_capacity  = 3
    }
  ]

  # Local Secondary Index
  local_secondary_indexes = [
    {
      name            = "LSI1"
      range_key       = "LSI1SK"
      projection_type = "ALL"
    }
  ]

  # Security and backup features
  encryption_enabled              = true
  point_in_time_recovery_enabled = true
  deletion_protection_enabled    = true
  stream_enabled                 = true
  stream_view_type               = "NEW_AND_OLD_IMAGES"

  # TTL configuration
  ttl_enabled         = true
  ttl_attribute_name  = "expires_at"

  tags = {
    Environment = "prod"
    Project     = "my-project"
    Owner       = "data-team"
  }
}
```

### Single-Key Table (No Range Key)

```hcl
module "dynamodb_table" {
  source = "../../modules/dynamodb"

  table_name = "user-sessions"
  hash_key   = "session_id"
  range_key  = ""  # Empty string for single-key table

  attributes = [
    {
      name = "session_id"
      type = "S"
    }
  ]

  global_secondary_indexes = []
  local_secondary_indexes  = []

  tags = {
    Environment = "dev"
    Purpose     = "session-storage"
  }
}
```

## Variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| table_name | Name of the DynamoDB table | `string` | n/a | yes |
| billing_mode | Billing mode: PAY_PER_REQUEST or PROVISIONED | `string` | `"PAY_PER_REQUEST"` | no |
| hash_key | Attribute to use as the hash (partition) key | `string` | `"PK"` | no |
| range_key | Attribute to use as the range (sort) key | `string` | `"SK"` | no |
| attributes | List of attribute definitions | `list(object)` | See variables.tf | no |
| global_secondary_indexes | List of global secondary indexes | `list(object)` | See variables.tf | no |
| local_secondary_indexes | List of local secondary indexes | `list(object)` | `[]` | no |
| read_capacity | Read capacity units (PROVISIONED only) | `number` | `5` | no |
| write_capacity | Write capacity units (PROVISIONED only) | `number` | `5` | no |
| encryption_enabled | Enable server-side encryption | `bool` | `true` | no |
| kms_key_id | KMS key ID for encryption | `string` | `null` | no |
| point_in_time_recovery_enabled | Enable point-in-time recovery | `bool` | `true` | no |
| ttl_enabled | Enable TTL | `bool` | `false` | no |
| ttl_attribute_name | Attribute name for TTL | `string` | `"ttl"` | no |
| stream_enabled | Enable DynamoDB Streams | `bool` | `false` | no |
| stream_view_type | Stream view type | `string` | `"NEW_AND_OLD_IMAGES"` | no |
| deletion_protection_enabled | Enable deletion protection | `bool` | `false` | no |
| tags | Tags to apply to the table | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| table_name | Name of the DynamoDB table |
| table_arn | ARN of the DynamoDB table |
| table_id | ID of the DynamoDB table |
| table_stream_arn | ARN of the DynamoDB stream (if enabled) |
| table_hash_key | Hash key attribute name |
| table_range_key | Range key attribute name |
| table_billing_mode | Billing mode of the table |
| table_read_capacity | Read capacity units |
| table_write_capacity | Write capacity units |
| global_secondary_index_names | List of GSI names |
| local_secondary_index_names | List of LSI names |
| kms_key_id | KMS key ID used for encryption |
| kms_key_arn | KMS key ARN used for encryption |
| table_endpoint | DynamoDB table endpoint URL |

## Examples

### E-commerce Application

```hcl
module "ecommerce_dynamodb" {
  source = "../../modules/dynamodb"

  table_name = "ecommerce-${var.environment}"

  attributes = [
    { name = "PK", type = "S" },      # partition key
    { name = "SK", type = "S" },      # sort key
    { name = "GSI1PK", type = "S" },  # user_id
    { name = "GSI1SK", type = "S" },  # order_date
    { name = "GSI2PK", type = "S" },  # product_id
    { name = "GSI2SK", type = "N" },  # price
  ]

  global_secondary_indexes = [
    {
      name            = "UserOrders"
      hash_key        = "GSI1PK"
      range_key       = "GSI1SK"
      projection_type = "ALL"
    },
    {
      name            = "ProductIndex"
      hash_key        = "GSI2PK"
      range_key       = "GSI2SK"
      projection_type = "INCLUDE"
    }
  ]

  # Production settings
  encryption_enabled              = true
  point_in_time_recovery_enabled = true
  deletion_protection_enabled    = var.environment == "prod"
  stream_enabled                 = true

  tags = {
    Environment = var.environment
    Project     = "ecommerce"
    DataType    = "transactional"
  }
}
```

### User Sessions with TTL

```hcl
module "user_sessions" {
  source = "../../modules/dynamodb"

  table_name = "user-sessions-${var.environment}"

  hash_key = "session_id"
  range_key = ""  # Single-key table

  attributes = [
    { name = "session_id", type = "S" },
    { name = "user_id", type = "S" },
    { name = "created_at", type = "N" }
  ]

  global_secondary_indexes = [
    {
      name            = "UserSessions"
      hash_key        = "user_id"
      range_key       = "created_at"
      projection_type = "ALL"
    }
  ]

  # TTL for automatic session cleanup
  ttl_enabled        = true
  ttl_attribute_name = "expires_at"

  # Security
  encryption_enabled              = true
  point_in_time_recovery_enabled = true

  tags = {
    Environment = var.environment
    Purpose     = "session-management"
    TTL         = "enabled"
  }
}
```

## Best Practices

1. **Use PAY_PER_REQUEST for development** and unpredictable workloads
2. **Use PROVISIONED for production** with predictable, consistent workloads
3. **Enable encryption** for all production tables
4. **Enable point-in-time recovery** for critical data
5. **Use deletion protection** for production tables
6. **Design your access patterns** before creating indexes
7. **Monitor capacity usage** and adjust as needed
8. **Use TTL** for automatic cleanup of temporary data
9. **Enable streams** for real-time processing needs
10. **Tag your resources** for cost allocation and management

## Migration from Deprecated Module

If you're migrating from the deprecated database module:

```hcl
# Old way
module "database" {
  source = "../../deprecated_modules/database"
  table_name = "my-table"
  tags = var.tags
}

# New way
module "dynamodb_table" {
  source = "../../modules/dynamodb"
  table_name = "my-table"
  tags = var.tags
  # All other settings use sensible defaults
}
```

## Integration with Lambda Functions

```hcl
# DynamoDB table
module "dynamodb_table" {
  source = "../../modules/dynamodb"
  table_name = "my-data-table"
}

# Lambda function with DynamoDB access
module "lambda_function" {
  source = "../../modules/lambda-api"
  
  name_prefix = var.project_name
  function_key = "data-processor"
  runtime = "python3.12"
  handler = "lambda_function.main"
  role_arn = aws_iam_role.lambda_role.arn
  
  env = {
    DYNAMODB_TABLE = module.dynamodb_table.table_name
    DYNAMODB_TABLE_ARN = module.dynamodb_table.table_arn
  }
}

# IAM policy for Lambda to access DynamoDB
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
