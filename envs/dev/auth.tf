# Authentication Configuration
# Contains Cognito User Pool and User Pool Client

# --- backend resources (APIgw/lambdas) ---
# COGNITO
resource "aws_cognito_user_pool" "pool" {
  name = "${local.base_name}-user-pool"
  tags = local.common_tags

  # Configurar solo email como método de verificación
  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject = "Your verification code"
    email_message = "Your verification code is {####}"
  }

  # Deshabilitar SMS completamente
  sms_verification_message = null
}

resource "aws_cognito_user_pool_client" "client" {
  name         = "${local.base_name}-client"
  user_pool_id = aws_cognito_user_pool.pool.id
  generate_secret = false # no secret for public clients -> easier integration with API Gateway
  
  # Habilitar flujos de autenticación
  explicit_auth_flows = [
    "ADMIN_NO_SRP_AUTH",
    "USER_PASSWORD_AUTH"
  ]
}
