# IAM Configuration
# Contains IAM roles, policies, and data sources

# Usar LabRole existente de AWS Academy
data "aws_iam_role" "lab_role" {
  name = "LabRole"
}
