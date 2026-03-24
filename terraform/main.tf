resource "digitalocean_ssh_key" "deploy" {
  name       = "github-actions-deploy"
  public_key = var.deploy_ssh_public_key
}

resource "digitalocean_droplet" "fba" {
  name     = var.droplet_name
  image    = "ubuntu-24-04-x64"
  size     = var.droplet_size
  region   = var.droplet_region
  ssh_keys = [digitalocean_ssh_key.deploy.fingerprint]
  tags     = ["fba", "production"]

  user_data = file("${path.module}/cloud-init.yml")

  # Imported droplet uses a custom marketplace image; these fields
  # can't be changed in-place so we ignore drift after import.
  lifecycle {
    ignore_changes = [image, user_data, ssh_keys]
  }
}

resource "digitalocean_reserved_ip" "fba" {
  region = var.droplet_region
}

resource "digitalocean_reserved_ip_assignment" "fba" {
  ip_address = digitalocean_reserved_ip.fba.ip_address
  droplet_id = digitalocean_droplet.fba.id
}

resource "digitalocean_firewall" "fba" {
  name        = "fba-firewall"
  droplet_ids = [digitalocean_droplet.fba.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = var.allowed_ssh_ips
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "8080"
    source_addresses = ["0.0.0.0/0"]
  }

  inbound_rule {
    protocol         = "icmp"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

# Spaces bucket for backups (requires Spaces API credentials, add later)
# resource "digitalocean_spaces_bucket" "backups" {
#   name   = "globalink-fba-backups"
#   region = var.spaces_region
#   acl    = "private"
#
#   lifecycle_rule {
#     enabled = true
#     expiration {
#       days = 30
#     }
#   }
# }

resource "digitalocean_monitor_alert" "cpu" {
  alerts {
    email = [var.alert_email]
  }
  window      = "5m"
  type        = "v1/insights/droplet/cpu"
  compare     = "GreaterThan"
  value       = 90
  enabled     = true
  entities    = [digitalocean_droplet.fba.id]
  description = "FBA droplet CPU > 90% for 5 min"
}

resource "digitalocean_monitor_alert" "disk" {
  alerts {
    email = [var.alert_email]
  }
  window      = "5m"
  type        = "v1/insights/droplet/disk_utilization_percent"
  compare     = "GreaterThan"
  value       = 85
  enabled     = true
  entities    = [digitalocean_droplet.fba.id]
  description = "FBA droplet disk > 85%"
}

resource "digitalocean_monitor_alert" "memory" {
  alerts {
    email = [var.alert_email]
  }
  window      = "5m"
  type        = "v1/insights/droplet/memory_utilization_percent"
  compare     = "GreaterThan"
  value       = 90
  enabled     = true
  entities    = [digitalocean_droplet.fba.id]
  description = "FBA droplet memory > 90% for 5 min"
}
