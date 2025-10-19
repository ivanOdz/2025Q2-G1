output "bucket_name" {
  value       = aws_s3_bucket.frontend.id
}

output "website_url" {
  description = "URL del sitio web estático (HTTP)."
  value       = aws_s3_bucket_website_configuration.website.website_endpoint
}