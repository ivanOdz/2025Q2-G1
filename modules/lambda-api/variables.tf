variable "name_prefix" {
  description = "Prefijo para nombrar la función"
  type        = string
}

variable "function_key" {
  description = "Clave corta de la función (se concatena al prefijo)."
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
  
  validation {
    condition     = length(var.source_code_hash_b64) > 0
    error_message = "source_code_hash_b64 is required for S3-based Lambda deployment."
  }
}

variable "memory_mb" {
  description = "Memoria (MB)."
  type        = number
  default     = 256
  
  validation {
    condition     = var.memory_mb >= 128 && var.memory_mb <= 10240
    error_message = "Memory size must be between 128 MB and 10240 MB."
  }
}

variable "timeout_s" {
  description = "Timeout (segundos)."
  type        = number
  default     = 15
  
  validation {
    condition     = var.timeout_s >= 1 && var.timeout_s <= 900
    error_message = "Timeout must be between 1 and 900 seconds."
  }
}

variable "runtime" {
  description = "Runtime de la Lambda (p.ej. python3.12)."
  type        = string
  
  validation {
    condition     = contains(["python3.8", "python3.9", "python3.10", "python3.11", "python3.12", "nodejs18.x", "nodejs20.x", "java11", "java17", "java21"], var.runtime)
    error_message = "Runtime must be a supported AWS Lambda runtime."
  }
}