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

# --- backend resources (APIgw/lambdas) ---
# COGNITO
resource "aws_cognito_user_pool" "pool" {
  name = "${local.base_name}-user-pool"
  tags = local.common_tags
}

resource "aws_cognito_user_pool_client" "client" {
  name         = "${local.base_name}-client"
  user_pool_id = aws_cognito_user_pool.pool.id
  generate_secret = false # no secret for public clients -> easier integration with API Gateway
}

# Usar LabRole existente de AWS Academy
data "aws_iam_role" "lab_role" {
  name = "LabRole"
}

# prepare lambda deployment packages
data "archive_file" "lambda_zip" {
  for_each    = var.lambda_handlers
  type        = "zip"
  source_dir  = "../../deprecated_modules/backend/lambda_src/${each.value}" //TODO change path to use S3 bucket code packages
  output_path = "../../deprecated_modules/backend/.terraform/${each.value}.zip" 
}

resource "aws_lambda_function" "lambdas" {
  # meta-argument 'for_each' to create one lambda per handler
  for_each      = var.lambda_handlers
  function_name = "${local.base_name}-${each.value}"
  role          = data.aws_iam_role.lab_role.arn
  handler       = "app.handler" # TODO: app.py and handler functions as entry point (modificaciones en backend)
  runtime       = "python3.12"

  filename         = data.archive_file.lambda_zip[each.key].output_path
  source_code_hash = data.archive_file.lambda_zip[each.key].output_base64sha256

  # setup lambdas in VPC
  vpc_config {
    subnet_ids         = module.vpc.private_subnets
    # setup security group
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      DYNAMODB_TABLE = element(split("/", aws_dynamodb_table.main.arn), length(split("/", aws_dynamodb_table.main.arn)) - 1)
      SNS_TOPIC_ARN  = aws_sns_topic.notifications.arn
      IMAGES_BUCKET  = module.images_bucket.bucket_id
    }
  }

  tags = local.common_tags
}

# Lambda permissions para que API Gateway pueda invocar todas las lambdas
resource "aws_lambda_permission" "api_gateway_invoke" {
  for_each      = var.lambda_handlers
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambdas[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  
  # Permite que este API Gateway invoque desde cualquier endpoint
  source_arn = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

# lambda security group
resource "aws_security_group" "lambda_sg" {
  name        = "${local.base_name}-lambda-sg"
  description = "SG para Lambdas en VPC"
  vpc_id      = module.vpc.vpc_id

  # TODO: mover esto al modulo network y pasarlo como variable a backend?
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

# API gw
resource "aws_api_gateway_rest_api" "api" {
  name        = "${local.base_name}-api"
  description = "API para el TP de Cloud"
  tags        = local.common_tags
}

# cognito authorizer for API gw
resource "aws_api_gateway_authorizer" "cognito" {
  name                   = "Cognito-Authorizer"
  type                   = "COGNITO_USER_POOLS"
  rest_api_id            = aws_api_gateway_rest_api.api.id
  provider_arns          = [aws_cognito_user_pool.pool.arn]
}

# TODO: definir todo lo que va en cada lambda (endpoints, recursos,etc)
resource "aws_api_gateway_resource" "packages" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "packages"
}

# POST /packages
resource "aws_api_gateway_method" "post_packages" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.packages.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS" # ¡Protegido!
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "post_packages_lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages.id
  http_method = aws_api_gateway_method.post_packages.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY" # proxies to lambda
  uri                     = aws_lambda_function.lambdas["packages"].invoke_arn
}

resource "aws_api_gateway_deployment" "api_deploy" {
  # meta-argument 'depends_on' to ensure all integrations are created before deployment
  depends_on = [
    aws_api_gateway_integration.post_packages_lambda,
  ]

  rest_api_id = aws_api_gateway_rest_api.api.id
}

