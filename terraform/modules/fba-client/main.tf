# ──────────────────────────────────────────────────────────────
# FBA Client Module — Resources
# ──────────────────────────────────────────────────────────────

# ── SSH Key ───────────────────────────────────────────────────

resource "digitalocean_ssh_key" "client" {
  name       = "${var.client_name}-admin"
  public_key = var.ssh_public_key
}

# ── Droplet ───────────────────────────────────────────────────

resource "digitalocean_droplet" "client" {
  name     = "fba-${var.client_name}"
  image    = "ubuntu-24-04-x64"
  size     = var.droplet_size
  region   = var.droplet_region
  ssh_keys = [digitalocean_ssh_key.client.fingerprint]
  tags     = ["fba", var.client_name]

  user_data = templatefile("${path.module}/cloud-init.yml.tpl", {
    client_name              = var.client_name
    assistant_name           = var.assistant_name
    timezone                 = var.timezone
    whatsapp_number          = var.whatsapp_number
    owner_whatsapp           = var.owner_whatsapp
    claude_oauth_token       = var.claude_oauth_token
    claude_refresh_token     = var.claude_refresh_token
    sp_api_refresh_token     = var.sp_api_refresh_token
    sp_api_lwa_app_id        = var.sp_api_lwa_app_id
    sp_api_lwa_client_secret = var.sp_api_lwa_client_secret
    amazon_seller_id         = var.amazon_seller_id
    amazon_marketplace_id    = var.amazon_marketplace_id
    dashboard_user           = var.dashboard_user
    dashboard_pass           = var.dashboard_pass
    ghcr_token               = var.ghcr_token
    ghcr_user                = var.ghcr_user
    firecrawl_api_key        = var.firecrawl_api_key
    exa_api_key              = var.exa_api_key
    ssh_public_key           = var.ssh_public_key
  })
}

# ── Reserved IP ───────────────────────────────────────────────

resource "digitalocean_reserved_ip" "client" {
  region = var.droplet_region
}

resource "digitalocean_reserved_ip_assignment" "client" {
  ip_address = digitalocean_reserved_ip.client.ip_address
  droplet_id = digitalocean_droplet.client.id
}

# ── Firewall ──────────────────────────────────────────────────

resource "digitalocean_firewall" "client" {
  name        = "fba-${var.client_name}"
  droplet_ids = [digitalocean_droplet.client.id]

  # SSH
  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Inngest dashboard / HTTP
  inbound_rule {
    protocol         = "tcp"
    port_range       = "8080"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # ICMP (ping)
  inbound_rule {
    protocol         = "icmp"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # All outbound
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

# ── Monitoring Alerts ─────────────────────────────────────────

resource "digitalocean_monitor_alert" "cpu" {
  alerts {
    email = [var.alert_email]
  }
  window      = "5m"
  type        = "v1/insights/droplet/cpu"
  compare     = "GreaterThan"
  value       = 90
  enabled     = true
  entities    = [digitalocean_droplet.client.id]
  description = "FBA ${var.client_name} CPU > 90% for 5 min"
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
  entities    = [digitalocean_droplet.client.id]
  description = "FBA ${var.client_name} disk > 85%"
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
  entities    = [digitalocean_droplet.client.id]
  description = "FBA ${var.client_name} memory > 90% for 5 min"
}
