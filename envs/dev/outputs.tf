# Outputs del ambiente

# Events module outputs
output "sns_topic_arn" {
  description = "ARN of the SNS notifications topic"
  value       = aws_sns_topic.notifications.arn
}

output "sqs_queue_arn" {
  description = "ARN of the SQS notifications queue"
  value       = aws_sqs_queue.notifications_queue.arn
}