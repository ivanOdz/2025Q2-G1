# Basic Configuration
variable "bucket_name" {
  description = "The name of the S3 bucket"
  type        = string
}

variable "tags" {
  description = "A mapping of tags to assign to the bucket"
  type        = map(string)
  default     = {}
}

# Versioning Configuration
variable "versioning_enabled" {
  description = "Enable versioning on the S3 bucket"
  type        = bool
  default     = false
}

# Encryption Configuration
variable "encryption_algorithm" {
  description = "The server-side encryption algorithm to use"
  type        = string
  default     = "AES256"
  validation {
    condition     = contains(["AES256", "aws:kms"], var.encryption_algorithm)
    error_message = "Encryption algorithm must be either 'AES256' or 'aws:kms'."
  }
}

variable "kms_key_id" {
  description = "The AWS KMS master key ID used for the SSE-KMS encryption"
  type        = string
  default     = null
}

variable "bucket_key_enabled" {
  description = "Whether or not to use Amazon S3 Bucket Keys for SSE-KMS"
  type        = bool
  default     = false
}

# Public Access Block Configuration
variable "block_public_acls" {
  description = "Whether Amazon S3 should block public ACLs for this bucket"
  type        = bool
  default     = true
}

variable "block_public_policy" {
  description = "Whether Amazon S3 should block public bucket policies for this bucket"
  type        = bool
  default     = true
}

variable "ignore_public_acls" {
  description = "Whether Amazon S3 should ignore public ACLs for this bucket"
  type        = bool
  default     = true
}

variable "restrict_public_buckets" {
  description = "Whether Amazon S3 should restrict public bucket policies for this bucket"
  type        = bool
  default     = true
}

# Lifecycle Configuration
variable "lifecycle_rules" {
  description = "List of lifecycle rules for the S3 bucket"
  type = list(object({
    id     = string
    status = string
    filter = optional(object({
      prefix = optional(string)
    }))
    expiration = optional(object({
      days = number
    }))
    transitions = optional(list(object({
      days          = number
      storage_class = string
    })))
    noncurrent_version_expiration = optional(object({
      noncurrent_days = number
    }))
    noncurrent_version_transitions = optional(list(object({
      noncurrent_days = number
      storage_class   = string
    })))
  }))
  default = []
}

# Notification Configuration
variable "notifications" {
  description = "S3 bucket notification configuration"
  type = object({
    lambda_functions = optional(list(object({
      lambda_function_arn = string
      events              = list(string)
      filter_prefix       = optional(string)
      filter_suffix       = optional(string)
    })))
    sqs = optional(list(object({
      queue_arn     = string
      events        = list(string)
      filter_prefix = optional(string)
      filter_suffix = optional(string)
    })))
    sns = optional(list(object({
      topic_arn     = string
      events        = list(string)
      filter_prefix = optional(string)
      filter_suffix = optional(string)
    })))
  })
  default = null
}

# CORS Configuration
variable "cors_rules" {
  description = "List of CORS rules for the S3 bucket"
  type = list(object({
    allowed_headers = optional(list(string))
    allowed_methods = list(string)
    allowed_origins = list(string)
    expose_headers  = optional(list(string))
    max_age_seconds = optional(number)
  }))
  default = []
}

# Website Configuration
variable "website_configuration" {
  description = "Website configuration for the S3 bucket"
  type = object({
    index_document = string
    error_document = optional(string)
    routing_rules  = optional(list(object({
      condition = object({
        http_error_code_returned_equals = optional(string)
        key_prefix_equals               = optional(string)
      })
      redirect = object({
        host_name               = optional(string)
        http_redirect_code      = optional(string)
        protocol                = optional(string)
        replace_key_prefix_with = optional(string)
        replace_key_with        = optional(string)
      })
    })))
  })
  default = null
}

# Logging Configuration
variable "logging_configuration" {
  description = "Logging configuration for the S3 bucket"
  type = object({
    target_bucket = string
    target_prefix = optional(string)
  })
  default = null
}

# Bucket Policy
variable "bucket_policy" {
  description = "The bucket policy as a JSON string"
  type        = string
  default     = null
}

# ACL Configuration
variable "acl" {
  description = "The canned ACL to apply to the bucket"
  type        = string
  default     = null
  validation {
    condition = var.acl == null || contains([
      "private", "public-read", "public-read-write", "aws-exec-read",
      "authenticated-read", "bucket-owner-read", "bucket-owner-full-control",
      "log-delivery-write"
    ], var.acl)
    error_message = "ACL must be one of the valid canned ACLs or null."
  }
}

variable "object_ownership" {
  description = "The object ownership setting for the bucket"
  type        = string
  default     = "BucketOwnerPreferred"
  validation {
    condition = contains([
      "BucketOwnerPreferred", "BucketOwnerEnforced", "ObjectWriter"
    ], var.object_ownership)
    error_message = "Object ownership must be one of: BucketOwnerPreferred, BucketOwnerEnforced, ObjectWriter."
  }
}
