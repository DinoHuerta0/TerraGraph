output "public_ip" {
  description = "IP pública de la instancia. Cambia cada vez que se crea."
  value       = aws_instance.app.public_ip
}

output "domain" {
  description = "Dominio de DuckDNS que apunta a la instancia."
  value       = "${var.duckdns_domain}.duckdns.org"
}

output "app_url" {
  description = "URL de la aplicación."
  value       = "http://${var.duckdns_domain}.duckdns.org"
}

output "ssh_command" {
  description = "Comando para entrar a la instancia con la llave del proyecto."
  value       = "ssh -i ~/.ssh/terragraph ubuntu@${aws_instance.app.public_ip}"
}
