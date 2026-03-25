variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "droplet_name" {
  description = "Name of the droplet"
  type        = string
  default     = "globalink-fba"
}

variable "droplet_size" {
  description = "Droplet size slug"
  type        = string
  default     = "s-2vcpu-4gb"
}

variable "droplet_region" {
  description = "Droplet region"
  type        = string
  default     = "nyc1"
}

variable "deploy_ssh_public_key" {
  description = "SSH public key for GitHub Actions deploy"
  type        = string
}

variable "allowed_ssh_ips" {
  description = "IP addresses allowed to SSH (CIDR notation)"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "alert_email" {
  description = "Email for monitoring alerts"
  type        = string
}

# variable "spaces_region" {
#   description = "Region for DO Spaces bucket"
#   type        = string
#   default     = "nyc3"
# }

# ── Multi-tenant client provisioning ────────────────────────

variable "provision_new_client" {
  description = "Set to true to provision a new FBA client droplet"
  type        = bool
  default     = false
}

variable "client_name" {
  description = "Unique client slug (lowercase alphanumeric + hyphens)"
  type        = string
  default     = ""
}

variable "whatsapp_number" {
  description = "Bot WhatsApp number (no + prefix)"
  type        = string
  default     = ""
}

variable "owner_whatsapp" {
  description = "Owner WhatsApp number (no + prefix)"
  type        = string
  default     = ""
}

variable "assistant_name" {
  description = "NanoClaw assistant name (trigger word)"
  type        = string
  default     = "FBA"
}

variable "timezone" {
  description = "IANA timezone for the client"
  type        = string
  default     = "America/Bogota"
}

variable "claude_oauth_token" {
  description = "Claude OAuth token for NanoClaw"
  type        = string
  sensitive   = true
  default     = ""
}

variable "claude_refresh_token" {
  description = "Claude refresh token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "sp_api_refresh_token" {
  description = "SP-API refresh token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "sp_api_lwa_app_id" {
  description = "SP-API LWA App ID (client ID)"
  type        = string
  default     = ""
}

variable "sp_api_lwa_client_secret" {
  description = "SP-API LWA client secret"
  type        = string
  sensitive   = true
  default     = ""
}

variable "amazon_seller_id" {
  description = "Amazon Seller Central seller ID"
  type        = string
  default     = ""
}

variable "amazon_marketplace_id" {
  description = "Amazon marketplace ID"
  type        = string
  default     = "ATVPDKIKX0DER"
}

variable "dashboard_user" {
  description = "Inngest dashboard HTTP basic-auth username"
  type        = string
  default     = "admin"
}

variable "dashboard_pass" {
  description = "Inngest dashboard HTTP basic-auth password"
  type        = string
  sensitive   = true
  default     = ""
}

variable "ghcr_token" {
  description = "GitHub Container Registry PAT"
  type        = string
  sensitive   = true
  default     = ""
}

variable "ghcr_user" {
  description = "GitHub Container Registry username"
  type        = string
  default     = "alastrat"
}

variable "firecrawl_api_key" {
  description = "Firecrawl API key (optional)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "exa_api_key" {
  description = "Exa search API key (optional)"
  type        = string
  sensitive   = true
  default     = ""
}
