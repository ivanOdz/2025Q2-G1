# DynamoDB Table Variables

variable "table_name" {
  description = "Name of the DynamoDB table"
  type        = string
}

variable "billing_mode" {
  description = "Billing mode for the DynamoDB table. Options: PAY_PER_REQUEST, PROVISIONED"
  type        = string
  default     = "PAY_PER_REQUEST"
  
  validation {
    condition     = contains(["PAY_PER_REQUEST", "PROVISIONED"], var.billing_mode)
    error_message = "Billing mode must be either PAY_PER_REQUEST or PROVISIONED."
  }
}

variable "hash_key" {
  description = "Attribute to use as the hash (partition) key"
  type        = string
  default     = "PK"
}

variable "range_key" {
  description = "Attribute to use as the range (sort) key. Leave empty for single-key table"
  type        = string
  default     = "SK"
}

variable "attributes" {
  description = "List of attribute definitions for the table"
  type = list(object({
    name = string
    type = string
  }))
  default = [
    {
      name = "PK"
      type = "S"
    },
    {
      name = "SK"
      type = "S"
    }
  ]
}

variable "global_secondary_indexes" {
  description = "List of global secondary indexes"
  type = list(object({
    name            = string
    hash_key        = string
    range_key       = optional(string)
    projection_type = string
    read_capacity   = optional(number)
    write_capacity  = optional(number)
  }))
  default = [
    {
      name            = "GSI1"
      hash_key        = "GSI1PK"
      range_key       = "GSI1SK"
      projection_type = "ALL"
      read_capacity   = null
      write_capacity  = null
    }
  ]
}

variable "local_secondary_indexes" {
  description = "List of local secondary indexes"
  type = list(object({
    name            = string
    range_key       = string
    projection_type = string
  }))
  default = []
}

variable "read_capacity" {
  description = "Number of read capacity units for the table (only for PROVISIONED billing mode)"
  type        = number
  default     = 5
}

variable "write_capacity" {
  description = "Number of write capacity units for the table (only for PROVISIONED billing mode)"
  type        = number
  default     = 5
}

variable "encryption_enabled" {
  description = "Enable server-side encryption for the DynamoDB table"
  type        = bool
  default     = true
}

variable "kms_key_id" {
  description = "KMS key ID for encryption. If not provided, a new KMS key will be created"
  type        = string
  default     = null
}

variable "kms_deletion_window_in_days" {
  description = "Deletion window in days for the KMS key (if created by this module)"
  type        = number
  default     = 7
}

variable "point_in_time_recovery_enabled" {
  description = "Enable point-in-time recovery for the DynamoDB table"
  type        = bool
  default     = true
}

variable "ttl_enabled" {
  description = "Enable TTL (Time To Live) for the DynamoDB table"
  type        = bool
  default     = false
}

variable "ttl_attribute_name" {
  description = "Attribute name to use for TTL"
  type        = string
  default     = "ttl"
}

variable "stream_enabled" {
  description = "Enable DynamoDB Streams"
  type        = bool
  default     = false
}

variable "stream_view_type" {
  description = "Stream view type for DynamoDB Streams. Options: KEYS_ONLY, NEW_IMAGE, OLD_IMAGE, NEW_AND_OLD_IMAGES"
  type        = string
  default     = "NEW_AND_OLD_IMAGES"
  
  validation {
    condition = contains([
      "KEYS_ONLY", 
      "NEW_IMAGE", 
      "OLD_IMAGE", 
      "NEW_AND_OLD_IMAGES"
    ], var.stream_view_type)
    error_message = "Stream view type must be one of: KEYS_ONLY, NEW_IMAGE, OLD_IMAGE, NEW_AND_OLD_IMAGES."
  }
}

variable "deletion_protection_enabled" {
  description = "Enable deletion protection for the DynamoDB table"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to the DynamoDB table"
  type        = map(string)
  default     = {}
}

# Validation rules
variable "validation_rules" {
  description = "Custom validation rules for the table configuration"
  type = object({
    min_read_capacity  = optional(number, 1)
    max_read_capacity  = optional(number, 40000)
    min_write_capacity = optional(number, 1)
    max_write_capacity = optional(number, 40000)
  })
  default = {
    min_read_capacity  = 1
    max_read_capacity  = 40000
    min_write_capacity = 1
    max_write_capacity = 40000
  }
}
