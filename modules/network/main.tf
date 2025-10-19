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

  enable_dynamodb_endpoint = true

  enable_sqs_endpoint = true

  tags = var.tags
}