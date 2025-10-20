variable "name_prefix" {
  description = "Prefijo para nombrar la función"
  type        = string
}

variable "function_key" {
  description = "Clave corta de la función (se concatena al prefijo)."
  type        = string
}

variable "runtime" {
  description = "Runtime de la Lambda (p.ej. python3.12)."
  type        = string
}

variable "handler" {
  description = "Handler (p.ej. handler.main)."
  type        = string
}

variable "role_arn" {
  description = "ARN del rol IAM de ejecución."
  type        = string
}

variable "memory_mb" {
  description = "Memoria (MB)."
  type        = number
  default     = 256
}

variable "timeout_s" {
  description = "Timeout (segundos)."
  type        = number
  default     = 15
}

variable "env" {
  description = "Variables de entorno."
  type        = map(string)
  default     = {}
}

variable "subnet_ids" {
  description = "Subnets (si corre en VPC). Vacío = sin VPC."
  type        = list(string)
  default     = []
}

variable "sg_ids" {
  description = "Security groups (si corre en VPC)."
  type        = list(string)
  default     = []
}

variable "layers" {
  description = "ARNs de layers."
  type        = list(string)
  default     = []
}

variable "architectures" {
  description = "Arquitecturas de la Lambda."
  type        = list(string)
  default     = ["arm64"]
}

variable "publish" {
  description = "Publicar nueva versión en cada cambio."
  type        = bool
  default     = true
}

variable "log_retention_in_days" {
  description = "Retención de logs (días)."
  type        = number
  default     = 14
}

# ---------- Código desde S3 ----------
variable "code_bucket" {
  description = "Bucket S3 con el artefacto ZIP."
  type        = string
}

variable "s3_key" {
  description = "Key del objeto en S3."
  type        = string
}

variable "s3_object_version" {
  description = "Versión del objeto (VersionId) en S3 (opcional)."
  type        = string
  default     = null
}

variable "source_code_hash_b64" {
  description = "Base64(SHA256 del ZIP) para forzar update."
  type        = string
}

# Validaciones simples
# validation {
#   condition     = length(var.code_bucket) > 0 && length(var.s3_key) > 0 && length(var.source_code_hash_b64) > 0
#   error_message = "code_bucket, s3_key y source_code_hash_b64 son requeridos."
# }