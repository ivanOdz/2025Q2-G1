# Database Configuration
# Contains DynamoDB table configuration

# --- DynamoDB module ---
module "dynamodb_table" {
  source = "../../modules/dynamodb"

  # meta argument 'depends_on' used outside module
  depends_on = [module.vpc]

  table_name = "${local.base_name}-table"
  
  # Same configuration as deprecated module
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"
  
  # Attribute definitions (same as deprecated)
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
    }
  ]
  
  # Global Secondary Index (same as deprecated)
  global_secondary_indexes = [
    {
      name            = "GSI1"
      hash_key        = "GSI1PK"
      range_key       = "GSI1SK"
      projection_type = "ALL"
      read_capacity   = null
      write_capacity  = null
    }
  ]
  
  # Enhanced features (new capabilities)
  encryption_enabled              = var.dynamodb_encryption_enabled
  point_in_time_recovery_enabled = var.dynamodb_point_in_time_recovery
  deletion_protection_enabled    = var.dynamodb_deletion_protection
  
  tags = local.common_tags
}
