# Orquestación: invoca módulos locales y externos

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}


# --- VPC module ---
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.5.3"

  name = local.base_name
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  private_subnets = ["${cidrsubnet("10.0.0.0/16", 8, 0)}", "${cidrsubnet("10.0.0.0/16", 8, 1)}"]
  public_subnets  = ["${cidrsubnet("10.0.0.0/16", 8, 100)}", "${cidrsubnet("10.0.0.0/16", 8, 101)}"]

  enable_nat_gateway = true # allow lambdas in private subnets to access internet to download packages or call external APIs
  single_nat_gateway = true

  # VPC Endpoints
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, {
    Name = "${local.base_name}-vpc"
  })
}

# VPC Endpoint para DynamoDB
resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id       = module.vpc.vpc_id
  service_name = "com.amazonaws.${var.aws_region}.dynamodb"
  route_table_ids = concat(
    module.vpc.private_route_table_ids,
    module.vpc.public_route_table_ids
  )
  tags = merge(local.common_tags, { Name = "${local.base_name}-dynamodb-endpoint" })
}

# VPC Endpoint para SQS
resource "aws_vpc_endpoint" "sqs" {
  vpc_id            = module.vpc.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.sqs"
  vpc_endpoint_type = "Interface"
  subnet_ids        = module.vpc.private_subnets
  security_group_ids = [aws_security_group.vpc_endpoints.id]
  tags = merge(local.common_tags, { Name = "${local.base_name}-sqs-endpoint" })
}

# Security Group para VPC Endpoints
resource "aws_security_group" "vpc_endpoints" {
  name        = "${local.base_name}-vpc-endpoints-sg"
  description = "Security group for VPC endpoints"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  tags = local.common_tags
}

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
  encryption_enabled              = true
  point_in_time_recovery_enabled = true
  deletion_protection_enabled    = false  # Set to true for production
  
  tags = local.common_tags
}

# --- events resources ---
# SNS topic
resource "aws_sns_topic" "notifications" {
  name = "${local.base_name}-notifications-topic"
  tags = local.common_tags
}

# SQS queue
resource "aws_sqs_queue" "notifications_queue" {
  name = "${local.base_name}-notifications-queue"
  tags = local.common_tags
}

# SNS -> SQS
resource "aws_sns_topic_subscription" "sns_to_sqs" {
  topic_arn = aws_sns_topic.notifications.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.notifications_queue.arn
}

# QUEUE POLICY to allow SNS to send messages to SQS
data "aws_iam_policy_document" "sqs_policy" {
  statement {
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.notifications_queue.arn]
    principals {
      type        = "Service"
      identifiers = ["sns.amazonaws.com"]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_sns_topic.notifications.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "main" {
  queue_url = aws_sqs_queue.notifications_queue.id
  policy    = data.aws_iam_policy_document.sqs_policy.json
}

# --- backend module (APIgw/lambdas) ---
module "backend" {
  source = "../../deprecated_modules/backend"

  depends_on = [module.vpc, module.dynamodb_table]

  project_name      = local.base_name
  vpc_id            = module.vpc.vpc_id
  lambda_subnet_ids = module.vpc.private_subnets

  dynamodb_table_arn = module.dynamodb_table.table_arn
  sns_topic_arn      = aws_sns_topic.notifications.arn

  images_bucket_name = module.images_bucket.bucket_id
  images_bucket_arn  = module.images_bucket.bucket_arn

  lambda_handlers_map = var.lambda_handlers

  tags = local.common_tags
}
