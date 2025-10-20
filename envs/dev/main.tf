# Orquestación: invoca módulos locales y externos
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}


# --- network module ---
module "network" {
  source = "../../deprecated_modules/network" # local

  project_name = local.base_name
  vpc_cidr     = "10.0.0.0/16"
  aws_region   = var.aws_region

  tags = merge(local.common_tags, {
    Name = "${local.base_name}-vpc"
  })
}

# --- bd module ---
module "database" {
  source = "../../deprecated_modules/database"

  # meta argument 'depends_on' used outside module
  depends_on = [module.network]

  table_name = "${local.base_name}-table"
  tags       = local.common_tags
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

# --- storage module (S3 buckets) ---
module "storage" {
  source = "../../deprecated_modules/storage"

  project_name = local.base_name
  tags         = local.common_tags
}

# --- backend module (APIgw/lambdas) ---
module "backend" {
  source = "../../deprecated_modules/backend"

  depends_on = [module.network, module.database]

  project_name      = local.base_name
  vpc_id            = module.network.vpc_id
  lambda_subnet_ids = module.network.private_subnet_ids

  dynamodb_table_arn = module.database.table_arn
  sns_topic_arn      = aws_sns_topic.notifications.arn

  images_bucket_name = module.storage.images_bucket_name
  images_bucket_arn  = module.storage.images_bucket_arn

  lambda_handlers_map = var.lambda_handlers

  tags = local.common_tags
}

# --- frontend module ---
module "frontend" {
  source = "../../deprecated_modules/frontend"
  project_name = local.base_name
  tags         = local.common_tags
}