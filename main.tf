terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  # resources base name
  base_name = "${var.project_name}-serverless"

  common_tags = {
    Project     = var.project_name
    Environment = "dev"
    ManagedBy   = "Terraform"
    Owner       = "Grupo-TP-Cloud"
  }
}

# --- network module ---
module "network" {
  source = "./modules/network" # local

  project_name = local.base_name
  vpc_cidr     = "10.0.0.0/16"
  aws_region   = var.aws_region

  tags = merge(local.common_tags, {
    Name = "${local.base_name}-vpc"
  })
}

# --- bd module ---
module "database" {
  source = "./modules/database"

  # meta argument 'depends_on' used outside module
  depends_on = [module.network]

  table_name = "${local.base_name}-table"
  tags       = local.common_tags
}

# --- event module ---
module "events" {
  source = "./modules/events"

  project_name  = local.base_name
  account_id    = data.aws_caller_identity.current.account_id
  region        = data.aws_region.current.name
  tags          = local.common_tags
}

# --- backend module (APIgw/lambdas) ---
module "backend" {
  source = "./modules/backend"

  depends_on = [module.network, module.database, module.events]

  project_name      = local.base_name
  lambda_subnet_ids = module.network.private_subnet_ids

  dynamodb_table_arn = module.database.table_arn
  sns_topic_arn      = module.events.sns_topic_arn

  lambda_handlers_map = var.lambda_handlers

  tags = local.common_tags
}

# --- frontend module ---
module "frontend" {
  source = "./modules/frontend"

  project_name = local.base_name
  account_id   = data.aws_caller_identity.current.account_id
  tags         = local.common_tags
}