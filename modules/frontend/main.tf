resource "aws_s3_bucket" "frontend" {
  bucket = "${var.project_name}-frontend-bucket"
  tags   = var.tags
}

# allow public access to this bucket
resource "aws_s3_bucket_public_access_block" "public_access" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# S3 used to host a static website
resource "aws_s3_bucket_website_configuration" "website" {
  # depends_on to ensure public access block is applied before web config
  depends_on = [aws_s3_bucket_public_access_block.public_access]

  bucket = aws_s3_bucket.frontend.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

# allow public read access to all objects in the bucket
data "aws_iam_policy_document" "public_read_policy" {
  statement {
    principals {
      type        = "AWS"
      identifiers = ["*"] # anyone
    }
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.frontend.arn}/*"]
  }
}

resource "aws_s3_bucket_policy" "public_policy" {
  bucket = aws_s3_bucket.frontend.id
  policy = data.aws_iam_policy_document.public_read_policy.json
}