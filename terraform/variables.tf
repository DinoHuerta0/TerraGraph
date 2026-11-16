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
