# API Gateway Configuration
# Contains REST API, resources, methods, integrations, and deployment

# API gw
resource "aws_api_gateway_rest_api" "api" {
  name        = "${local.base_name}-api"
  description = "API para el TP de Cloud"
  tags        = local.common_tags
}

# cognito authorizer for API gw
resource "aws_api_gateway_authorizer" "cognito" {
  name                   = "Cognito-Authorizer"
  type                   = "COGNITO_USER_POOLS"
  rest_api_id            = aws_api_gateway_rest_api.api.id
  provider_arns          = [aws_cognito_user_pool.pool.arn]
}

# TODO: definir todo lo que va en cada lambda (endpoints, recursos,etc)
resource "aws_api_gateway_resource" "packages" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  
  lifecycle {
    # Helps avoid AWS timing issues when replacing deployments that still
    # have active stages pointing to the previous one.
    create_before_destroy = true
  }
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "packages"
}

# Tracks resource
resource "aws_api_gateway_resource" "tracks" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  
  lifecycle {
    create_before_destroy = true
  }
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "tracks"
}

# Packages/{code} resource for individual package operations
resource "aws_api_gateway_resource" "packages_code" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  
  lifecycle {
    create_before_destroy = true
  }
  parent_id   = aws_api_gateway_resource.packages.id
  path_part   = "{code}"
}

# Packages/{code}/images resource for package images
resource "aws_api_gateway_resource" "packages_code_images" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  
  lifecycle {
    create_before_destroy = true
  }
  parent_id   = aws_api_gateway_resource.packages_code.id
  path_part   = "images"
}

# Packages/{code}/tracks resource for package tracks
resource "aws_api_gateway_resource" "packages_code_tracks" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  
  lifecycle {
    create_before_destroy = true
  }
  parent_id   = aws_api_gateway_resource.packages_code.id
  path_part   = "tracks"
}

# Packages/{code}/tracks/latest resource for latest track
resource "aws_api_gateway_resource" "packages_code_tracks_latest" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  
  lifecycle {
    create_before_destroy = true
  }
  parent_id   = aws_api_gateway_resource.packages_code_tracks.id
  path_part   = "latest"
}

# Addresses resource
resource "aws_api_gateway_resource" "addresses" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  
  lifecycle {
    create_before_destroy = true
  }
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "addresses"
}

# Addresses/{id} resource for individual address operations
resource "aws_api_gateway_resource" "addresses_id" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  
  lifecycle {
    create_before_destroy = true
  }
  parent_id   = aws_api_gateway_resource.addresses.id
  path_part   = "{id}"
}

# Depots resource
resource "aws_api_gateway_resource" "depots" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  
  lifecycle {
    create_before_destroy = true
  }
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "depots"
}

# Depots/{id} resource for individual depot operations
resource "aws_api_gateway_resource" "depots_id" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  
  lifecycle {
    create_before_destroy = true
  }
  parent_id   = aws_api_gateway_resource.depots.id
  path_part   = "{id}"
}

# POST /packages
resource "aws_api_gateway_method" "post_packages" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.packages.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS" # ¡Protegido!
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "post_packages_lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages.id
  http_method = aws_api_gateway_method.post_packages.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY" # proxies to lambda
  uri                     = module.lambdas["packages"].function_invoke_arn
}

# GET /packages
resource "aws_api_gateway_method" "get_packages" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.packages.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS" # Protected endpoint
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "get_packages_lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages.id
  http_method = aws_api_gateway_method.get_packages.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY" # proxies to lambda
  uri                     = module.lambdas["packages"].function_invoke_arn
}

# GET /packages/{code}
resource "aws_api_gateway_method" "get_packages_code" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.packages_code.id
  http_method   = "GET"
  authorization = "NONE" # Public endpoint for package lookup
}

resource "aws_api_gateway_integration" "get_packages_code_lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages_code.id
  http_method = aws_api_gateway_method.get_packages_code.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY" # proxies to lambda
  uri                     = module.lambdas["packages"].function_invoke_arn
}

# GET /packages/{code}/images (for requesting upload URL)
resource "aws_api_gateway_method" "get_packages_code_images" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.packages_code_images.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS" # Protected endpoint
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

# POST /packages/{code}/images (for uploading via multipart - keeping for now)
resource "aws_api_gateway_method" "post_packages_code_images" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.packages_code_images.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS" # Protected endpoint
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

# Integration for GET /packages/{code}/images (pre-signed URL)
resource "aws_api_gateway_integration" "get_packages_code_images_lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages_code_images.id
  http_method = aws_api_gateway_method.get_packages_code_images.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY" # Use proxy for simple requests
  uri                     = module.lambdas["images"].function_invoke_arn
}

# Integration for POST /packages/{code}/images (multipart upload - keeping for now)
resource "aws_api_gateway_integration" "post_packages_code_images_lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages_code_images.id
  http_method = aws_api_gateway_method.post_packages_code_images.http_method

  integration_http_method = "POST"
  type                    = "AWS" # Use AWS integration instead of proxy
  uri                     = module.lambdas["images"].function_invoke_arn
  
  # Add mapping template for multipart/form-data
  request_templates = {
    "multipart/form-data" = jsonencode({
      "body" = "$input.body"
      "isBase64Encoded" = true
    })
  }
}

# GET /packages/{code}/tracks
resource "aws_api_gateway_method" "get_packages_code_tracks" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.packages_code_tracks.id
  http_method   = "GET"
  authorization = "NONE" # Public endpoint for track lookups
}

resource "aws_api_gateway_integration" "get_packages_code_tracks_lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages_code_tracks.id
  http_method = aws_api_gateway_method.get_packages_code_tracks.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY" # proxies to lambda
  uri                     = module.lambdas["tracks"].function_invoke_arn
}

# GET /packages/{code}/tracks/latest
resource "aws_api_gateway_method" "get_packages_code_tracks_latest" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.packages_code_tracks_latest.id
  http_method   = "GET"
  authorization = "NONE" # Public endpoint for latest track lookup
}

resource "aws_api_gateway_integration" "get_packages_code_tracks_latest_lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages_code_tracks_latest.id
  http_method = aws_api_gateway_method.get_packages_code_tracks_latest.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY" # proxies to lambda
  uri                     = module.lambdas["tracks"].function_invoke_arn
}

# POST /packages/{code}/tracks
resource "aws_api_gateway_method" "post_packages_code_tracks" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.packages_code_tracks.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS" # Protected endpoint
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "post_packages_code_tracks_lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages_code_tracks.id
  http_method = aws_api_gateway_method.post_packages_code_tracks.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY" # proxies to lambda
  uri                     = module.lambdas["tracks"].function_invoke_arn
}

# POST /addresses
resource "aws_api_gateway_method" "post_addresses" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.addresses.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS" # Protected endpoint
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "post_addresses_lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.addresses.id
  http_method = aws_api_gateway_method.post_addresses.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY" # proxies to lambda
  uri                     = module.lambdas["address"].function_invoke_arn
}

# GET /addresses
resource "aws_api_gateway_method" "get_addresses" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.addresses.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS" # Protected endpoint
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "get_addresses_lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.addresses.id
  http_method = aws_api_gateway_method.get_addresses.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY" # proxies to lambda
  uri                     = module.lambdas["address"].function_invoke_arn
}

# GET /addresses/{id}
resource "aws_api_gateway_method" "get_addresses_id" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.addresses_id.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS" # Protected endpoint
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "get_addresses_id_lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.addresses_id.id
  http_method = aws_api_gateway_method.get_addresses_id.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY" # proxies to lambda
  uri                     = module.lambdas["address"].function_invoke_arn
}
# GET /depots
resource "aws_api_gateway_method" "get_depots" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.depots.id
  http_method   = "GET"
  authorization = "NONE" # Public endpoint for depot lookups
}

resource "aws_api_gateway_integration" "get_depots_lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.depots.id
  http_method = aws_api_gateway_method.get_depots.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY" # proxies to lambda
  uri                     = module.lambdas["depots"].function_invoke_arn
}

# GET /depots/{id}
resource "aws_api_gateway_method" "get_depots_id" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.depots_id.id
  http_method   = "GET"
  authorization = "NONE" # Public endpoint for individual depot lookup
}

resource "aws_api_gateway_integration" "get_depots_id_lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.depots_id.id
  http_method = aws_api_gateway_method.get_depots_id.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY" # proxies to lambda
  uri                     = module.lambdas["depots"].function_invoke_arn
}

resource "aws_api_gateway_deployment" "api_deploy" {
  # meta-argument 'depends_on' to ensure all integrations are created before deployment
  depends_on = [
    aws_api_gateway_integration.post_packages_lambda,
    aws_api_gateway_integration.get_packages_lambda,
    aws_api_gateway_integration.get_packages_code_lambda,
    aws_api_gateway_integration.get_packages_code_images_lambda,
    aws_api_gateway_integration.post_packages_code_images_lambda,
    aws_api_gateway_integration.get_packages_code_tracks_lambda,
    aws_api_gateway_integration.get_packages_code_tracks_latest_lambda,
    aws_api_gateway_integration.post_packages_code_tracks_lambda,
    aws_api_gateway_integration.post_addresses_lambda,
    aws_api_gateway_integration.get_addresses_lambda,
    aws_api_gateway_integration.get_addresses_id_lambda,
    aws_api_gateway_integration.get_depots_lambda,
    aws_api_gateway_integration.get_depots_id_lambda,
    aws_api_gateway_integration.options_packages_mock,
    aws_api_gateway_integration.options_packages_code_mock,
    aws_api_gateway_integration.options_addresses_mock,
    aws_api_gateway_integration.options_addresses_id_mock,
    aws_api_gateway_integration.options_depots_mock,
    aws_api_gateway_integration.options_depots_id_mock,
    aws_api_gateway_integration.options_tracks_mock,
    aws_api_gateway_integration.options_packages_code_tracks_mock,
    aws_api_gateway_integration.options_packages_code_tracks_latest_mock,
    aws_api_gateway_integration.options_packages_code_images_mock
  ]

  rest_api_id = aws_api_gateway_rest_api.api.id
  
  # Forzar nuevo deployment cuando cambie la autorización
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_method.post_packages.authorization,
      aws_api_gateway_integration.post_packages_lambda.uri,
      aws_api_gateway_integration.get_packages_lambda.uri,
      aws_api_gateway_integration.get_packages_code_lambda.uri,
      aws_api_gateway_integration.get_packages_code_images_lambda.uri,
      aws_api_gateway_integration.post_packages_code_images_lambda.uri,
      aws_api_gateway_integration.get_packages_code_tracks_lambda.uri,
      aws_api_gateway_integration.get_packages_code_tracks_latest_lambda.uri,
      aws_api_gateway_integration.post_packages_code_tracks_lambda.uri,
      aws_api_gateway_integration.post_addresses_lambda.uri,
      aws_api_gateway_integration.get_addresses_lambda.uri,
      aws_api_gateway_integration.get_addresses_id_lambda.uri,
      aws_api_gateway_integration.get_depots_lambda.uri,
      aws_api_gateway_integration.get_depots_id_lambda.uri,
      aws_api_gateway_method.options_packages.http_method,
      aws_api_gateway_method.options_packages_code.http_method,
      aws_api_gateway_method.options_addresses.http_method,
      aws_api_gateway_method.options_addresses_id.http_method,
      aws_api_gateway_method.options_depots.http_method,
      aws_api_gateway_method.options_depots_id.http_method,
      aws_api_gateway_method.options_tracks.http_method,
      aws_api_gateway_method.options_packages_code_tracks.http_method,
      aws_api_gateway_method.options_packages_code_tracks_latest.http_method,
      aws_api_gateway_method.options_packages_code_images.http_method,
      aws_api_gateway_integration.options_packages_mock.type,
      aws_api_gateway_integration.options_packages_code_mock.type,
      aws_api_gateway_integration.options_addresses_mock.type,
      aws_api_gateway_integration.options_addresses_id_mock.type,
      aws_api_gateway_integration.options_depots_mock.type,
      aws_api_gateway_integration.options_depots_id_mock.type,
      aws_api_gateway_integration.options_tracks_mock.type,
      aws_api_gateway_integration.options_packages_code_tracks_mock.type,
      aws_api_gateway_integration.options_packages_code_tracks_latest_mock.type,
      aws_api_gateway_integration.options_packages_code_images_mock.type
    ]))
  }
}

# Stage para el API Gateway
resource "aws_api_gateway_stage" "api_stage" {
  deployment_id = aws_api_gateway_deployment.api_deploy.id
  rest_api_id   = aws_api_gateway_rest_api.api.id
  stage_name    = "api"
}

# -----------------------------------------------------------------
# CORS Configuration for all endpoints
# -----------------------------------------------------------------

# OPTIONS /packages
resource "aws_api_gateway_method" "options_packages" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.packages.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_packages_mock" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages.id
  http_method = aws_api_gateway_method.options_packages.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_packages_200" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages.id
  http_method = aws_api_gateway_method.options_packages.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true,
    "method.response.header.Access-Control-Allow-Methods" = true,
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_packages_200_response" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages.id
  http_method = aws_api_gateway_method.options_packages.http_method
  status_code = aws_api_gateway_method_response.options_packages_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'",
    "method.response.header.Access-Control-Allow-Methods" = "'GET, POST, OPTIONS'",
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token'"
  }

  depends_on = [aws_api_gateway_integration.options_packages_mock]
}

# OPTIONS /packages/{code}
resource "aws_api_gateway_method" "options_packages_code" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.packages_code.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_packages_code_mock" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages_code.id
  http_method = aws_api_gateway_method.options_packages_code.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

# OPTIONS response
resource "aws_api_gateway_method_response" "options_packages_code_200" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages_code.id
  http_method = aws_api_gateway_method.options_packages_code.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true,
    "method.response.header.Access-Control-Allow-Methods" = true,
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_packages_code_200_response" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages_code.id
  http_method = aws_api_gateway_method.options_packages_code.http_method
  status_code = aws_api_gateway_method_response.options_packages_code_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'",
    "method.response.header.Access-Control-Allow-Methods" = "'GET, OPTIONS'",
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token'"
  }

  depends_on = [aws_api_gateway_integration.options_packages_code_mock]
}

# OPTIONS /addresses
resource "aws_api_gateway_method" "options_addresses" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.addresses.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_addresses_mock" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.addresses.id
  http_method = aws_api_gateway_method.options_addresses.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_addresses_200" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.addresses.id
  http_method = aws_api_gateway_method.options_addresses.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true,
    "method.response.header.Access-Control-Allow-Methods" = true,
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_addresses_200_response" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.addresses.id
  http_method = aws_api_gateway_method.options_addresses.http_method
  status_code = aws_api_gateway_method_response.options_addresses_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'",
    "method.response.header.Access-Control-Allow-Methods" = "'GET, POST, OPTIONS'",
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token'"
  }

  depends_on = [aws_api_gateway_integration.options_addresses_mock]
}

# OPTIONS /addresses/{id}
resource "aws_api_gateway_method" "options_addresses_id" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.addresses_id.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_addresses_id_mock" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.addresses_id.id
  http_method = aws_api_gateway_method.options_addresses_id.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_addresses_id_200" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.addresses_id.id
  http_method = aws_api_gateway_method.options_addresses_id.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true,
    "method.response.header.Access-Control-Allow-Methods" = true,
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_addresses_id_200_response" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.addresses_id.id
  http_method = aws_api_gateway_method.options_addresses_id.http_method
  status_code = aws_api_gateway_method_response.options_addresses_id_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'",
    "method.response.header.Access-Control-Allow-Methods" = "'GET, OPTIONS'",
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token'"
  }

  depends_on = [aws_api_gateway_integration.options_addresses_id_mock]
}

# OPTIONS /depots
resource "aws_api_gateway_method" "options_depots" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.depots.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_depots_mock" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.depots.id
  http_method = aws_api_gateway_method.options_depots.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_depots_200" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.depots.id
  http_method = aws_api_gateway_method.options_depots.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true,
    "method.response.header.Access-Control-Allow-Methods" = true,
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_depots_200_response" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.depots.id
  http_method = aws_api_gateway_method.options_depots.http_method
  status_code = aws_api_gateway_method_response.options_depots_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'",
    "method.response.header.Access-Control-Allow-Methods" = "'GET, OPTIONS'",
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token'"
  }

  depends_on = [aws_api_gateway_integration.options_depots_mock]
}

# OPTIONS /depots/{id}
resource "aws_api_gateway_method" "options_depots_id" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.depots_id.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_depots_id_mock" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.depots_id.id
  http_method = aws_api_gateway_method.options_depots_id.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_depots_id_200" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.depots_id.id
  http_method = aws_api_gateway_method.options_depots_id.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true,
    "method.response.header.Access-Control-Allow-Methods" = true,
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_depots_id_200_response" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.depots_id.id
  http_method = aws_api_gateway_method.options_depots_id.http_method
  status_code = aws_api_gateway_method_response.options_depots_id_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'",
    "method.response.header.Access-Control-Allow-Methods" = "'GET, OPTIONS'",
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token'"
  }

  depends_on = [aws_api_gateway_integration.options_depots_id_mock]
}

# OPTIONS /tracks
resource "aws_api_gateway_method" "options_tracks" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.tracks.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_tracks_mock" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.tracks.id
  http_method = aws_api_gateway_method.options_tracks.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_tracks_200" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.tracks.id
  http_method = aws_api_gateway_method.options_tracks.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true,
    "method.response.header.Access-Control-Allow-Methods" = true,
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_tracks_200_response" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.tracks.id
  http_method = aws_api_gateway_method.options_tracks.http_method
  status_code = aws_api_gateway_method_response.options_tracks_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'",
    "method.response.header.Access-Control-Allow-Methods" = "'GET, OPTIONS'",
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token'"
  }

  depends_on = [aws_api_gateway_integration.options_tracks_mock]
}

# OPTIONS /packages/{code}/tracks
resource "aws_api_gateway_method" "options_packages_code_tracks" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.packages_code_tracks.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_packages_code_tracks_mock" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages_code_tracks.id
  http_method = aws_api_gateway_method.options_packages_code_tracks.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_packages_code_tracks_200" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages_code_tracks.id
  http_method = aws_api_gateway_method.options_packages_code_tracks.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true,
    "method.response.header.Access-Control-Allow-Methods" = true,
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_packages_code_tracks_200_response" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages_code_tracks.id
  http_method = aws_api_gateway_method.options_packages_code_tracks.http_method
  status_code = aws_api_gateway_method_response.options_packages_code_tracks_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'",
    "method.response.header.Access-Control-Allow-Methods" = "'GET, POST, OPTIONS'",
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token'"
  }

  depends_on = [aws_api_gateway_integration.options_packages_code_tracks_mock]
}

# OPTIONS /packages/{code}/tracks/latest
resource "aws_api_gateway_method" "options_packages_code_tracks_latest" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.packages_code_tracks_latest.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_packages_code_tracks_latest_mock" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages_code_tracks_latest.id
  http_method = aws_api_gateway_method.options_packages_code_tracks_latest.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_packages_code_tracks_latest_200" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages_code_tracks_latest.id
  http_method = aws_api_gateway_method.options_packages_code_tracks_latest.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true,
    "method.response.header.Access-Control-Allow-Methods" = true,
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_packages_code_tracks_latest_200_response" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages_code_tracks_latest.id
  http_method = aws_api_gateway_method.options_packages_code_tracks_latest.http_method
  status_code = aws_api_gateway_method_response.options_packages_code_tracks_latest_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'",
    "method.response.header.Access-Control-Allow-Methods" = "'GET, OPTIONS'",
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token'"
  }

  depends_on = [aws_api_gateway_integration.options_packages_code_tracks_latest_mock]
}

# OPTIONS /packages/{code}/images
resource "aws_api_gateway_method" "options_packages_code_images" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.packages_code_images.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_packages_code_images_mock" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages_code_images.id
  http_method = aws_api_gateway_method.options_packages_code_images.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_packages_code_images_200" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages_code_images.id
  http_method = aws_api_gateway_method.options_packages_code_images.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true,
    "method.response.header.Access-Control-Allow-Methods" = true,
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_packages_code_images_200_response" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.packages_code_images.id
  http_method = aws_api_gateway_method.options_packages_code_images.http_method
  status_code = aws_api_gateway_method_response.options_packages_code_images_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = "'*'",
    "method.response.header.Access-Control-Allow-Methods" = "'GET, POST, OPTIONS'",
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token'"
  }

  depends_on = [aws_api_gateway_integration.options_packages_code_images_mock]
}


# ERROR responses---

# 4XX
resource "aws_api_gateway_gateway_response" "cors_4xx" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  response_type = "DEFAULT_4XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'"
  }
}

# 5XX
resource "aws_api_gateway_gateway_response" "cors_5xx" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  response_type = "DEFAULT_5XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'"
  }
}