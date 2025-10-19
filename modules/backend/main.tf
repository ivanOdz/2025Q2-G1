# COGNITO
resource "aws_cognito_user_pool" "pool" {
  name = "${var.project_name}-user-pool"
  tags = var.tags
}

resource "aws_cognito_user_pool_client" "client" {
  name         = "${var.project_name}-client"
  user_pool_id = aws_cognito_user_pool.pool.id
  generate_secret = false # no secret for public clients -> easier integration with API Gateway
}

# IAM Policies for Lambdas
# base policy
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# dynamo access policy
data "aws_iam_policy_document" "dynamodb_access" {
  statement {
    actions   = [
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem"
    ]
    resources = [var.dynamodb_table_arn, "${var.dynamodb_table_arn}/index/*"]
  }
}
resource "aws_iam_policy" "dynamodb" {
  name   = "${var.project_name}-dynamodb-policy"
  policy = data.aws_iam_policy_document.dynamodb_access.json
}

# SNS publish policy
data "aws_iam_policy_document" "sns_publish" {
  statement {
    actions   = ["sns:Publish"]
    resources = [var.sns_topic_arn]
  }
}
resource "aws_iam_policy" "sns" {
  name   = "${var.project_name}-sns-policy"
  policy = data.aws_iam_policy_document.sns_publish.json
}


# LAMBDAS ---

resource "aws_iam_role" "lambda_roles" {
  # meta-argument 'for_each' to create one role per lambda -> min privilege
  for_each           = var.lambda_handlers_map
  name               = "${var.project_name}-${each.key}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags

  # vpc execution role policy
  managed_policy_arns = ["arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"]
}

# attach dynamo and sns policies to roles
resource "aws_iam_role_policy_attachment" "dynamo_attach" {
  for_each   = var.lambda_handlers_map
  role       = aws_iam_role.lambda_roles[each.key].name
  policy_arn = aws_iam_policy.dynamodb.arn
}
resource "aws_iam_role_policy_attachment" "sns_attach" {
  # ONLY attach sns policy to lambdas that need it
  for_each   = { for k, v in var.lambda_handlers_map : k => v if k != "notifications" }
  role       = aws_iam_role.lambda_roles[each.key].name
  policy_arn = aws_iam_policy.sns.arn
}


# prepare lambda deployment packages
data "archive_file" "lambda_zip" {
  for_each    = var.lambda_handlers_map
  type        = "zip"
  source_dir  = "${path.module}/lambda_src/${each.value}"
  output_path = "${path.module}/.terraform/${each.value}.zip"
}

resource "aws_lambda_function" "lambdas" {
  # meta-argument 'for_each' to create one lambda per handler
  for_each      = var.lambda_handlers_map
  function_name = "${var.project_name}-${each.value}"
  role          = aws_iam_role.lambda_roles[each.key].arn
  handler       = "app.handler" # TODO: app.py and handler functions as entry point (modificaciones en backend)
  runtime       = "python3.12"

  filename         = data.archive_file.lambda_zip[each.key].output_path
  source_code_hash = data.archive_file.lambda_zip[each.key].output_base64sha256

  # setup lambdas in VPC
  vpc_config {
    subnet_ids         = var.lambda_subnet_ids
    # setup security group
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      DYNAMODB_TABLE = split("-", var.dynamodb_table_arn)[-1]
      SNS_TOPIC_ARN  = var.sns_topic_arn
    }
  }

  tags = var.tags
}

# lambda security group
resource "aws_security_group" "lambda_sg" {
  name        = "${var.project_name}-lambda-sg"
  description = "SG para Lambdas en VPC"
  vpc_id      = module.network.vpc_id

  # TODO: mover esto al modulo network y pasarlo como variable a backend?
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = var.tags
}


# API gw
resource "aws_api_gateway_rest_api" "api" {
  name        = "${var.project_name}-api"
  description = "API para el TP de Cloud"
  tags        = var.tags
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
  stage_name  = "v1"
}