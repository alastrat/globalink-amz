# Infrastructure, CI/CD & TypeScript Rewrite Design

**Date**: 2026-02-25
**Status**: Approved
**Context**: The FBA agent runs on a DigitalOcean VPS with manually deployed code. No CI/CD, no IaC, no type safety. This design addresses all three.

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Repo cleanup | Clean slate (remove old CrewAI code) | Old code is unused; production runs NanoClaw + Inngest |
| CI/CD | GitHub Actions → build images → push GHCR → deploy VPS | Immutable deployments, rollback via image tags |
| Deploy trigger | Push to main + tests pass | Safe automation without extra manual steps |
| Infrastructure | Terraform (full stack DO) | Droplet, firewall, reserved IP, Spaces, monitoring |
| Secrets | Terraform (infra) + GitHub Secrets (app) | Free, clear separation |
| NanoClaw runtime | Containerized (custom Docker image) | Aligns with Docker blog approach; eliminates bare-metal fragility |
| TypeScript patterns | Discriminated unions + Transport interface | KISS-approved by 3 architect evaluations (no GoF class hierarchies) |

## 1. Repository Structure

```
globalink-amz/
├── src/                              # TypeScript source (monorepo, single build)
│   ├── shared/                       # Shared types and utilities
│   │   ├── types/
│   │   │   ├── messages.ts           # OutboundMessage, InboundMessage unions
│   │   │   ├── products.ts           # Product, ProductAnalysis, etc.
│   │   │   └── ipc.ts               # IPC payload schemas (Zod + TS)
│   │   └── validation.ts            # Zod schemas (runtime validation)
│   │
│   ├── nanoclaw/                     # NanoClaw patches (replaces monkey-patched JS)
│   │   ├── transport/
│   │   │   └── whatsapp.ts          # WhatsApp transport (sendMessage, sendImage, sendQuotedReply)
│   │   ├── ipc/
│   │   │   └── watcher.ts           # IPC file watcher (reads JSON, dispatches via transport)
│   │   ├── interceptors/
│   │   │   ├── detalles.ts          # "detalles B0XXX" handler
│   │   │   └── research.ts          # "research" → Inngest trigger
│   │   ├── container-runner.ts       # Container spawning (applies interceptors before agent)
│   │   └── index.ts                 # Entry point, wires deps
│   │
│   └── inngest/                      # Inngest worker
│       ├── server.ts                 # Express + Inngest serve
│       ├── functions/
│       │   └── research.ts           # Product research pipeline
│       └── lib/
│           ├── ipc.ts               # Write IPC JSON (sendProgress, sendImage, sendProductCard)
│           └── tools.ts             # Python tool executor
│
├── tools/                            # Python tools (unchanged, mounted into containers)
│   ├── sp-api-query.py
│   ├── cache.py
│   ├── bsr-estimator.py
│   ├── exa-search.py
│   ├── firecrawl-scrape.py
│   └── .env.example
│
├── config/
│   ├── CLAUDE.md                     # Business logic for the agent
│   └── REFERENCE.md                  # Command reference
│
├── docker/
│   ├── nanoclaw.Dockerfile           # NanoClaw + patches (FROM node:22-slim)
│   ├── inngest-worker.Dockerfile     # Inngest worker (FROM node:20-slim + python3)
│   └── docker-compose.yml            # Full stack: nanoclaw + inngest-server + inngest-worker
│
├── terraform/
│   ├── main.tf                       # DO droplet, firewall, reserved IP, Spaces
│   ├── variables.tf                  # Configurable inputs
│   ├── outputs.tf                    # IP, droplet ID, etc.
│   ├── versions.tf                   # Provider versions
│   └── terraform.tfvars.example      # Example values
│
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Lint + typecheck + test on every push
│       └── deploy.yml                # Build → GHCR → deploy (on main, after CI passes)
│
├── tsconfig.json                     # TypeScript config (strict mode)
├── package.json                      # Dependencies, scripts
├── .env.example                      # All env vars with placeholders
└── .gitignore
```

## 2. TypeScript Architecture

### Core Principle: Discriminated Unions + Exhaustive Switches

No abstract classes. No GoF patterns. Pure functions where possible. Interfaces only for dependency injection (Transport, Database).

### 2a. Message Types (the contract layer)

```typescript
// src/shared/types/messages.ts

export type OutboundMessage =
  | { type: "text";          to: string; body: string }
  | { type: "image";         to: string; url: string; caption?: string }
  | { type: "quoted_reply";  to: string; body: string; quotedId: string }
  | { type: "button";        to: string; body: string; buttons: ButtonDef[] };

export type ButtonDef = { id: string; label: string };

export type InboundMessage = {
  from: string;
  text: string;
  messageId: string;
  timestamp: number;
};

export type SentMessageKey = {
  remoteJid: string;
  fromMe: boolean;
  id: string;
};
```

### 2b. Runtime Validation (Zod, at system boundaries only)

```typescript
// src/shared/validation.ts

import { z } from "zod";

const TextMsg = z.object({ type: z.literal("text"), to: z.string(), body: z.string() });
const ImageMsg = z.object({ type: z.literal("image"), to: z.string(), url: z.string(), caption: z.string().optional() });
const QuotedMsg = z.object({ type: z.literal("quoted_reply"), to: z.string(), body: z.string(), quotedId: z.string() });
const ButtonMsg = z.object({
  type: z.literal("button"), to: z.string(), body: z.string(),
  buttons: z.array(z.object({ id: z.string(), label: z.string() })),
});

export const OutboundMessageSchema = z.discriminatedUnion("type", [TextMsg, ImageMsg, QuotedMsg, ButtonMsg]);

// IPC payload (what Inngest worker writes to disk)
export const IpcPayloadSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("message"), chatJid: z.string(), text: z.string(), storeKeyAs: z.string().optional() }),
  z.object({ type: z.literal("image"), chatJid: z.string(), imageUrl: z.string(), caption: z.string().optional(), storeKeyAs: z.string().optional() }),
  z.object({ type: z.literal("quoted_reply"), chatJid: z.string(), text: z.string(), quotedKeyFile: z.string() }),
]);

export type IpcPayload = z.infer<typeof IpcPayloadSchema>;
```

### 2c. Transport Interface (dependency injection, not a Facade)

```typescript
// src/nanoclaw/transport/whatsapp.ts

import type { OutboundMessage, SentMessageKey } from "../../shared/types/messages";

export interface Transport {
  send(msg: OutboundMessage): Promise<SentMessageKey | null>;
  sendQuotedReply(jid: string, text: string, quotedKey: SentMessageKey): Promise<void>;
}

export class WhatsAppTransport implements Transport {
  constructor(private sock: WASocket) {}

  async send(msg: OutboundMessage): Promise<SentMessageKey | null> {
    const jid = `${msg.to}@s.whatsapp.net`;
    switch (msg.type) {
      case "text": {
        const sent = await this.sock.sendMessage(jid, { text: msg.body });
        return sent?.key ?? null;
      }
      case "image": {
        const sent = await this.sock.sendMessage(jid, { image: { url: msg.url }, caption: msg.caption });
        return sent?.key ?? null;
      }
      case "quoted_reply": {
        await this.sock.sendMessage(jid, { text: msg.body }, {
          quoted: { key: { id: msg.quotedId }, message: { conversation: "" } },
        });
        return null;
      }
      case "button": {
        const sent = await this.sock.sendMessage(jid, {
          text: msg.body,
          buttons: msg.buttons.map(b => ({ buttonId: b.id, buttonText: { displayText: b.label }, type: 1 })),
        });
        return sent?.key ?? null;
      }
      default:
        assertNever(msg);
    }
  }

  async sendQuotedReply(jid: string, text: string, quotedKey: SentMessageKey): Promise<void> {
    await this.sock.sendMessage(jid, { text }, {
      quoted: { key: quotedKey, message: { conversation: "" } },
    });
  }
}

function assertNever(x: never): never {
  throw new Error(`Unhandled message type: ${JSON.stringify(x)}`);
}
```

### 2d. IPC Watcher (reads JSON files, validates, dispatches)

```typescript
// src/nanoclaw/ipc/watcher.ts

import { IpcPayloadSchema, type IpcPayload } from "../../shared/validation";
import type { Transport, SentMessageKey } from "../transport/whatsapp";

export function handleIpcPayload(
  payload: IpcPayload,
  transport: Transport,
  keyStore: KeyStore,
): Promise<void> {
  switch (payload.type) {
    case "message": {
      const key = await transport.send({ type: "text", to: payload.chatJid, body: payload.text });
      if (payload.storeKeyAs && key) keyStore.save(payload.storeKeyAs, key);
      return;
    }
    case "image": {
      const key = await transport.send({ type: "image", to: payload.chatJid, url: payload.imageUrl, caption: payload.caption });
      if (payload.storeKeyAs && key) keyStore.save(payload.storeKeyAs, key);
      return;
    }
    case "quoted_reply": {
      const storedKey = keyStore.load(payload.quotedKeyFile);
      if (storedKey) {
        await transport.sendQuotedReply(payload.chatJid, payload.text, storedKey);
      } else {
        await transport.send({ type: "text", to: payload.chatJid, body: payload.text });
      }
      return;
    }
    default:
      assertNever(payload);
  }
}

// Simple file-based key store
export interface KeyStore {
  save(id: string, key: SentMessageKey): void;
  load(id: string): SentMessageKey | null;
}
```

### 2e. Interceptors (detalles + research, pure functions)

```typescript
// src/nanoclaw/interceptors/detalles.ts

export function matchDetalles(text: string): string | null {
  const match = text.match(/\bdetalles\s+(B0[A-Z0-9]{8})\b/i);
  return match ? match[1] : null;
}

export function formatFullDetails(product: ProductAnalysis): string {
  // ... same formatting logic, but typed
}
```

```typescript
// src/nanoclaw/interceptors/research.ts

export function matchResearch(text: string): { query?: string; asin?: string; cost?: number } | null {
  const re = /\b(research|analyze|analizar|investigar|analiza|investiga)\b/i;
  if (!re.test(text)) return null;
  const asinMatch = text.match(/\bB0[A-Z0-9]{8}\b/);
  const costMatch = text.match(/cost\s+(\d+\.?\d*)/i);
  return {
    query: asinMatch ? undefined : text,
    asin: asinMatch?.[0],
    cost: costMatch ? parseFloat(costMatch[1]) : undefined,
  };
}
```

### 2f. How Adding a New Message Type Works

1. Add variant to `OutboundMessage` union in `types/messages.ts`
2. Add Zod schema variant to `validation.ts`
3. Add `case` to `WhatsAppTransport.send()` switch
4. Compiler flags any other switches that are now non-exhaustive

**2 files for types, 1 file for transport. Compiler catches the rest.**

## 3. Docker Architecture

### 3a. NanoClaw Container

```dockerfile
# docker/nanoclaw.Dockerfile
FROM node:22-slim

RUN apt-get update && apt-get install -y git docker.io --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/nanoclaw

# Install upstream NanoClaw
RUN git clone https://github.com/qwibitai/nanoclaw.git . && npm install

# Copy our compiled patches over upstream dist/
COPY dist/nanoclaw/ dist/

# Copy agent-runner patch
COPY dist/nanoclaw/patches/ patches/

# Config and tools are mounted at runtime (not baked into image)
# /workspace/group  → /opt/nanoclaw/groups/owner
# /workspace/tools  → Python tools
# /var/run/docker.sock → for spawning agent containers

CMD ["node", "dist/index.js"]
```

Key: NanoClaw spawns agent containers via Docker, so the host Docker socket is mounted (`-v /var/run/docker.sock:/var/run/docker.sock`).

### 3b. Inngest Worker Container

```dockerfile
# docker/inngest-worker.Dockerfile
FROM node:20-slim

RUN apt-get update && apt-get install -y python3 python3-pip --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY dist/inngest/ .
RUN npm install --production

CMD ["node", "server.js"]
```

### 3c. Docker Compose (full stack)

```yaml
# docker/docker-compose.yml
services:
  nanoclaw:
    image: ghcr.io/alastrat/globalink-amz/nanoclaw:latest
    restart: always
    env_file: .env.nanoclaw
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - nanoclaw-store:/opt/nanoclaw/store          # WhatsApp auth state
      - nanoclaw-data:/opt/nanoclaw/data             # IPC, sessions
      - ./groups/owner:/opt/nanoclaw/groups/owner     # Config, tools, cache
    networks:
      - inngest

  inngest-server:
    image: inngest/inngest:latest
    restart: always
    ports:
      - "8288:8288"
    environment:
      - INNGEST_EVENT_KEY=${INNGEST_EVENT_KEY}
      - INNGEST_SIGNING_KEY=${INNGEST_SIGNING_KEY}
    volumes:
      - inngest-data:/var/lib/inngest
    command: inngest dev -u http://inngest-worker:3500/api/inngest --no-discovery
    networks:
      - inngest

  inngest-worker:
    image: ghcr.io/alastrat/globalink-amz/inngest-worker:latest
    restart: always
    env_file: .env.inngest
    volumes:
      - ./groups/owner/tools:/tools:ro
      - nanoclaw-data:/opt/nanoclaw/data             # Shared IPC directory
      - ./groups/owner/cache:/cache
    depends_on:
      - inngest-server
    networks:
      - inngest

volumes:
  nanoclaw-store:
  nanoclaw-data:
  inngest-data:

networks:
  inngest:
```

## 4. Terraform (DigitalOcean Full Stack)

```hcl
# terraform/main.tf

resource "digitalocean_droplet" "fba" {
  name     = "globalink-fba"
  image    = "ubuntu-24-04-x64"
  size     = "s-2vcpu-4gb"
  region   = "nyc1"
  ssh_keys = [digitalocean_ssh_key.deploy.fingerprint]
  tags     = ["fba", "production"]

  user_data = file("${path.module}/cloud-init.yml")
}

resource "digitalocean_reserved_ip" "fba" {
  region = "nyc1"
}

resource "digitalocean_reserved_ip_assignment" "fba" {
  ip_address = digitalocean_reserved_ip.fba.ip_address
  droplet_id = digitalocean_droplet.fba.id
}

resource "digitalocean_firewall" "fba" {
  name        = "fba-firewall"
  droplet_ids = [digitalocean_droplet.fba.id]

  # SSH (restricted to GitHub Actions + your IP)
  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = var.allowed_ssh_ips
  }

  # All outbound (WhatsApp, APIs, Docker pulls)
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
}

resource "digitalocean_spaces_bucket" "backups" {
  name   = "globalink-fba-backups"
  region = "nyc3"
  acl    = "private"
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
  description = "FBA droplet CPU > 90%"
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

resource "digitalocean_ssh_key" "deploy" {
  name       = "github-actions-deploy"
  public_key = var.deploy_ssh_public_key
}
```

## 5. CI/CD (GitHub Actions)

### 5a. CI — every push

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
        with: { node-version: 22 }
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm test
```

### 5b. Deploy — push to main, after CI passes

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  ci:
    uses: ./.github/workflows/ci.yml

  build-and-push:
    needs: ci
    runs-on: ubuntu-latest
    permissions:
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build TypeScript
        run: npm ci && npm run build

      - name: Build and push NanoClaw image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/nanoclaw.Dockerfile
          push: true
          tags: ghcr.io/alastrat/globalink-amz/nanoclaw:${{ github.sha }},ghcr.io/alastrat/globalink-amz/nanoclaw:latest

      - name: Build and push Inngest worker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/inngest-worker.Dockerfile
          push: true
          tags: ghcr.io/alastrat/globalink-amz/inngest-worker:${{ github.sha }},ghcr.io/alastrat/globalink-amz/inngest-worker:latest

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to VPS
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: root
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/globalink-fba
            docker compose pull
            docker compose up -d --remove-orphans
            docker image prune -f
```

### Deploy flow:
```
Push to main → CI (lint + typecheck + test) → Build TS → Build Docker images
  → Push to GHCR (tagged with SHA + latest) → SSH into VPS → docker compose pull → up -d
```

## 6. Secrets Management

| Secret | Stored In | Injected How |
|--------|-----------|-------------|
| `ANTHROPIC_API_KEY` | GitHub Secrets | Deploy writes to `.env.nanoclaw` on VPS |
| `SP_API_*` credentials | GitHub Secrets | Deploy writes to `tools/.env` on VPS |
| `FIRECRAWL_API_KEY` | GitHub Secrets | Deploy writes to `tools/.env` on VPS |
| `EXA_API_KEY` | GitHub Secrets | Deploy writes to `tools/.env` on VPS |
| `INNGEST_EVENT_KEY` | GitHub Secrets | Deploy writes to `.env.inngest` on VPS |
| `DO_TOKEN` | GitHub Secrets | Used by Terraform in CI |
| `VPS_SSH_KEY` | GitHub Secrets | Used by deploy action |
| `DEPLOY_SSH_PUBLIC_KEY` | Terraform variable | Added to droplet on creation |

No secrets in the repo. `.env*` files are gitignored. Deploy step writes them from GitHub Secrets.

## 7. Migration Path

The TypeScript rewrite + containerization is a significant change. Phased approach:

**Phase 1**: Repo restructure + CI/CD + Terraform (no code rewrite)
- Pull current VPS files into repo as-is (JS, not TS)
- Set up GitHub Actions, GHCR, deploy pipeline
- Set up Terraform for existing infra
- Goal: automated deploys working

**Phase 2**: TypeScript rewrite
- Rewrite NanoClaw patches in TypeScript
- Rewrite Inngest worker in TypeScript
- Add Zod validation, typed contracts
- Goal: type-safe codebase, same runtime behavior

**Phase 3**: NanoClaw containerization
- Build custom NanoClaw Docker image
- Migrate from systemd to docker compose
- Goal: fully containerized stack, immutable deploys
