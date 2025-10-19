module "images_bucket" {
  source  = "terraform-aws-modules/s3-bucket/aws" 
  version = "5.8.1" 
  bucket = "${var.project_name}-images-storage"
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        sse_algorithm = "AES256"
      }
    }
  }

  versioning = {
    enabled = false
  }

  cors_rule = try(
      [
        {
          allowed_headers = ["*"]
          allowed_methods = ["GET", "PUT", "POST", "DELETE"]
          allowed_origins = ["*"]
          expose_headers  = ["ETag"]
          max_age_seconds = 3000
        }
      ],
      []
  )


  lifecycle_rule = [
    { 
      id     = "delete-incomplete-multipart-uploads"
      status = "Enabled"
      
      filter = {}
      
      abort_incomplete_multipart_upload = {
        days_after_initiation = 7
      }
    },
    { 
      id     = "transition-old-images"
      status = "Enabled"
      
      filter = {}
      
      transition = [
        {
          days          = 90
          storage_class = "STANDARD_IA"  
        },
        {
          days          = 365
          storage_class = "GLACIER_IR" 
        }
      ]
    }
  ]
}