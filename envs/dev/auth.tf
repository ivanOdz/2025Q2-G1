# Authentication Configuration
# Contains Cognito User Pool and User Pool Client

# --- backend resources (APIgw/lambdas) ---
# COGNITO
resource "aws_cognito_user_pool" "pool" {
  name = "${local.base_name}-user-pool"
  tags = local.common_tags
}

resource "aws_cognito_user_pool_client" "client" {
  name         = "${local.base_name}-client"
  user_pool_id = aws_cognito_user_pool.pool.id
  generate_secret = false # no secret for public clients -> easier integration with API Gateway
}
