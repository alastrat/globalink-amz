# ──────────────────────────────────────────────────────────────
# FBA Client Module — Outputs
# ──────────────────────────────────────────────────────────────

output "droplet_ip" {
  description = "Droplet public IPv4 address"
  value       = digitalocean_droplet.client.ipv4_address
}

output "reserved_ip" {
  description = "Reserved (static) IP address"
  value       = digitalocean_reserved_ip.client.ip_address
}

output "droplet_id" {
  description = "DigitalOcean droplet ID"
  value       = digitalocean_droplet.client.id
}

output "dashboard_url" {
  description = "Inngest dashboard URL"
  value       = "http://${digitalocean_reserved_ip.client.ip_address}:8080/dashboard"
}

output "ssh_command" {
  description = "SSH command to connect to the droplet"
  value       = "ssh root@${digitalocean_reserved_ip.client.ip_address}"
}
