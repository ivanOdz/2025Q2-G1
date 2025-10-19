module "frontend_bucket" {
  source  = "terraform-aws-modules/s3-bucket/aws" 
  version = "5.8.1" 
  bucket = "${var.project_name}-frontend-bucket"
  tags   = var.tags
  

  website = { 
    index_document = "index.html" 
    error_document = "index.html" 
  }
  

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false


  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid       = "PublicReadGetObject",
        Effect    = "Allow",
        Principal = "*",
        Action    = "s3:GetObject",
        Resource  = [
          format("%s/*", module.frontend_bucket.s3_bucket_arn) 
        ]
      },
    ],
  })
}