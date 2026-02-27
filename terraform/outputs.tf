output "droplet_ip" {
  description = "Droplet public IPv4"
  value       = digitalocean_droplet.fba.ipv4_address
}

output "reserved_ip" {
  description = "Reserved (floating) IP"
  value       = digitalocean_reserved_ip.fba.ip_address
}

output "droplet_id" {
  description = "Droplet ID"
  value       = digitalocean_droplet.fba.id
}

output "spaces_bucket" {
  description = "Spaces bucket name"
  value       = digitalocean_spaces_bucket.backups.name
}

output "spaces_endpoint" {
  description = "Spaces endpoint URL"
  value       = digitalocean_spaces_bucket.backups.bucket_domain_name
}
