# El estado se guarda en el bucket que crea bootstrap/create-state-bucket.sh.
#
# El nombre del bucket no va aquí: lleva el ID de la cuenta de AWS y cambia si
# se usa otra cuenta. Se pasa al inicializar (configuración parcial):
#   terraform init -backend-config="bucket=terragraph-tfstate-<ACCOUNT_ID>"
# En GitHub Actions saldrá de la variable del repositorio TF_STATE_BUCKET.
terraform {
  backend "s3" {
    key          = "terragraph/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
