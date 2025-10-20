# external vpc module
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.5.3"

  name = var.project_name
  cidr = var.vpc_cidr

  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  private_subnets = ["${cidrsubnet(var.vpc_cidr, 8, 0)}", "${cidrsubnet(var.vpc_cidr, 8, 1)}"]
  public_subnets  = ["${cidrsubnet(var.vpc_cidr, 8, 100)}", "${cidrsubnet(var.vpc_cidr, 8, 101)}"]

  enable_nat_gateway = true # allow lambdas in private subnets to access internet to download packages or call external APIs
  single_nat_gateway = true

  # VPC Endpoints
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = var.tags
}

# VPC Endpoint para DynamoDB
resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id       = module.vpc.vpc_id
  service_name = "com.amazonaws.${var.aws_region}.dynamodb"
  route_table_ids = concat(
    module.vpc.private_route_table_ids,
    module.vpc.public_route_table_ids
  )
  tags = merge(var.tags, { Name = "${var.project_name}-dynamodb-endpoint" })
}

# VPC Endpoint para SQS
resource "aws_vpc_endpoint" "sqs" {
  vpc_id            = module.vpc.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.sqs"
  vpc_endpoint_type = "Interface"
  subnet_ids        = module.vpc.private_subnets
  security_group_ids = [aws_security_group.vpc_endpoints.id]
  tags = merge(var.tags, { Name = "${var.project_name}-sqs-endpoint" })
}

# Security Group para VPC Endpoints
resource "aws_security_group" "vpc_endpoints" {
  name        = "${var.project_name}-vpc-endpoints-sg"
  description = "Security group for VPC endpoints"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = var.tags
}