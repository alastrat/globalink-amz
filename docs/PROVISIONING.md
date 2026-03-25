# Multi-Tenant Client Provisioning

Provision a new Amazon FBA Agent droplet for a client in ~3 minutes.

## Architecture Overview

Each client gets an independent DigitalOcean droplet running:
- **NanoClaw** -- WhatsApp bot powered by Claude (Baileys v7)
- **Inngest** -- task orchestration (product research, restriction checks, nightly audits)
- **Research Dashboard** -- web UI on port 8080

Docker images are shared from GHCR (`ghcr.io/alastrat/globalink-amz`). Credentials, WhatsApp sessions, and Terraform state are fully isolated per client via Terraform workspaces.

## Prerequisites

- **DigitalOcean** account + API token (`DO_TOKEN` env var or in `.tfvars`)
- **GitHub** account with GHCR access (run `gh auth token` to get a PAT)
- **Claude Team** subscription (OAuth token from browser devtools)
- **Amazon SP-API** developer app: refresh token, LWA app ID, LWA client secret
- **Amazon Seller Central** account (seller ID)
- **WhatsApp** number for the bot (will be linked via QR scan)
- **SSH key pair** (public key is uploaded to DigitalOcean, private key used for access)

## Quick Start

```bash
./scripts/provision-client.sh --name <client-name>
```

The interactive script prompts for all required values, writes a `.tfvars` file, runs Terraform, waits for cloud-init to complete, and opens WhatsApp QR setup. When it finishes you get the droplet IP, dashboard URL, and SSH access details.

## Manual Provisioning

If you prefer to run each step yourself:

### 1. Create tfvars file

```bash
cp terraform/clients/example.tfvars terraform/clients/<name>.tfvars
```

Fill in all values (tokens, WhatsApp numbers, seller ID, etc.).

### 2. Create Terraform workspace

```bash
cd terraform
terraform workspace new <name>
```

### 3. Apply

```bash
terraform apply \
  -var-file=clients/<name>.tfvars \
  -var="provision_new_client=true"
```

### 4. Wait for cloud-init

Takes ~3 minutes. The droplet pulls Docker images from GHCR and starts all services.

### 5. Link WhatsApp

```bash
ssh root@<ip> "cd /opt/nanoclaw && node setup-wa.js"
```

Scan the QR code with WhatsApp on the bot phone.

### 6. Verify

Open the dashboard at `http://<reserved-ip>:8080/dashboard` and confirm services are running.

## Managing Clients

- **List clients:** `terraform workspace list`
- **Switch to client:** `terraform workspace select <name>`
- **Update client:** Edit the tfvars file, then `terraform apply -var-file=clients/<name>.tfvars -var="provision_new_client=true"`
- **Destroy client:** `terraform workspace select <name> && terraform destroy -var-file=clients/<name>.tfvars -var="provision_new_client=true"`
- **View logs:** `ssh root@<ip> docker logs globalink-fba-nanoclaw`

## Troubleshooting

- **Cloud-init not complete:** SSH in and check `cat /var/log/cloud-init-output.log`
- **WhatsApp won't connect:** Run `ssh -t root@<ip> "cd /opt/nanoclaw && node setup-wa.js"` again to re-scan the QR code
- **Token expired:** Check `/var/log/token-refresh.log`, verify `/root/.claude/.credentials.json` has a valid refresh token
- **Dashboard not loading:** Check `docker ps` to confirm containers are up, verify port 8080 is open in the firewall
- **Services not starting:** Check `docker logs globalink-fba-nanoclaw` and `docker logs globalink-fba-inngest-worker-1` for errors
