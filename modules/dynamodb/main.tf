# DynamoDB Table Module
# Creates a flexible, reusable DynamoDB table with configurable options

resource "aws_dynamodb_table" "main" {
  name           = var.table_name
  billing_mode   = var.billing_mode
  hash_key       = var.hash_key
  range_key      = var.range_key

  # Dynamically create attributes based on the attribute definitions
  dynamic "attribute" {
    for_each = var.attributes
    content {
      name = attribute.value.name
      type = attribute.value.type
    }
  }

  # Dynamically create global secondary indexes
  dynamic "global_secondary_index" {
    for_each = var.global_secondary_indexes
    content {
      name            = global_secondary_index.value.name
      hash_key        = global_secondary_index.value.hash_key
      range_key       = global_secondary_index.value.range_key
      projection_type = global_secondary_index.value.projection_type
      
      # Only set read/write capacity if using PROVISIONED billing mode
      read_capacity  = var.billing_mode == "PROVISIONED" ? global_secondary_index.value.read_capacity : null
      write_capacity = var.billing_mode == "PROVISIONED" ? global_secondary_index.value.write_capacity : null
    }
  }

  # Dynamically create local secondary indexes
  dynamic "local_secondary_index" {
    for_each = var.local_secondary_indexes
    content {
      name            = local_secondary_index.value.name
      range_key       = local_secondary_index.value.range_key
      projection_type = local_secondary_index.value.projection_type
    }
  }

  # Capacity settings (only for PROVISIONED billing mode)
  read_capacity  = var.billing_mode == "PROVISIONED" ? var.read_capacity : null
  write_capacity = var.billing_mode == "PROVISIONED" ? var.write_capacity : null

  # Encryption
  server_side_encryption {
    enabled     = var.encryption_enabled
    kms_key_arn = var.encryption_enabled ? (var.kms_key_id != null ? var.kms_key_id : aws_kms_key.dynamodb[0].arn) : null
  }

  # Point-in-time recovery
  point_in_time_recovery {
    enabled = var.point_in_time_recovery_enabled
  }

  # TTL
  dynamic "ttl" {
    for_each = var.ttl_enabled ? [1] : []
    content {
      attribute_name = var.ttl_attribute_name
      enabled        = var.ttl_enabled
    }
  }

  # Stream configuration
  dynamic "stream" {
    for_each = var.stream_enabled ? [1] : []
    content {
      stream_view_type = var.stream_view_type
    }
  }

  # Deletion protection
  deletion_protection_enabled = var.deletion_protection_enabled

  tags = var.tags

  lifecycle {
    ignore_changes = [
      # Ignore changes to read/write capacity if using PAY_PER_REQUEST
      read_capacity,
      write_capacity,
    ]
  }
}

# DynamoDB KMS key (if encryption is enabled and no KMS key provided)
resource "aws_kms_key" "dynamodb" {
  count = var.encryption_enabled && var.kms_key_id == null ? 1 : 0

  description             = "KMS key for DynamoDB table ${var.table_name}"
  deletion_window_in_days = var.kms_deletion_window_in_days

  tags = merge(var.tags, {
    Name = "${var.table_name}-dynamodb-key"
  })
}

resource "aws_kms_alias" "dynamodb" {
  count = var.encryption_enabled && var.kms_key_id == null ? 1 : 0

  name          = "alias/${var.table_name}-dynamodb"
  target_key_id = aws_kms_key.dynamodb[0].key_id
}
