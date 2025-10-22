 # Valores propios del entorno dev

env          = "dev"
project_name = "fast-track-delivery"
aws_region   = "us-east-1"

# ¡El bucket debe ser globalmente único! OJO AL PIOJO CON ESTO pongo un //TODO
code_bucket  = "fast-track-delivery-dev-code-2025-ddjvi-guiso-de-lentejas"
images_bucket="fast-track-delivery-dev-images-2025-ddjvi-guiso-de-lentejas"
frontend_bucket="fast-track-delivery-dev-frontend-2025-ddjvi-guiso-de-lentejas"
lambda_zip_path = "../../lambdas/packaged"
# Agrega (digamos) data governance (opcional despues le damos mas sentido)
extra_tags = {
  owner = "team-dev"
}
