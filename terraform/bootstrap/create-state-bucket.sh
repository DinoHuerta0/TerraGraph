#!/usr/bin/env bash
# Crea el bucket S3 donde Terraform guarda su estado. Se corre UNA sola vez, a
# mano, con las credenciales del laboratorio de AWS ya configuradas.
#
# El bucket queda fuera de Terraform a propósito: si Terraform lo administrara,
# su propio estado viviría dentro del recurso que está creando, y un
# `terraform destroy` lo borraría junto con la infraestructura.
#
# Es seguro correrlo otra vez: si el bucket ya existe, solo vuelve a aplicar la
# configuración (versionado y bloqueo de acceso público).
#
# Uso:  bash terraform/bootstrap/create-state-bucket.sh

set -euo pipefail

REGION="us-east-1"

# El nombre de un bucket es único en todo AWS, así que se le agrega el ID de la
# cuenta para no chocar con el de otra persona.
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="terragraph-tfstate-${ACCOUNT_ID}"

if aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo "El bucket ${BUCKET} ya existe; se actualiza su configuración."
else
  echo "Creando el bucket ${BUCKET} en ${REGION}..."
  # En us-east-1 no se manda LocationConstraint; en otras regiones sí.
  aws s3api create-bucket --bucket "$BUCKET" --region "$REGION"
fi

# Versionado: cada escritura del estado guarda una versión nueva, así que si un
# apply lo deja mal se puede recuperar la anterior.
aws s3api put-bucket-versioning \
  --bucket "$BUCKET" \
  --versioning-configuration Status=Enabled

# El estado puede contener datos sensibles (por ejemplo DATABASE_URL), así que
# se bloquea cualquier forma de hacerlo público.
aws s3api put-public-access-block \
  --bucket "$BUCKET" \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

echo
echo "Listo. Inicializa Terraform con:"
echo "  terraform -chdir=terraform init -backend-config=\"bucket=${BUCKET}\""
