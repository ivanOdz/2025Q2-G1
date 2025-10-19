variable "project_name" { type = string }
variable "lambda_subnet_ids" { type = list(string) }
variable "dynamodb_table_arn" { type = string }
variable "sns_topic_arn" { type = string }
variable "lambda_handlers_map" { type = map(string) }
variable "tags" { type = map(string) }