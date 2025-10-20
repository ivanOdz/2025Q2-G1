 # Valores propios del entorno dev

env          = "dev"
project_name = "fast-track-delivery"
aws_region   = "us-east-1"

# ¡El bucket debe ser globalmente único! OJO AL PIOJO CON ESTO pongo un //TODO
code_bucket  = "fast-track-delivery-dev-artifacts"

# Agrega (digamos) data governance (opcional despues le damos mas sentido)
extra_tags = {
  owner = "team-dev"
}
