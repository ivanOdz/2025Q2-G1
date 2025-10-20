# S3 Bucket Terraform Module

This Terraform module creates a comprehensive AWS S3 bucket with configurable features including versioning, encryption, lifecycle policies, notifications, CORS, website hosting, and more.

## Features

- S3 Bucket creation with customizable name and tags
- Versioning configuration
- Server-side encryption (AES256 or KMS)
- Public access block settings
- Lifecycle rules for cost optimization
- Event notifications (Lambda, SQS, SNS)
- CORS configuration
- Static website hosting
- Access logging
- Bucket policies
- ACL configuration
-  Comprehensive outputs

## Usage

### Basic Example

```hcl
module "s3_bucket" {
  source = "./modules/s3-bucket"

  bucket_name = "my-unique-bucket-name"
  tags = {
    Environment = "production"
    Project     = "my-project"
  }
}
```

### Advanced Example with All Features

```hcl
module "s3_bucket" {
  source = "./modules/s3-bucket"

  bucket_name = "my-advanced-bucket"
  
  # Versioning
  versioning_enabled = true
  
  # Encryption
  encryption_algorithm = "aws:kms"
  kms_key_id          = "arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"
  bucket_key_enabled  = true
  
  # Public Access Block
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
  
  # Lifecycle Rules
  lifecycle_rules = [
    {
      id     = "delete_old_versions"
      status = "Enabled"
      noncurrent_version_expiration = {
        noncurrent_days = 30
      }
    },
    {
      id     = "transition_to_ia"
      status = "Enabled"
      filter = {
        prefix = "logs/"
      }
      transitions = [
        {
          days          = 30
          storage_class = "STANDARD_IA"
        },
        {
          days          = 90
          storage_class = "GLACIER"
        }
      ]
    }
  ]
  
  # CORS Configuration
  cors_rules = [
    {
      allowed_headers = ["*"]
      allowed_methods = ["GET", "PUT", "POST", "DELETE"]
      allowed_origins = ["https://example.com"]
      expose_headers  = ["ETag"]
      max_age_seconds = 3000
    }
  ]
  
  # Website Configuration
  website_configuration = {
    index_document = "index.html"
    error_document = "error.html"
  }
  
  # Logging Configuration
  logging_configuration = {
    target_bucket = "my-access-logs-bucket"
    target_prefix = "logs/"
  }
  
  # Tags
  tags = {
    Environment = "production"
    Project     = "my-project"
    Owner       = "team@company.com"
  }
}
```

### Website Hosting Example

```hcl
module "static_website" {
  source = "./modules/s3-bucket"

  bucket_name = "my-static-website"
  
  # Website configuration
  website_configuration = {
    index_document = "index.html"
    error_document = "404.html"
  }
  
  # Allow public read access for website
  acl = "public-read"
  
  # Disable public access block for website
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
  
  tags = {
    Purpose = "static-website"
  }
}
```

### Data Lake Example

```hcl
module "data_lake" {
  source = "./modules/s3-bucket"

  bucket_name = "my-data-lake"
  
  # Enable versioning for data protection
  versioning_enabled = true
  
  # Use KMS encryption
  encryption_algorithm = "aws:kms"
  bucket_key_enabled   = true
  
  # Lifecycle rules for cost optimization
  lifecycle_rules = [
    {
      id     = "data_lifecycle"
      status = "Enabled"
      transitions = [
        {
          days          = 30
          storage_class = "STANDARD_IA"
        },
        {
          days          = 90
          storage_class = "GLACIER"
        },
        {
          days          = 365
          storage_class = "DEEP_ARCHIVE"
        }
      ]
      noncurrent_version_transitions = [
        {
          noncurrent_days = 30
          storage_class   = "STANDARD_IA"
        }
      ]
    }
  ]
  
  # Access logging
  logging_configuration = {
    target_bucket = "my-data-lake-logs"
    target_prefix = "access-logs/"
  }
  
  tags = {
    Purpose     = "data-lake"
    DataType    = "analytics"
    Retention   = "7-years"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| bucket_name | The name of the S3 bucket | `string` | n/a | yes |
| tags | A mapping of tags to assign to the bucket | `map(string)` | `{}` | no |
| versioning_enabled | Enable versioning on the S3 bucket | `bool` | `false` | no |
| encryption_algorithm | The server-side encryption algorithm to use | `string` | `"AES256"` | no |
| kms_key_id | The AWS KMS master key ID used for the SSE-KMS encryption | `string` | `null` | no |
| bucket_key_enabled | Whether or not to use Amazon S3 Bucket Keys for SSE-KMS | `bool` | `false` | no |
| block_public_acls | Whether Amazon S3 should block public ACLs for this bucket | `bool` | `true` | no |
| block_public_policy | Whether Amazon S3 should block public bucket policies for this bucket | `bool` | `true` | no |
| ignore_public_acls | Whether Amazon S3 should ignore public ACLs for this bucket | `bool` | `true` | no |
| restrict_public_buckets | Whether Amazon S3 should restrict public bucket policies for this bucket | `bool` | `true` | no |
| lifecycle_rules | List of lifecycle rules for the S3 bucket | `list(object)` | `[]` | no |
| notifications | S3 bucket notification configuration | `object` | `null` | no |
| cors_rules | List of CORS rules for the S3 bucket | `list(object)` | `[]` | no |
| website_configuration | Website configuration for the S3 bucket | `object` | `null` | no |
| logging_configuration | Logging configuration for the S3 bucket | `object` | `null` | no |
| bucket_policy | The bucket policy as a JSON string | `string` | `null` | no |
| acl | The canned ACL to apply to the bucket | `string` | `null` | no |
| object_ownership | The object ownership setting for the bucket | `string` | `"BucketOwnerPreferred"` | no |

## Outputs

| Name | Description |
|------|-------------|
| bucket_id | The name of the bucket |
| bucket_arn | The ARN of the bucket |
| bucket_domain_name | The bucket domain name |
| bucket_regional_domain_name | The bucket region-specific domain name |
| bucket_hosted_zone_id | The Route 53 Hosted Zone ID for this bucket's region |
| bucket_region | The AWS region this bucket resides in |
| bucket_website_endpoint | The website endpoint, if the bucket is configured with a website |
| bucket_website_domain | The domain of the website endpoint, if the bucket is configured with a website |
| versioning_status | The versioning state of the bucket |
| encryption_algorithm | The server-side encryption algorithm used |
| kms_key_id | The KMS key ID used for encryption |
| public_access_block_configuration | The public access block configuration |
| website_configuration | The website configuration |
| logging_configuration | The logging configuration |
| acl | The ACL applied to the bucket |
| object_ownership | The object ownership setting |

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.0 |
| aws | >= 5.0 |

## Providers

| Name | Version |
|------|---------|
| aws | >= 5.0 |

## Security Considerations

1. **Public Access**: By default, this module blocks all public access. Only disable these settings if you specifically need public access (e.g., for static websites).

2. **Encryption**: Always enable encryption for sensitive data. Use KMS encryption for additional security and audit capabilities.

3. **Versioning**: Enable versioning for critical data to protect against accidental deletion or modification.

4. **Lifecycle Rules**: Implement lifecycle rules to manage costs and comply with data retention policies.

5. **Access Logging**: Enable access logging for audit and security monitoring.

6. **Bucket Policies**: Use bucket policies to implement fine-grained access control.

## Best Practices

1. **Naming**: Use descriptive, unique bucket names that follow your organization's naming conventions.

2. **Tags**: Always tag your resources for cost allocation, compliance, and management purposes.

3. **Lifecycle Management**: Implement lifecycle rules to automatically transition objects to cheaper storage classes and delete old versions.

4. **Monitoring**: Set up CloudWatch alarms for bucket metrics and configure notifications for important events.

5. **Backup**: Consider cross-region replication for critical data.

6. **Access Control**: Use IAM policies and bucket policies together for comprehensive access control.

## License

This module is released under the MIT License.
