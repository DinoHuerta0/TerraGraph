# Red del proyecto: una VPC con una sola subred pública, que es donde vivirá la
# instancia EC2 (issue #25). Todo esto se crea y se destruye en cada sesión del
# laboratorio; ninguno de estos recursos cobra por existir.

resource "aws_vpc" "main" {
  cidr_block = var.vpc_cidr

  # Necesarios para que la instancia reciba un nombre DNS público y pueda
  # resolver nombres (Docker Hub, Neon, DuckDNS).
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "terragraph-vpc"
  }
}

resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.public_subnet_cidr
  availability_zone = var.availability_zone

  # Cada instancia que se cree aquí recibe una IP pública automáticamente.
  map_public_ip_on_launch = true

  tags = {
    Name = "terragraph-public"
  }
}

# Puerta de la VPC hacia internet, en los dos sentidos.
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "terragraph-igw"
  }
}

# Lo que hace "pública" a la subred: todo el tráfico que no es de la VPC
# (0.0.0.0/0) sale por el internet gateway. El tráfico interno (10.0.0.0/16)
# lo resuelve la ruta local que AWS agrega sola.
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "terragraph-public"
  }
}

# Sin esta asociación la subred usaría la tabla principal de la VPC, que solo
# tiene la ruta local, y la instancia no tendría salida a internet.
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}
