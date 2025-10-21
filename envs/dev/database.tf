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


# Users Table (optional)
module "dynamodb_users" {
  source = "../../modules/dynamodb"

  table_name   = "package-tracking-users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = null

  attributes = [
    { name = "user_id", type = "S" },
    { name = "email",   type = "S" }
  ]

  global_secondary_indexes = [
    {
      name            = "email-index"
      hash_key        = "email"
      projection_type = "ALL"
    }
  ]

  # Avoid creating extra KMS resources or PITR to match original
  encryption_enabled               = false
  point_in_time_recovery_enabled   = false

  tags = merge(local.common_tags, { Name = "package-tracking-users" })
}

# Addresses Table
module "dynamodb_addresses" {
  source = "../../modules/dynamodb"

  table_name   = "package-tracking-addresses"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "address_id"
  range_key    = null

  attributes = [
    { name = "address_id", type = "S" }
  ]

  encryption_enabled             = false
  point_in_time_recovery_enabled = false

    tags = merge(local.common_tags, { Name = "package-tracking-addresses"})

}

# Depots Table
module "dynamodb_depots" {
  source = "../../modules/dynamodb"

  table_name   = "package-tracking-depots"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "depot_id"
  range_key    = null

  attributes = [
    { name = "depot_id", type = "S" }
  ]

  encryption_enabled             = false
  point_in_time_recovery_enabled = false


  tags = merge(local.common_tags, { Name = "package-tracking-depots" })

}

# Packages Table
module "dynamodb_packages" {
  source = "../../modules/dynamodb"

  table_name   = "package-tracking-packages"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "package_id"
  range_key    = null

  attributes = [
    { name = "package_id", type = "S" },
    { name = "code",       type = "S" },
    { name = "sender_id",  type = "S" },
    { name = "state",      type = "S" }
  ]

  global_secondary_indexes = [
    {
      name            = "code-index"
      hash_key        = "code"
      projection_type = "ALL"
    },
    {
      name            = "sender-index"
      hash_key        = "sender_id"
      projection_type = "ALL"
    },
    {
      name            = "state-index"
      hash_key        = "state"
      projection_type = "ALL"
    }
  ]

  encryption_enabled             = false
  point_in_time_recovery_enabled = false

  tags = merge(local.common_tags, { Name = "package-tracking-packages"})
}

# Tracks Table
module "dynamodb_tracks" {
  source = "../../modules/dynamodb"

  table_name   = "package-tracking-tracks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "track_id"
  range_key    = null

  attributes = [
    { name = "track_id",   type = "S" },
    { name = "package_id", type = "S" }
  ]

  global_secondary_indexes = [
    {
      name            = "package-index"
      hash_key        = "package_id"
      projection_type = "ALL"
    }
  ]

  encryption_enabled             = false
  point_in_time_recovery_enabled = false

    tags = merge(local.common_tags, { Name = "package-tracking-tracks"})

}

# Package Images Table
module "dynamodb_package_images" {
  source = "../../modules/dynamodb"

  table_name   = "package-tracking-images"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "image_id"
  range_key    = null

  attributes = [
    { name = "image_id",   type = "S" },
    { name = "package_id", type = "S" }
  ]

  global_secondary_indexes = [
    {
      name            = "package-index"
      hash_key        = "package_id"
      projection_type = "ALL"
    }
  ]

  encryption_enabled             = false
  point_in_time_recovery_enabled = false
    tags = merge(local.common_tags, { Name = "package-tracking-images" })

}

