terraform {
  # 1.11 es la primera versión con el bloqueo nativo de S3 (use_lockfile)
  # estable, que evita crear una tabla de DynamoDB solo para los locks.
  required_version = ">= 1.11"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
