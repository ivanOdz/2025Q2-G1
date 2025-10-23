# datasources (AZs, caller identity, etc.)

# Current AWS region
data "aws_region" "current" {}

# Current AWS caller identity
data "aws_caller_identity" "current" {}