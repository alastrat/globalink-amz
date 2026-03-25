#!/bin/bash
set -euo pipefail

# ── FBA Client Provisioning Script ─────────────────────────────────────
# Provisions a new multi-tenant FBA assistant client via Terraform.
#
# Usage:
#   ./scripts/provision-client.sh                              # Interactive mode
#   ./scripts/provision-client.sh --tfvars clients/acme.tfvars # From existing file
# ───────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TERRAFORM_DIR="$(cd "$SCRIPT_DIR/../terraform" && pwd)"
CLIENTS_DIR="$TERRAFORM_DIR/clients"

# ── Helpers ────────────────────────────────────────────────────────────

die()  { echo "❌ $*" >&2; exit 1; }
info() { echo "ℹ️  $*"; }
ok()   { echo "✅ $*"; }
warn() { echo "⚠️  $*"; }

validate_client_name() {
  local name="$1"
  if [[ ! "$name" =~ ^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$ ]] && [[ ! "$name" =~ ^[a-z0-9]{3}$ ]]; then
    # More precise: 3-32 chars, lowercase alphanumeric + hyphens, no leading/trailing hyphen
    if [[ ${#name} -lt 3 || ${#name} -gt 32 ]]; then
      die "Client name must be 3-32 characters long."
    fi
    if [[ ! "$name" =~ ^[a-z0-9-]+$ ]]; then
      die "Client name must contain only lowercase letters, digits, and hyphens."
    fi
    if [[ "$name" =~ ^- ]] || [[ "$name" =~ -$ ]]; then
      die "Client name must not start or end with a hyphen."
    fi
  fi
}

prompt_required() {
  local var_name="$1"
  local prompt_text="$2"
  local hint="${3:-}"
  local value=""

  while [[ -z "$value" ]]; do
    if [[ -n "$hint" ]]; then
      echo "  Hint: $hint"
    fi
    read -rp "  $prompt_text: " value
    if [[ -z "$value" ]]; then
      echo "  (required — cannot be empty)"
    fi
  done
  eval "$var_name=\"\$value\""
}

prompt_secret() {
  local var_name="$1"
  local prompt_text="$2"
  local hint="${3:-}"
  local value=""

  while [[ -z "$value" ]]; do
    if [[ -n "$hint" ]]; then
      echo "  Hint: $hint"
    fi
    read -rsp "  $prompt_text: " value
    echo
    if [[ -z "$value" ]]; then
      echo "  (required — cannot be empty)"
    fi
  done
  eval "$var_name=\"\$value\""
}

prompt_optional() {
  local var_name="$1"
  local prompt_text="$2"
  local default_val="${3:-}"
  local value=""

  if [[ -n "$default_val" ]]; then
    read -rp "  $prompt_text [$default_val]: " value
    value="${value:-$default_val}"
  else
    read -rp "  $prompt_text (Enter to skip): " value
  fi
  eval "$var_name=\"\$value\""
}

prompt_optional_secret() {
  local var_name="$1"
  local prompt_text="$2"
  local hint="${3:-}"
  local value=""

  if [[ -n "$hint" ]]; then
    echo "  Hint: $hint"
  fi
  read -rsp "  $prompt_text (Enter to skip): " value
  echo
  eval "$var_name=\"\$value\""
}

# ── Parse arguments ───────────────────────────────────────────────────

TFVARS_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tfvars)
      TFVARS_FILE="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage:"
      echo "  $0                              # Interactive mode"
      echo "  $0 --tfvars clients/acme.tfvars # From existing file"
      exit 0
      ;;
    *)
      die "Unknown argument: $1"
      ;;
  esac
done

# ── Mode: from existing tfvars ────────────────────────────────────────

if [[ -n "$TFVARS_FILE" ]]; then
  # Resolve relative to terraform dir
  if [[ ! "$TFVARS_FILE" = /* ]]; then
    TFVARS_FILE="$TERRAFORM_DIR/$TFVARS_FILE"
  fi
  [[ -f "$TFVARS_FILE" ]] || die "File not found: $TFVARS_FILE"

  # Extract client_name from the file
  CLIENT_NAME=$(grep -E '^client_name\s*=' "$TFVARS_FILE" | head -1 | sed 's/.*=\s*"\(.*\)"/\1/')
  [[ -n "$CLIENT_NAME" ]] || die "Could not extract client_name from $TFVARS_FILE"

  info "Provisioning client '$CLIENT_NAME' from $TFVARS_FILE"

  cd "$TERRAFORM_DIR"

  info "Selecting Terraform workspace '$CLIENT_NAME'..."
  terraform workspace select -or-create "$CLIENT_NAME"

  info "Running terraform apply..."
  if ! terraform apply -var-file="$TFVARS_FILE" -var="provision_new_client=true"; then
    die "Terraform apply failed. Check output above."
  fi

  RESERVED_IP=$(terraform output -raw client_reserved_ip 2>/dev/null || terraform output -raw reserved_ip 2>/dev/null || echo "")
  if [[ -z "$RESERVED_IP" ]]; then
    die "Could not retrieve reserved IP from Terraform output."
  fi

  info "Waiting for cloud-init to complete on $RESERVED_IP..."
  ELAPSED=0
  MAX_WAIT=300
  INTERVAL=15
  while [[ $ELAPSED -lt $MAX_WAIT ]]; do
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "root@$RESERVED_IP" "test -f /opt/provisioning-complete" 2>/dev/null; then
      ok "Cloud-init complete!"
      break
    fi
    echo "  Waiting... ($ELAPSED/${MAX_WAIT}s)"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
  done

  if [[ $ELAPSED -ge $MAX_WAIT ]]; then
    warn "Cloud-init still running after ${MAX_WAIT}s."
    warn "SSH in and check: ssh root@$RESERVED_IP cat /var/log/cloud-init-output.log"
  fi

  # WhatsApp setup
  info "Starting WhatsApp setup..."
  WHATSAPP_NUMBER=$(grep -E '^whatsapp_number\s*=' "$TFVARS_FILE" | head -1 | sed 's/.*=\s*"\(.*\)"/\1/' || echo "unknown")
  if ! "$SCRIPT_DIR/setup-whatsapp.sh" "$RESERVED_IP"; then
    warn "WhatsApp setup was skipped or failed."
    warn "Run later: ./scripts/setup-whatsapp.sh $RESERVED_IP"
  fi

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  ok "Client '$CLIENT_NAME' provisioned successfully!"
  echo "  Dashboard: http://$RESERVED_IP:8080/dashboard"
  echo "  SSH:       ssh root@$RESERVED_IP"
  echo "  WhatsApp:  $WHATSAPP_NUMBER"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 0
fi

# ── Mode: Interactive ─────────────────────────────────────────────────

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   FBA Assistant — New Client Provisioning        ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# 1. Client name
echo "── Step 1: Client Identity ──"
prompt_required CLIENT_NAME "Client name (lowercase, 3-32 chars, alphanumeric + hyphens)"
validate_client_name "$CLIENT_NAME"
echo ""

# Check if tfvars already exists
GENERATED_TFVARS="$CLIENTS_DIR/${CLIENT_NAME}.tfvars"
if [[ -f "$GENERATED_TFVARS" ]]; then
  warn "File already exists: $GENERATED_TFVARS"
  read -rp "  Overwrite? [y/N]: " OVERWRITE
  if [[ ! "$OVERWRITE" =~ ^[yY]$ ]]; then
    die "Aborted. Use --tfvars to apply the existing file."
  fi
fi

# 2. Required values
echo "── Step 2: Required Configuration ──"
echo ""

echo "[WhatsApp]"
prompt_required WHATSAPP_NUMBER "Bot WhatsApp number (no + prefix, e.g. 573011982530)"
prompt_required OWNER_WHATSAPP  "Owner WhatsApp number (no + prefix)"
echo ""

echo "[Notifications]"
prompt_required ALERT_EMAIL "Alert email address"
echo ""

echo "[Amazon SP-API]"
prompt_required AMAZON_SELLER_ID       "Amazon Seller ID"
prompt_secret   SP_API_REFRESH_TOKEN   "SP-API refresh token"
prompt_required SP_API_LWA_APP_ID      "SP-API LWA App ID (client ID)"
prompt_secret   SP_API_LWA_CLIENT_SECRET "SP-API LWA client secret"
echo ""

echo "[Claude]"
prompt_secret CLAUDE_OAUTH_TOKEN   "Claude OAuth token" \
  "On Mac: security find-generic-password -s \"Claude Code-credentials\" -w"
prompt_secret CLAUDE_REFRESH_TOKEN "Claude refresh token"
echo ""

echo "[Dashboard]"
prompt_secret DASHBOARD_PASS "Dashboard password (for HTTP basic-auth, user=admin)"
echo ""

echo "[GitHub Container Registry]"
prompt_secret GHCR_TOKEN "GHCR token" "Run: gh auth token"
echo ""

# 3. Optional values
echo "── Step 3: Optional Configuration ──"
echo ""
prompt_optional_secret FIRECRAWL_API_KEY "Firecrawl API key"
prompt_optional_secret EXA_API_KEY       "Exa API key"
prompt_optional        REGION            "DigitalOcean region" "nyc1"
prompt_optional        SIZE              "Droplet size" "s-2vcpu-4gb"
prompt_optional        TIMEZONE          "Timezone (IANA)" "America/Bogota"
echo ""

# 4. Generate tfvars file
info "Generating $GENERATED_TFVARS ..."
mkdir -p "$CLIENTS_DIR"

cat > "$GENERATED_TFVARS" <<TFVARS
# Auto-generated by provision-client.sh — $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Client: $CLIENT_NAME

client_name    = "$CLIENT_NAME"
droplet_region = "$REGION"
droplet_size   = "$SIZE"
alert_email    = "$ALERT_EMAIL"

# WhatsApp
whatsapp_number = "$WHATSAPP_NUMBER"
owner_whatsapp  = "$OWNER_WHATSAPP"

# Amazon
amazon_seller_id         = "$AMAZON_SELLER_ID"
sp_api_refresh_token     = "$SP_API_REFRESH_TOKEN"
sp_api_lwa_app_id        = "$SP_API_LWA_APP_ID"
sp_api_lwa_client_secret = "$SP_API_LWA_CLIENT_SECRET"

# Claude
claude_oauth_token   = "$CLAUDE_OAUTH_TOKEN"
claude_refresh_token = "$CLAUDE_REFRESH_TOKEN"

# Dashboard
dashboard_pass = "$DASHBOARD_PASS"

# GHCR
ghcr_token = "$GHCR_TOKEN"

# Timezone
timezone = "$TIMEZONE"
TFVARS

# Append optional keys only if provided
if [[ -n "${FIRECRAWL_API_KEY:-}" ]]; then
  echo "" >> "$GENERATED_TFVARS"
  echo "# Firecrawl" >> "$GENERATED_TFVARS"
  echo "firecrawl_api_key = \"$FIRECRAWL_API_KEY\"" >> "$GENERATED_TFVARS"
fi

if [[ -n "${EXA_API_KEY:-}" ]]; then
  echo "" >> "$GENERATED_TFVARS"
  echo "# Exa" >> "$GENERATED_TFVARS"
  echo "exa_api_key = \"$EXA_API_KEY\"" >> "$GENERATED_TFVARS"
fi

ok "Generated: $GENERATED_TFVARS"
echo ""

# 5. Terraform workspace
info "Selecting Terraform workspace '$CLIENT_NAME'..."
cd "$TERRAFORM_DIR"
terraform workspace select -or-create "$CLIENT_NAME"
echo ""

# 6. Terraform apply
info "Running terraform apply..."
echo ""
if ! terraform apply -var-file="$GENERATED_TFVARS" -var="provision_new_client=true"; then
  die "Terraform apply failed. Fix the issue and re-run:"
  echo "  cd terraform && terraform apply -var-file=clients/${CLIENT_NAME}.tfvars -var=\"provision_new_client=true\""
fi

echo ""

# Get the reserved IP
RESERVED_IP=$(terraform output -raw client_reserved_ip 2>/dev/null || terraform output -raw reserved_ip 2>/dev/null || echo "")
if [[ -z "$RESERVED_IP" ]]; then
  die "Could not retrieve reserved IP from Terraform output."
fi

# 7. Wait for cloud-init
info "Waiting for cloud-init to complete on $RESERVED_IP..."
ELAPSED=0
MAX_WAIT=300
INTERVAL=15
CLOUD_INIT_DONE=false

while [[ $ELAPSED -lt $MAX_WAIT ]]; do
  if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes "root@$RESERVED_IP" "test -f /opt/provisioning-complete" 2>/dev/null; then
    ok "Cloud-init complete!"
    CLOUD_INIT_DONE=true
    break
  fi
  echo "  Waiting... ($ELAPSED/${MAX_WAIT}s)"
  sleep $INTERVAL
  ELAPSED=$((ELAPSED + INTERVAL))
done

if [[ "$CLOUD_INIT_DONE" != "true" ]]; then
  warn "Cloud-init still running after ${MAX_WAIT}s."
  warn "SSH in and check: ssh root@$RESERVED_IP"
  warn "Log: /var/log/cloud-init-output.log"
  echo ""
fi

# 8. WhatsApp setup
info "Starting WhatsApp setup..."
echo "  (Press Ctrl+C to skip — you can run it later)"
echo ""

WHATSAPP_OK=false
trap 'echo ""; warn "WhatsApp setup skipped."; warn "Run later: ./scripts/setup-whatsapp.sh '"$RESERVED_IP"'"' INT

if "$SCRIPT_DIR/setup-whatsapp.sh" "$RESERVED_IP"; then
  WHATSAPP_OK=true
fi

trap - INT

# 9. Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ok "Client '$CLIENT_NAME' provisioned successfully!"
echo "  Dashboard: http://$RESERVED_IP:8080/dashboard"
echo "  SSH:       ssh root@$RESERVED_IP"
echo "  WhatsApp:  $WHATSAPP_NUMBER"
if [[ "$WHATSAPP_OK" != "true" ]]; then
  echo ""
  warn "WhatsApp not yet connected. Run:"
  echo "  ./scripts/setup-whatsapp.sh $RESERVED_IP"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
