# SNS topic
resource "aws_sns_topic" "notifications" {
  name = "${var.project_name}-notifications-topic"
  tags = var.tags
}

# SQS queue
resource "aws_sqs_queue" "notifications_queue" {
  name = "${var.project_name}-notifications-queue"
  tags = var.tags
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

# SQS -> Lambda in backend module to avoid circular dependency
