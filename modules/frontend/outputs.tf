output "bucket_name" {
  value       = module.frontend_bucket.s3_bucket_id
}

output "website_url" {
  description = "URL del sitio web estático (HTTP)."
  value       = module.frontend_bucket.s3_bucket_website_endpoint
}