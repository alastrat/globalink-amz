# ──────────────────────────────────────────────────────────────
# Example client tfvars — copy and fill in for each new client
# ──────────────────────────────────────────────────────────────
# Usage:
#   terraform plan  -var-file="clients/acme-fba.tfvars"
#   terraform apply -var-file="clients/acme-fba.tfvars"
# ──────────────────────────────────────────────────────────────

# ── REQUIRED: set to true to provision ──────────────────────
provision_new_client = true

# ── REQUIRED: client identity ───────────────────────────────
client_name    = "acme-fba"         # Unique slug: lowercase, hyphens, 3-32 chars
whatsapp_number = "15551234567"     # Bot WhatsApp number (no + prefix)
owner_whatsapp  = "15559876543"     # Owner WhatsApp number (no + prefix)

# ── OPTIONAL: defaults shown ────────────────────────────────
# assistant_name = "FBA"            # NanoClaw trigger word
# timezone       = "America/Bogota" # IANA timezone
# droplet_region = "nyc1"           # DigitalOcean region
# droplet_size   = "s-2vcpu-4gb"    # DigitalOcean droplet size

# ── REQUIRED: Claude credentials ────────────────────────────
claude_oauth_token   = ""           # Claude OAuth token for NanoClaw
# claude_refresh_token = ""         # Optional: Claude refresh token

# ── REQUIRED: Amazon SP-API ─────────────────────────────────
sp_api_refresh_token     = ""       # SP-API refresh token
sp_api_lwa_app_id        = ""       # SP-API LWA App ID (client ID)
sp_api_lwa_client_secret = ""       # SP-API LWA client secret
amazon_seller_id         = ""       # Amazon Seller Central seller ID
# amazon_marketplace_id  = "ATVPDKIKX0DER"  # Optional: defaults to US marketplace

# ── REQUIRED: Inngest dashboard ─────────────────────────────
dashboard_pass = ""                 # HTTP basic-auth password
# dashboard_user = "admin"          # Optional: defaults to "admin"

# ── REQUIRED: Container registry ────────────────────────────
ghcr_token = ""                     # GitHub Container Registry PAT
# ghcr_user = "alastrat"            # Optional: defaults to "alastrat"

# ── OPTIONAL: enrichment APIs ───────────────────────────────
# firecrawl_api_key = ""            # Firecrawl API key
# exa_api_key       = ""            # Exa search API key
