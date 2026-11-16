provider "aws" {
  region = var.aws_region

  # Etiquetas que se agregan a todos los recursos, para reconocerlos en la
  # consola del laboratorio.
  default_tags {
    tags = {
      Project   = "terragraph"
      ManagedBy = "terraform"
    }
  }
}
