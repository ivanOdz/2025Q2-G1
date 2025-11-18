# Events Configuration
# Contains SNS topic, SQS queue, and related policies

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

# Lambda Event Source Mapping: SQS -> Lambda
# This connects the SQS queue to the notifications Lambda function
resource "aws_lambda_event_source_mapping" "sqs_to_notifications" {
  event_source_arn = aws_sqs_queue.notifications_queue.arn
  function_name    = module.lambdas["notifications"].function_name
  batch_size       = 10
  enabled          = true

  depends_on = [
    module.lambdas["notifications"],
    aws_sqs_queue.notifications_queue
  ]
}

# IAM Permission for SQS to invoke Lambda
resource "aws_lambda_permission" "sqs_invoke_notifications" {
  statement_id  = "AllowSQSToInvokeNotificationsLambda"
  action        = "lambda:InvokeFunction"
  function_name = module.lambdas["notifications"].function_name
  principal     = "sqs.amazonaws.com"
  source_arn    = aws_sqs_queue.notifications_queue.arn
}
