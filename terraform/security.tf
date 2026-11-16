# Firewall de la instancia. Las reglas van como recursos aparte y no dentro del
# bloque del security group: es lo que recomienda el proveedor de AWS, cada
# regla se puede cambiar sin tocar las demás y en el grafo de TerraGraph se ve
# cada una como un nodo que depende del security group.
#
# Las descripciones van en inglés y sin acentos porque AWS no acepta esos
# caracteres en ellas.

resource "aws_security_group" "app" {
  name        = "terragraph-app"
  description = "HTTP for the application and SSH for the deployment"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "terragraph-app"
  }
}

# Puerto 80: el Ingress de Traefik (k3s) que atiende a los usuarios.
resource "aws_vpc_security_group_ingress_rule" "http" {
  security_group_id = aws_security_group.app.id
  description       = "HTTP to Traefik"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

# Puerto 22: el despliegue por SSH desde GitHub Actions. Queda abierto a todo
# internet porque los runners no tienen IP fija; lo protege la llave, no el
# firewall.
resource "aws_vpc_security_group_ingress_rule" "ssh" {
  security_group_id = aws_security_group.app.id
  description       = "SSH for the deployment pipeline"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 22
  to_port           = 22
}

# Salida libre. AWS crea esta regla sola en cada security group, pero Terraform
# la borra al crearlo, así que hay que declararla. Sin ella la instancia no
# podría descargar k3s ni la imagen, ni conectarse a Neon o a DuckDNS.
resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.app.id
  description       = "All outbound traffic"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}
