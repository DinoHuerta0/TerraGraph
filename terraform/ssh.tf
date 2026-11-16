# Llave para entrar por SSH a la instancia. La usa el job de despliegue del
# issue #28 (secreto EC2_SSH_KEY) y sirve también para revisarla a mano.
#
# Solo la llave pública vive en el repositorio. La privada se queda en tu
# máquina (~/.ssh/terragraph) y en el secreto de GitHub. Como la pública no
# cambia, la misma llave privada sirve aunque la instancia se destruya y se
# vuelva a crear en cada sesión del laboratorio.
resource "aws_key_pair" "deploy" {
  key_name   = "terragraph-deploy"
  public_key = file("${path.module}/keys/terragraph.pub")
}
