# Bucket para imágenes subidas por usuarios
resource "aws_s3_bucket" "images" {
  bucket = "${var.project_name}-images-bucket"
  tags   = var.tags
}

resource "aws_s3_bucket_versioning" "images_versioning" {
  bucket = aws_s3_bucket.images.id
  versioning_configuration {
    status = "Disabled"
  }
}

# CORS para permitir uploads desde el frontend
resource "aws_s3_bucket_cors_configuration" "images_cors" {
  bucket = aws_s3_bucket.images.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE"]
    allowed_origins = ["*"]  # TODO: cambiar por dominio específico en producción
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# Block public access (acceso via pre-signed URLs solamente)
resource "aws_s3_bucket_public_access_block" "images_private" {
  bucket = aws_s3_bucket.images.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy para limpiar uploads incompletos
resource "aws_s3_bucket_lifecycle_configuration" "images_lifecycle" {
  bucket = aws_s3_bucket.images.id

  rule {
    id     = "delete-incomplete-multipart-uploads"
    status = "Enabled"
    filter {}
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  rule {
    id     = "transition-old-images"
    status = "Enabled"
    filter {}

    transition {
      days          = 90
      storage_class = "STANDARD_IA"  # Infrequent Access (más barato)
    }

    transition {
      days          = 365
      storage_class = "GLACIER_IR"  # Aún más barato
    }
  }
}

# Server-side encryption (seguridad adicional)
resource "aws_s3_bucket_server_side_encryption_configuration" "images_encryption" {
  bucket = aws_s3_bucket.images.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}