# ──────────────────────────────────────────────────────────────
# FBA Client Module — Input Variables
# ──────────────────────────────────────────────────────────────

# ── Identity ──────────────────────────────────────────────────

variable "client_name" {
  description = "Unique client slug (lowercase alphanumeric + hyphens)"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,30}[a-z0-9]$", var.client_name))
    error_message = "client_name must be 3-32 chars, lowercase alphanumeric + hyphens, start with letter, end with letter/digit."
  }
}

# ── DigitalOcean ──────────────────────────────────────────────

variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
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

variable "ssh_public_key" {
  description = "SSH public key for admin access"
  type        = string
}

variable "alert_email" {
  description = "Email address for monitoring alerts"
  type        = string
}

# ── WhatsApp / NanoClaw ───────────────────────────────────────

variable "whatsapp_number" {
  description = "Bot WhatsApp number (no + prefix)"
  type        = string
}

variable "owner_whatsapp" {
  description = "Owner WhatsApp number (no + prefix)"
  type        = string
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

# ── Claude / LLM ─────────────────────────────────────────────

variable "claude_oauth_token" {
  description = "Claude OAuth token for NanoClaw"
  type        = string
  sensitive   = true
}

variable "claude_refresh_token" {
  description = "Claude refresh token (optional)"
  type        = string
  sensitive   = true
  default     = ""
}

# ── Amazon SP-API ─────────────────────────────────────────────

variable "sp_api_refresh_token" {
  description = "SP-API refresh token"
  type        = string
  sensitive   = true
}

variable "sp_api_lwa_app_id" {
  description = "SP-API LWA App ID (client ID)"
  type        = string
}

variable "sp_api_lwa_client_secret" {
  description = "SP-API LWA client secret"
  type        = string
  sensitive   = true
}

variable "amazon_seller_id" {
  description = "Amazon Seller Central seller ID"
  type        = string
}

variable "amazon_marketplace_id" {
  description = "Amazon marketplace ID"
  type        = string
  default     = "ATVPDKIKX0DER"
}

# ── Inngest Dashboard ────────────────────────────────────────

variable "dashboard_user" {
  description = "Inngest dashboard HTTP basic-auth username"
  type        = string
  default     = "admin"
}

variable "dashboard_pass" {
  description = "Inngest dashboard HTTP basic-auth password"
  type        = string
  sensitive   = true
}

# ── Container Registry ────────────────────────────────────────

variable "ghcr_token" {
  description = "GitHub Container Registry PAT"
  type        = string
  sensitive   = true
}

variable "ghcr_user" {
  description = "GitHub Container Registry username"
  type        = string
  default     = "alastrat"
}

# ── Optional Enrichment APIs ─────────────────────────────────

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
