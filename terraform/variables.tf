variable "aws_region" {
  description = "Región de AWS donde se crea la infraestructura."
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "Rango de IPs de la VPC del proyecto."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "Rango de IPs de la subred pública, dentro de vpc_cidr."
  type        = string
  default     = "10.0.1.0/24"
}

# Se fija la zona para que la subred no caiga en una donde no exista el tipo de
# instancia del issue #25 (t3.small no está en todas las zonas de us-east-1).
variable "availability_zone" {
  description = "Zona de disponibilidad de la subred pública."
  type        = string
  default     = "us-east-1a"
}

variable "instance_type" {
  description = "Tipo de la instancia EC2 que corre k3s y la aplicación."
  type        = string
  default     = "t3.small"
}

variable "root_volume_size" {
  description = "Tamaño en GB del disco de la instancia."
  type        = number
  default     = 20
}

variable "duckdns_domain" {
  description = "Subdominio de DuckDNS, sin .duckdns.org (por ejemplo, terragraph-demo)."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.duckdns_domain))
    error_message = "Escribe solo el subdominio, sin .duckdns.org: minúsculas, números y guiones."
  }
}

variable "dockerhub_username" {
  description = "Usuario de Docker Hub; la imagen es <usuario>/terragraph."
  type        = string
}

# Las variables sensitive no se muestran en el plan ni en los logs. En GitHub
# Actions llegan como TF_VAR_<nombre> desde los secretos del repositorio.
variable "duckdns_token" {
  description = "Token de DuckDNS para actualizar la IP del dominio."
  type        = string
  sensitive   = true
}

variable "database_url" {
  description = "URL de conexión a Neon. Termina en el Secret de Kubernetes."
  type        = string
  sensitive   = true
}

variable "sentry_dsn" {
  description = "DSN de Sentry. Vacío desactiva el monitoreo."
  type        = string
  sensitive   = true
  default     = ""
}
