# Phase 1: Repo Restructure + CI/CD + Terraform

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Get all production code into the repo, automated deploys via GitHub Actions + GHCR, and infrastructure managed by Terraform.

**Architecture:** Current JS files from VPS are pulled into the repo as-is (no TS rewrite yet). GitHub Actions builds Docker images on push to main (after lint/test passes), pushes to GHCR, then SSHes into VPS to pull and restart. Terraform manages the DigitalOcean droplet, firewall, reserved IP, Spaces bucket, and monitoring alerts.

**Tech Stack:** Node.js 22, Docker, GitHub Actions, GHCR, Terraform, DigitalOcean

**Design doc:** `docs/plans/2026-02-25-infra-cicd-typescript-design.md`

---

### Task 1: Clean Out Old Code

Remove the unused CrewAI/Python codebase that was replaced by NanoClaw + Inngest.

**Files:**
- Delete: `src/` (entire directory)
- Delete: `config/` (agents.yaml, filters.yaml, schedules.yaml)
- Delete: `gateway/`
- Delete: `whatsapp-bridge/`
- Delete: `tests/`
- Delete: `scripts/`
- Delete: `data/`
- Delete: `Dockerfile`
- Delete: `docker-compose.yml`
- Delete: `pyproject.toml`
- Delete: `requirements.txt`
- Delete: `.env.example`
- Delete: `.coderabbit.yaml`
- Keep: `docs/plans/` (design docs)
- Keep: `.gitignore` (will update)
- Keep: `.claude/` (project memory)

**Step 1: Remove old directories and files**

```bash
git rm -r src/ config/ gateway/ whatsapp-bridge/ tests/ scripts/ data/
git rm Dockerfile docker-compose.yml pyproject.toml requirements.txt .env.example .coderabbit.yaml
```

**Step 2: Commit**

```bash
git add -A
git commit -m "chore: remove unused CrewAI/Python codebase

Architecture migrated to NanoClaw + Inngest. Old code is no longer
deployed or referenced. Design docs preserved in docs/plans/."
```

---

### Task 2: Create Project Structure and Package.json

Set up the new directory structure and Node.js project.

**Files:**
- Create: `package.json`
- Create: `tsconfig.json`
- Modify: `.gitignore`

**Step 1: Create package.json**

```json
{
  "name": "globalink-amz",
  "version": "1.0.0",
  "private": true,
  "description": "Amazon FBA Agent — NanoClaw + Inngest stack",
  "scripts": {
    "lint": "eslint . --ext .ts,.js",
    "typecheck": "tsc --noEmit",
    "test": "node --test tests/**/*.test.ts",
    "build": "tsc",
    "build:nanoclaw": "docker build -f docker/nanoclaw.Dockerfile -t ghcr.io/alastrat/globalink-amz/nanoclaw:local .",
    "build:inngest-worker": "docker build -f docker/inngest-worker.Dockerfile -t ghcr.io/alastrat/globalink-amz/inngest-worker:local ."
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "typescript": "^5.7.0",
    "eslint": "^9.0.0",
    "@eslint/js": "^9.0.0",
    "typescript-eslint": "^8.0.0"
  }
}
```

**Step 2: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "declaration": true,
    "sourceMap": true,
    "resolveJsonModule": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "tests"]
}
```

**Step 3: Update .gitignore**

Replace contents with:

```
# Dependencies
node_modules/

# Build output
dist/

# Environment (secrets)
.env
.env.*
!.env.example

# Python
__pycache__/
*.pyc

# OS
.DS_Store

# Terraform
terraform/.terraform/
terraform/*.tfstate
terraform/*.tfstate.backup
terraform/.terraform.lock.hcl
terraform/terraform.tfvars

# Docker
*.tar

# IDE
.vscode/
.idea/

# NanoClaw runtime (not in repo)
store/
*.db

# Worktrees
.worktrees/
```

**Step 4: Install deps and verify**

```bash
npm install
npx tsc --noEmit  # Should succeed (no src files yet)
```

**Step 5: Commit**

```bash
git add package.json tsconfig.json .gitignore package-lock.json
git commit -m "chore: set up Node.js project with TypeScript and ESLint"
```

---

### Task 3: Pull NanoClaw Patches Into Repo

Copy the 4 patched JS files + 1 TS patch from the VPS into the repo.

**Files:**
- Create: `nanoclaw/patches/channels/whatsapp.js`
- Create: `nanoclaw/patches/ipc.js`
- Create: `nanoclaw/patches/container-runner.js`
- Create: `nanoclaw/patches/index.js`
- Create: `nanoclaw/patches/agent-runner-index.ts`

**Step 1: Create directory**

```bash
mkdir -p nanoclaw/patches/channels
```

**Step 2: SCP files from VPS**

```bash
scp root@167.172.134.211:/opt/nanoclaw/dist/channels/whatsapp.js nanoclaw/patches/channels/
scp root@167.172.134.211:/opt/nanoclaw/dist/ipc.js nanoclaw/patches/ipc.js
scp root@167.172.134.211:/opt/nanoclaw/dist/container-runner.js nanoclaw/patches/container-runner.js
scp root@167.172.134.211:/opt/nanoclaw/dist/index.js nanoclaw/patches/index.js
scp root@167.172.134.211:/opt/nanoclaw/patches/agent-runner-index.ts nanoclaw/patches/agent-runner-index.ts
```

**Step 3: Verify files exist**

```bash
find nanoclaw/patches -type f | sort
```

Expected:
```
nanoclaw/patches/agent-runner-index.ts
nanoclaw/patches/channels/whatsapp.js
nanoclaw/patches/container-runner.js
nanoclaw/patches/index.js
nanoclaw/patches/ipc.js
```

**Step 4: Commit**

```bash
git add nanoclaw/
git commit -m "feat: add NanoClaw patches from production VPS

These are compiled JS patches applied over upstream NanoClaw dist/:
- whatsapp.js: sendImage, sendQuotedReply, message key capture
- ipc.js: storeKeyAs, quoted_reply type, message key storage
- container-runner.js: detalles handler, Inngest auto-trigger
- index.js: sendQuotedReply wired into IPC deps
- agent-runner-index.ts: WebSearch/WebFetch removed from allowedTools"
```

---

### Task 4: Pull Inngest Worker Into Repo

Copy the full Inngest stack from VPS.

**Files:**
- Create: `inngest/docker-compose.yml`
- Create: `inngest/worker/Dockerfile`
- Create: `inngest/worker/package.json`
- Create: `inngest/worker/server.js`
- Create: `inngest/worker/functions/research.js`
- Create: `inngest/worker/lib/ipc.js`
- Create: `inngest/worker/lib/tools.js`
- Create: `inngest/.env.example`

**Step 1: Create directories**

```bash
mkdir -p inngest/worker/{functions,lib}
```

**Step 2: SCP files from VPS**

```bash
scp root@167.172.134.211:/opt/inngest/docker-compose.yml inngest/docker-compose.yml
scp root@167.172.134.211:/opt/inngest/worker/Dockerfile inngest/worker/Dockerfile
scp root@167.172.134.211:/opt/inngest/worker/package.json inngest/worker/package.json
scp root@167.172.134.211:/opt/inngest/worker/server.js inngest/worker/server.js
scp root@167.172.134.211:/opt/inngest/worker/functions/research.js inngest/worker/functions/research.js
scp root@167.172.134.211:/opt/inngest/worker/lib/ipc.js inngest/worker/lib/ipc.js
scp root@167.172.134.211:/opt/inngest/worker/lib/tools.js inngest/worker/lib/tools.js
```

**Step 3: Create .env.example**

```bash
cat > inngest/.env.example << 'EOF'
INNGEST_EVENT_KEY=local-fba-event-key
INNGEST_SIGNING_KEY=signkey-test-12345678
INNGEST_DEV=1
INNGEST_BASE_URL=http://inngest-server:8288
TOOLS_DIR=/tools
IPC_DIR=/ipc/messages
CACHE_DIR=/cache
CHAT_JID=573002061607@s.whatsapp.net
EOF
```

**Step 4: Verify**

```bash
find inngest -type f | sort
```

Expected:
```
inngest/.env.example
inngest/docker-compose.yml
inngest/worker/Dockerfile
inngest/worker/functions/research.js
inngest/worker/lib/ipc.js
inngest/worker/lib/tools.js
inngest/worker/package.json
inngest/worker/server.js
```

**Step 5: Commit**

```bash
git add inngest/
git commit -m "feat: add Inngest worker stack from production VPS

Inngest server + worker for background job processing:
- research.js: Product research pipeline (SP-API → analysis → cards)
- ipc.js: Compact product cards, analysis caching, storeKeyAs
- tools.js: Python tool child process executor"
```

---

### Task 5: Pull Python Tools and Config Into Repo

Copy the Python tools and business config.

**Files:**
- Create: `tools/sp-api-query.py`
- Create: `tools/cache.py`
- Create: `tools/bsr-estimator.py`
- Create: `tools/exa-search.py`
- Create: `tools/firecrawl-scrape.py`
- Create: `tools/.env.example`
- Create: `config/CLAUDE.md`

**Step 1: Create directories**

```bash
mkdir -p tools config
```

**Step 2: SCP files from VPS**

```bash
scp root@167.172.134.211:/opt/nanoclaw/groups/owner/tools/sp-api-query.py tools/
scp root@167.172.134.211:/opt/nanoclaw/groups/owner/tools/cache.py tools/
scp root@167.172.134.211:/opt/nanoclaw/groups/owner/tools/bsr-estimator.py tools/
scp root@167.172.134.211:/opt/nanoclaw/groups/owner/tools/exa-search.py tools/
scp root@167.172.134.211:/opt/nanoclaw/groups/owner/tools/firecrawl-scrape.py tools/
scp root@167.172.134.211:/opt/nanoclaw/groups/owner/CLAUDE.md config/CLAUDE.md
```

**Step 3: Create tools/.env.example**

```bash
cat > tools/.env.example << 'EOF'
SP_API_LWA_APP_ID=amzn1.application-oa2-client.xxxx
SP_API_LWA_CLIENT_SECRET=xxxx
SP_API_REFRESH_TOKEN=Atzr|xxxx
AMAZON_SELLER_ID=xxxx
AMAZON_MARKETPLACE_ID=ATVPDKIKX0DER
FIRECRAWL_API_KEY=fc-xxxx
EXA_API_KEY=xxxx
EOF
```

**Step 4: Create root .env.example**

```bash
cat > .env.example << 'EOF'
# NanoClaw
ANTHROPIC_API_KEY=sk-ant-xxxx
ASSISTANT_NAME=FBA
ASSISTANT_HAS_OWN_NUMBER=true
TZ=America/Bogota

# Inngest
INNGEST_EVENT_KEY=local-fba-event-key
INNGEST_SIGNING_KEY=signkey-test-12345678

# DigitalOcean (for Terraform)
DO_TOKEN=dop_v1_xxxx
EOF
```

**Step 5: Commit**

```bash
git add tools/ config/ .env.example
git commit -m "feat: add Python tools and business config from production VPS

Tools: SP-API query, cache, BSR estimator, Exa search, Firecrawl scrape
Config: CLAUDE.md business logic for the FBA agent"
```

---

### Task 6: Create Docker Compose (Full Stack)

Create the root docker-compose.yml that ties NanoClaw + Inngest together.

**Files:**
- Create: `docker/nanoclaw.Dockerfile`
- Create: `docker/inngest-worker.Dockerfile`
- Create: `docker-compose.yml`

**Step 1: Create docker directory**

```bash
mkdir -p docker
```

**Step 2: Create nanoclaw.Dockerfile**

NanoClaw needs: Node.js 22, git (to clone upstream), Docker CLI (to spawn agent containers).

```dockerfile
# docker/nanoclaw.Dockerfile
FROM node:22-slim AS base

RUN apt-get update && \
    apt-get install -y git ca-certificates curl --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Install Docker CLI (needed to spawn agent containers)
RUN install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc && \
    chmod a+r /etc/apt/keyrings/docker.asc && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y docker-ce-cli --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/nanoclaw

# Clone upstream NanoClaw and install dependencies
RUN git clone https://github.com/qwibitai/nanoclaw.git . && npm install --production

# Apply our patches over upstream dist/
COPY nanoclaw/patches/channels/whatsapp.js dist/channels/whatsapp.js
COPY nanoclaw/patches/ipc.js dist/ipc.js
COPY nanoclaw/patches/container-runner.js dist/container-runner.js
COPY nanoclaw/patches/index.js dist/index.js
COPY nanoclaw/patches/agent-runner-index.ts patches/agent-runner-index.ts

CMD ["node", "dist/index.js"]
```

**Step 3: Create inngest-worker.Dockerfile**

```dockerfile
# docker/inngest-worker.Dockerfile
FROM node:20-slim

RUN apt-get update && \
    apt-get install -y python3 python3-pip --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY inngest/worker/package.json inngest/worker/package-lock.json* ./
RUN npm install --production

COPY inngest/worker/ .

EXPOSE 3500
CMD ["node", "server.js"]
```

**Step 4: Create root docker-compose.yml**

```yaml
# docker-compose.yml
# Full stack: NanoClaw + Inngest (server + worker)
# Run: docker compose up -d

services:
  nanoclaw:
    image: ghcr.io/alastrat/globalink-amz/nanoclaw:${IMAGE_TAG:-latest}
    build:
      context: .
      dockerfile: docker/nanoclaw.Dockerfile
    restart: always
    env_file: .env.nanoclaw
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - nanoclaw-store:/opt/nanoclaw/store
      - nanoclaw-data:/opt/nanoclaw/data
      - ./config:/opt/nanoclaw/groups/owner:ro
      - ./tools:/opt/nanoclaw/groups/owner/tools:ro
    networks:
      - inngest
    depends_on:
      - inngest-server

  inngest-server:
    image: inngest/inngest:latest
    restart: always
    ports:
      - "127.0.0.1:8288:8288"
    environment:
      - INNGEST_EVENT_KEY=${INNGEST_EVENT_KEY:-local-fba-event-key}
      - INNGEST_SIGNING_KEY=${INNGEST_SIGNING_KEY:-signkey-test-12345678}
    volumes:
      - inngest-data:/var/lib/inngest
    command: inngest dev -u http://inngest-worker:3500/api/inngest --no-discovery
    networks:
      - inngest

  inngest-worker:
    image: ghcr.io/alastrat/globalink-amz/inngest-worker:${IMAGE_TAG:-latest}
    build:
      context: .
      dockerfile: docker/inngest-worker.Dockerfile
    restart: always
    environment:
      - INNGEST_DEV=1
      - INNGEST_BASE_URL=http://inngest-server:8288
      - INNGEST_EVENT_KEY=${INNGEST_EVENT_KEY:-local-fba-event-key}
      - INNGEST_SIGNING_KEY=${INNGEST_SIGNING_KEY:-signkey-test-12345678}
      - TOOLS_DIR=/tools
      - IPC_DIR=/ipc/messages
      - CACHE_DIR=/cache
      - CHAT_JID=${CHAT_JID:-573002061607@s.whatsapp.net}
    volumes:
      - ./tools:/tools:ro
      - nanoclaw-data:/opt/nanoclaw/data
      - nanoclaw-cache:/cache
    depends_on:
      - inngest-server
    networks:
      - inngest

volumes:
  nanoclaw-store:
  nanoclaw-data:
  nanoclaw-cache:
  inngest-data:

networks:
  inngest:
```

**Step 5: Verify Dockerfiles are valid syntax**

```bash
docker build --check -f docker/nanoclaw.Dockerfile .
docker build --check -f docker/inngest-worker.Dockerfile .
```

**Step 6: Commit**

```bash
git add docker/ docker-compose.yml
git commit -m "feat: add Dockerfiles and docker-compose for full stack

- nanoclaw.Dockerfile: upstream NanoClaw + patches + Docker CLI
- inngest-worker.Dockerfile: Node.js 20 + Python3
- docker-compose.yml: NanoClaw + Inngest server + worker with shared volumes"
```

---

### Task 7: Create Terraform Configuration

Set up Terraform for DigitalOcean: droplet, firewall, reserved IP, Spaces, monitoring.

**Files:**
- Create: `terraform/versions.tf`
- Create: `terraform/variables.tf`
- Create: `terraform/main.tf`
- Create: `terraform/outputs.tf`
- Create: `terraform/terraform.tfvars.example`
- Create: `terraform/cloud-init.yml`

**Step 1: Create terraform directory**

```bash
mkdir -p terraform
```

**Step 2: Create versions.tf**

```hcl
# terraform/versions.tf
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.40"
    }
  }
}

provider "digitalocean" {
  token = var.do_token
}
```

**Step 3: Create variables.tf**

```hcl
# terraform/variables.tf

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
  default     = ["0.0.0.0/0"]  # Restrict in tfvars
}

variable "alert_email" {
  description = "Email for monitoring alerts"
  type        = string
}

variable "spaces_region" {
  description = "Region for DO Spaces bucket"
  type        = string
  default     = "nyc3"
}
```

**Step 4: Create main.tf**

```hcl
# terraform/main.tf

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

  # SSH
  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = var.allowed_ssh_ips
  }

  # ICMP (ping)
  inbound_rule {
    protocol         = "icmp"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # All outbound TCP (WhatsApp, Docker Hub, APIs, GHCR)
  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  # All outbound UDP (DNS, WhatsApp)
  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  # ICMP outbound
  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

resource "digitalocean_spaces_bucket" "backups" {
  name   = "globalink-fba-backups"
  region = var.spaces_region
  acl    = "private"

  lifecycle_rule {
    enabled = true
    expiration {
      days = 30
    }
  }
}

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
```

**Step 5: Create outputs.tf**

```hcl
# terraform/outputs.tf

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
```

**Step 6: Create cloud-init.yml**

```yaml
# terraform/cloud-init.yml
#cloud-config

package_update: true
package_upgrade: true

packages:
  - docker.io
  - docker-compose-plugin
  - fail2ban
  - ufw

runcmd:
  # Enable Docker
  - systemctl enable docker
  - systemctl start docker

  # Login to GHCR (token injected by deploy step)
  - mkdir -p /opt/globalink-fba

  # Firewall (UFW as backup to DO firewall)
  - ufw default deny incoming
  - ufw default allow outgoing
  - ufw allow ssh
  - ufw --force enable

  # Docker log rotation
  - |
    cat > /etc/docker/daemon.json << 'DEOF'
    {
      "log-driver": "json-file",
      "log-opts": {
        "max-size": "10m",
        "max-file": "3"
      }
    }
    DEOF
  - systemctl restart docker
```

**Step 7: Create terraform.tfvars.example**

```hcl
# terraform/terraform.tfvars.example
# Copy to terraform.tfvars and fill in values

do_token              = "dop_v1_xxxx"
deploy_ssh_public_key = "ssh-ed25519 AAAA... github-actions"
allowed_ssh_ips       = ["your.ip.here/32"]
alert_email           = "you@example.com"
```

**Step 8: Verify Terraform syntax**

```bash
cd terraform && terraform fmt -check && terraform validate
```

Note: `terraform validate` requires `terraform init` first. If Terraform CLI is not installed locally, skip validation — it will be validated in CI.

**Step 9: Commit**

```bash
git add terraform/
git commit -m "feat: add Terraform config for DigitalOcean infrastructure

Manages: droplet, reserved IP, firewall, Spaces bucket (backups),
monitoring alerts (CPU, disk, memory). Cloud-init installs Docker
and hardens the server on first boot."
```

---

### Task 8: Create GitHub Actions CI Workflow

Lint, typecheck, and test on every push.

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `eslint.config.js`
- Create: `tests/smoke.test.ts`

**Step 1: Create CI workflow**

```bash
mkdir -p .github/workflows
```

```yaml
# .github/workflows/ci.yml
name: CI

on: push

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm

      - run: npm ci

      - name: Lint
        run: npm run lint

      - name: Typecheck
        run: npm run typecheck

      - name: Test
        run: npm test
```

**Step 2: Create eslint.config.js**

```javascript
// eslint.config.js
import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default [
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    ignores: ["dist/", "node_modules/", "nanoclaw/", "inngest/", "tools/"],
  },
];
```

**Step 3: Create minimal smoke test**

```bash
mkdir -p tests
```

```typescript
// tests/smoke.test.ts
import { describe, it } from "node:test";
import assert from "node:assert";

describe("smoke test", () => {
  it("should pass", () => {
    assert.strictEqual(1 + 1, 2);
  });
});
```

**Step 4: Verify locally**

```bash
npm run lint
npm run typecheck
npm test
```

All three should pass.

**Step 5: Commit**

```bash
git add .github/workflows/ci.yml eslint.config.js tests/
git commit -m "feat: add GitHub Actions CI workflow

Runs lint, typecheck, and tests on every push."
```

---

### Task 9: Create GitHub Actions Deploy Workflow

Build Docker images, push to GHCR, deploy to VPS on push to main.

**Files:**
- Create: `.github/workflows/deploy.yml`

**Step 1: Create deploy workflow**

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

# Ensure only one deploy runs at a time
concurrency:
  group: deploy-production
  cancel-in-progress: false

jobs:
  ci:
    uses: ./.github/workflows/ci.yml

  build-and-push:
    needs: ci
    runs-on: ubuntu-latest
    permissions:
      packages: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push NanoClaw
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/nanoclaw.Dockerfile
          push: true
          tags: |
            ghcr.io/alastrat/globalink-amz/nanoclaw:${{ github.sha }}
            ghcr.io/alastrat/globalink-amz/nanoclaw:latest

      - name: Build and push Inngest worker
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/inngest-worker.Dockerfile
          push: true
          tags: |
            ghcr.io/alastrat/globalink-amz/inngest-worker:${{ github.sha }}
            ghcr.io/alastrat/globalink-amz/inngest-worker:latest

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to VPS
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: root
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            set -e

            # Login to GHCR
            echo "${{ secrets.GHCR_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin

            # Pull latest images
            cd /opt/globalink-fba
            docker compose pull nanoclaw inngest-worker

            # Restart services with new images
            docker compose up -d --remove-orphans

            # Cleanup old images
            docker image prune -f

            echo "Deploy complete: ${{ github.sha }}"
```

**Step 2: Document required GitHub Secrets**

The following secrets must be set in the GitHub repo settings (`Settings > Secrets and variables > Actions`):

| Secret | Description |
|--------|-------------|
| `VPS_HOST` | VPS IP address (e.g., `167.172.134.211`) |
| `VPS_SSH_KEY` | Private SSH key for deploy access |
| `GHCR_TOKEN` | GitHub PAT with `read:packages` scope (for VPS to pull from GHCR) |

Note: `GITHUB_TOKEN` is automatically available in Actions (used for GHCR push).

**Step 3: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "feat: add GitHub Actions deploy workflow

On push to main (after CI passes): builds Docker images, pushes to
GHCR (tagged with SHA + latest), SSHes into VPS to pull and restart."
```

---

### Task 10: Set Up VPS for Docker Compose Deploy

Prepare the VPS to receive deploys from GitHub Actions. This replaces the current systemd-based NanoClaw setup with Docker Compose.

**Step 1: Generate deploy SSH key pair**

On your local machine:

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/globalink-deploy -N ""
cat ~/.ssh/globalink-deploy.pub  # This goes into GitHub Secrets + Terraform
cat ~/.ssh/globalink-deploy      # This goes into GitHub Secrets (VPS_SSH_KEY)
```

**Step 2: Add deploy key to VPS**

```bash
ssh root@167.172.134.211 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys" < ~/.ssh/globalink-deploy.pub
```

**Step 3: Set up deploy directory on VPS**

```bash
ssh root@167.172.134.211 << 'REMOTE'
set -e

# Create deploy directory
mkdir -p /opt/globalink-fba

# Copy docker-compose.yml and config from current setup
# (GitHub Actions will update this via git pull later, but we need it bootstrapped)

# Create env files from current secrets
cat > /opt/globalink-fba/.env.nanoclaw << 'EOF'
ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY /opt/nanoclaw/.env 2>/dev/null | cut -d= -f2 || grep CLAUDE_CODE_OAUTH_TOKEN /opt/nanoclaw/.env | cut -d= -f2)
ASSISTANT_NAME=FBA
ASSISTANT_HAS_OWN_NUMBER=true
TZ=America/Bogota
EOF

echo "VPS bootstrap complete"
REMOTE
```

**Step 4: Set GitHub Secrets**

Go to `https://github.com/alastrat/globalink-amz/settings/secrets/actions` and add:

- `VPS_HOST`: `167.172.134.211`
- `VPS_SSH_KEY`: Contents of `~/.ssh/globalink-deploy`
- `GHCR_TOKEN`: Create a GitHub PAT at `https://github.com/settings/tokens` with `read:packages` scope

**Step 5: Verify SSH from local machine**

```bash
ssh -i ~/.ssh/globalink-deploy root@167.172.134.211 "echo 'Deploy key works'"
```

Expected: `Deploy key works`

---

### Task 11: Push and Verify First Deploy

Push everything to main and verify the CI/CD pipeline works end-to-end.

**Step 1: Review all changes**

```bash
git log --oneline --since="1 hour ago"
git status
```

**Step 2: Push to main**

```bash
git push origin main
```

**Step 3: Monitor CI**

```bash
gh run watch  # Or check https://github.com/alastrat/globalink-amz/actions
```

Expected:
1. CI job runs: lint, typecheck, test → all pass
2. Build job runs: builds both Docker images, pushes to GHCR
3. Deploy job runs: SSHes to VPS, pulls images, restarts

**Step 4: Verify on VPS**

```bash
ssh root@167.172.134.211 "docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'"
```

Expected: Three containers running (nanoclaw, inngest-server, inngest-worker).

**Step 5: Verify WhatsApp still works**

Send a test message via WhatsApp to verify NanoClaw is connected and responsive.

---

### Task 12: Import Existing Droplet Into Terraform

Since the droplet already exists, import it into Terraform state rather than creating a new one.

**Step 1: Initialize Terraform**

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with real values
terraform init
```

**Step 2: Import existing resources**

```bash
# Get droplet ID
DROPLET_ID=$(ssh root@167.172.134.211 "curl -s http://169.254.169.254/metadata/v1/id")

# Import droplet
terraform import digitalocean_droplet.fba $DROPLET_ID

# Import SSH key (get ID from DO API)
# terraform import digitalocean_ssh_key.deploy <key_id>
```

Note: Reserved IP, Spaces bucket, firewall, and monitoring alerts will be created fresh by Terraform (they don't exist yet).

**Step 3: Plan and apply**

```bash
terraform plan    # Review what Terraform wants to create/change
terraform apply   # Apply (creates firewall, reserved IP, Spaces, alerts)
```

**Step 4: Verify**

```bash
terraform output
```

Expected: Shows droplet_ip, reserved_ip, spaces_bucket, spaces_endpoint.

**Step 5: Commit Terraform lock file**

```bash
cd ..
git add terraform/.terraform.lock.hcl
git commit -m "chore: add Terraform provider lock file"
```

---

## Summary: Files Created/Modified

| Task | Files | Purpose |
|------|-------|---------|
| 1 | Delete old `src/`, `config/`, etc. | Clean slate |
| 2 | `package.json`, `tsconfig.json`, `.gitignore` | Project setup |
| 3 | `nanoclaw/patches/*` (5 files) | NanoClaw patches |
| 4 | `inngest/*` (8 files) | Inngest worker stack |
| 5 | `tools/*` (6 files), `config/CLAUDE.md`, `.env.example` | Python tools + config |
| 6 | `docker/*` (2 files), `docker-compose.yml` | Containerization |
| 7 | `terraform/*` (6 files) | Infrastructure as Code |
| 8 | `.github/workflows/ci.yml`, `eslint.config.js`, `tests/smoke.test.ts` | CI pipeline |
| 9 | `.github/workflows/deploy.yml` | CD pipeline |
| 10 | VPS setup (manual) | Deploy target |
| 11 | Push + verify (manual) | End-to-end test |
| 12 | Terraform import (manual) | Import existing infra |

## Important Notes

- **Do NOT stop the current NanoClaw systemd service** until the Docker Compose version is verified working. The migration in Task 10 should be done carefully with a rollback plan (re-enable systemd if Docker version fails).
- **WhatsApp auth state** (`/opt/nanoclaw/store/`) must be preserved during the migration. The Docker volume `nanoclaw-store` must be initialized from the current auth state.
- **The NanoClaw Dockerfile clones upstream on build.** This means image builds are not fully reproducible — a future improvement would be to pin to a specific commit hash.
