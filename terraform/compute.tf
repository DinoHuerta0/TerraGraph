# Servidor de la aplicación: una EC2 con Ubuntu 24.04 que, al arrancar, instala
# k3s, actualiza DuckDNS, crea el Secret de Kubernetes y aplica los manifiestos
# (ver user_data.sh.tftpl). No hay que entrar a configurarla a mano.

# AMI oficial de Ubuntu 24.04 (Noble) publicada por Canonical. Se busca en cada
# plan en lugar de escribir el ID, porque los IDs cambian por región y con cada
# actualización de la imagen.
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

locals {
  # Manifiestos de Kubernetes del issue #26, como { "archivo.yaml" = contenido }.
  # Mientras la carpeta k8s/ no exista, fileset devuelve un conjunto vacío y el
  # user_data solo crea el namespace y el Secret.
  k8s_dir = "${path.module}/../k8s"
  manifests = {
    for name in fileset(local.k8s_dir, "*.yaml") :
    name => file("${local.k8s_dir}/${name}")
  }
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.app.id]
  key_name               = aws_key_pair.deploy.key_name

  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    duckdns_domain = var.duckdns_domain
    duckdns_token  = var.duckdns_token
    database_url   = var.database_url
    sentry_dsn     = var.sentry_dsn
    manifests      = local.manifests
  })

  # El user_data solo corre en el primer arranque. Si cambia (por ejemplo, un
  # manifiesto nuevo), la instancia se reemplaza para que se vuelva a ejecutar.
  user_data_replace_on_change = true

  # IMDSv2 obligatorio: el servicio de metadatos exige un token, lo que protege
  # contra ataques que intentan leerlo a través de la aplicación.
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  # k3s, Traefik y la imagen de la app no caben con holgura en los 8 GB que trae
  # la AMI.
  root_block_device {
    volume_type = "gp3"
    volume_size = var.root_volume_size
    encrypted   = true
  }

  tags = {
    Name = "terragraph-app"
  }

  # Sin esto Terraform crearía la instancia en cuanto existan la subred y el
  # security group, posiblemente antes de la ruta a internet y de la regla de
  # salida. El user_data arrancaría sin salida y no podría descargar k3s.
  depends_on = [
    aws_route_table_association.public,
    aws_vpc_security_group_egress_rule.all,
  ]

  lifecycle {
    # Canonical publica AMIs nuevas seguido. Sin esto, un plan a mitad de la
    # sesión querría reemplazar la instancia solo porque salió una imagen nueva.
    ignore_changes = [ami]
  }
}
