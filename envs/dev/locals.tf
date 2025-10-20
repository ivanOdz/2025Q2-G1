# locals (naming, prefijos, cálculos)
locals {
  # resources base name
  base_name = "${var.project_name}-serverless"

  common_tags = {
    Project     = var.project_name
    Environment = "dev"
    ManagedBy   = "Terraform"
    Owner       = "Grupo-TP-Cloud"
  }
}