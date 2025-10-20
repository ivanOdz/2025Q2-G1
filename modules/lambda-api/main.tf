 # API Lambda + IAM + logs
 locals {
  fn_name = "${var.name_prefix}-${var.function_key}"
}

# Log group explícito para controlar retención
resource "aws_cloudwatch_log_group" "lg" {
  name              = "/aws/lambda/${local.fn_name}"
  retention_in_days = var.log_retention_in_days

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_lambda_function" "this" {
  function_name = local.fn_name
  role          = var.role_arn
  runtime       = var.runtime
  handler       = var.handler

  # Código desde S3
  s3_bucket         = var.code_bucket
  s3_key            = var.s3_key
  s3_object_version = var.s3_object_version

  # Hash para detectar cambios y desplegar
  source_code_hash = var.source_code_hash_b64

  memory_size   = var.memory_mb
  timeout       = var.timeout_s
  architectures = var.architectures
  publish       = var.publish

  environment {
    variables = var.env
  }

  dynamic "vpc_config" {
    for_each = length(var.subnet_ids) > 0 ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = var.sg_ids
    }
  }

  layers = var.layers

  depends_on = [aws_cloudwatch_log_group.lg]
}
