# Lambda Functions Configuration
## Objetivo: desplegar Lambdas usando el módulo modules/lambda-api, con código desde S3.

# 1) Bucket S3 para artefactos de Lambda (usa var.code_bucket)
module "lambda_code_bucket" {
  source = "../../modules/s3-bucket"

  bucket_name       = var.code_bucket
  tags              = local.common_tags
  versioning_enabled = true
  encryption_algorithm = "AES256"
}



resource "aws_s3_object" "lambda_artifacts" {
  for_each = var.lambda_handlers

  bucket       = module.lambda_code_bucket.bucket_id
  key          = "lambda/${each.value}.zip"
  source       = "${path.module}/${var.lambda_zip_path}/${each.value}.zip"
  content_type = "application/zip"

  # Forzar actualización cuando cambie el ZIP local
  etag = filemd5("${var.lambda_zip_path}/${each.value}.zip")
}

# 3) Crear Lambdas con el módulo, una por handler
module "lambdas" {
  source = "../../modules/lambda-api"

  for_each = var.lambda_handlers

  name_prefix  = local.base_name
  function_key = each.key
  handler      = "${each.value}.lambda_handler"
  role_arn     = data.aws_iam_role.lab_role.arn

  runtime   = "python3.12"
  timeout_s = 15
  memory_mb = 256

  # Código desde S3
  code_bucket         = module.lambda_code_bucket.bucket_id
  s3_key              = aws_s3_object.lambda_artifacts[each.key].key
  s3_object_version   = aws_s3_object.lambda_artifacts[each.key].version_id
  source_code_hash_b64 = filebase64sha256("${var.lambda_zip_path}/${each.value}.zip")

  # VPC
  subnet_ids = module.vpc.private_subnets
  sg_ids     = [aws_security_group.lambda_sg.id]

  # Variables de entorno usadas por los handlers
  env = {
    SNS_TOPIC_ARN  = aws_sns_topic.notifications.arn,
    S3_BUCKET_NAME = module.images_bucket.bucket_id
  }

  # Garantizar que primero se creen bucket y objetos
  depends_on = [module.lambda_code_bucket, aws_s3_object.lambda_artifacts, module.vpc,aws_sns_topic.notifications]
}

# 4) Permisos para que API Gateway invoque cada Lambda
resource "aws_lambda_permission" "api_gateway_invoke" {
  for_each      = var.lambda_handlers
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.lambdas[each.key].function_name
  principal     = "apigateway.amazonaws.com"

  # Permite que este API Gateway invoque desde cualquier endpoint
  source_arn = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}
