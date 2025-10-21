# Lambda Functions Configuration
# Contains Lambda functions, permissions, and deployment packages

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
      DYNAMODB_TABLE = element(split("/", module.dynamodb_table.table_arn), length(split("/", module.dynamodb_table.table_arn)) - 1)
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
