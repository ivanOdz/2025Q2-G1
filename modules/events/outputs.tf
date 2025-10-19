output "sns_topic_arn" {
  value = aws_sns_topic.notifications.arn
}

output "sqs_queue_arn" {
  value = aws_sqs_queue.notifications_queue.arn
}