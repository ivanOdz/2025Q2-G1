# Estado remoto (S3/DynamoDB) SOLO tenemos que configurarla aca en modulos es una instancia generica

# --- S3 Storage (images bucket) ---
module "images_bucket" {
  source = "../../modules/s3-bucket"
  
  bucket_name = var.images_bucket
  tags        = local.common_tags
  
  # Public access block configuration (secure defaults)
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  # Encryption configuration
  encryption_algorithm = "AES256"
  
  # Versioning configuration
  versioning_enabled = false

  # CORS configuration
  cors_rules = [
    {
      allowed_headers = ["*"]
      allowed_methods = ["GET", "PUT", "POST", "DELETE"]
      allowed_origins = ["*"]
      expose_headers  = ["ETag"]
      max_age_seconds = 3000
    }
  ]

  # Lifecycle configuration
  lifecycle_rules = [
    {
      id     = "delete-incomplete-multipart-uploads"
      status = "Enabled"
      filter = null
      expiration = null
      transitions = null
      noncurrent_version_expiration = null
      noncurrent_version_transitions = null
      abort_incomplete_multipart_upload = {
        days_after_initiation = 7
      }
    },
    {
      id     = "transition-old-images"
      status = "Enabled"
      filter = null
      expiration = null
      transitions = [
        {
          days          = 90
          storage_class = "STANDARD_IA"
        },
        {
          days          = 365
          storage_class = "GLACIER_IR"
        }
      ]
      noncurrent_version_expiration = null
      noncurrent_version_transitions = null
      abort_incomplete_multipart_upload = null
    }
  ]
}

# --- S3 Frontend Bucket (Static Website) ---
module "frontend_bucket" {
  source = "../../modules/s3-bucket"
  
  bucket_name = var.frontend_bucket
  tags        = local.common_tags
  
  # Public access block configuration (disabled for static website)
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false

  # Website configuration
  website_configuration = {
    index_document = "index.html"
    error_document = "index.html"
    routing_rules  = null
  }
}

# Bucket policy for frontend bucket public read access
resource "aws_s3_bucket_policy" "frontend_bucket_policy" {
  bucket = module.frontend_bucket.bucket_id
  
  # Ensure public access block is configured before applying policy
  depends_on = [module.frontend_bucket]
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid       = "PublicReadGetObject",
        Effect    = "Allow",
        Principal = "*",
        Action    = "s3:GetObject",
        Resource  = [
          format("%s/*", module.frontend_bucket.bucket_arn) 
        ]
      },
    ],
  })
}


