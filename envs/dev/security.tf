# Security Configuration
# Contains security groups and security-related resources

# lambda security group
resource "aws_security_group" "lambda_sg" {
  name        = "${local.base_name}-lambda-sg"
  description = "SG para Lambdas en VPC"
  vpc_id      = module.vpc.vpc_id

  # TODO: mover esto al modulo network y pasarlo como variable a backend?
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}
