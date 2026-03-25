#cloud-config

package_update: true
package_upgrade: true

packages:
  - docker.io
  - docker-compose-plugin
  - fail2ban
  - ufw
  - python3
  - python3-pip

write_files:
  # ── NanoClaw .env ──────────────────────────────────────────
  - path: /opt/nanoclaw/.env
    permissions: "0600"
    content: |
      CLAUDE_CODE_OAUTH_TOKEN=${claude_oauth_token}
      ASSISTANT_NAME=${assistant_name}
      ASSISTANT_HAS_OWN_NUMBER=true
      TZ=${timezone}

  # ── NanoClaw .env (docker run --env-file copy) ────────────
  - path: /opt/globalink-fba/.env.nanoclaw
    permissions: "0600"
    content: |
      CLAUDE_CODE_OAUTH_TOKEN=${claude_oauth_token}
      ASSISTANT_NAME=${assistant_name}
      ASSISTANT_HAS_OWN_NUMBER=true
      TZ=${timezone}

  # ── Inngest / app .env ─────────────────────────────────────
  - path: /opt/globalink-fba/.env
    permissions: "0600"
    content: |
      INNGEST_EVENT_KEY=fba-${client_name}-event-key
      INNGEST_SIGNING_KEY=signkey-${client_name}-placeholder
      CHAT_JID=${owner_whatsapp}@s.whatsapp.net
      DASHBOARD_USER=${dashboard_user}
      DASHBOARD_PASS=${dashboard_pass}

  # ── SP-API / tool credentials ──────────────────────────────
  - path: /opt/nanoclaw/groups/owner/tools/.env
    permissions: "0600"
    content: |
      SP_API_LWA_APP_ID=${sp_api_lwa_app_id}
      SP_API_LWA_CLIENT_SECRET=${sp_api_lwa_client_secret}
      SP_API_REFRESH_TOKEN=${sp_api_refresh_token}
      AMAZON_SELLER_ID=${amazon_seller_id}
      AMAZON_MARKETPLACE_ID=${amazon_marketplace_id}
%{ if firecrawl_api_key != "" ~}
      FIRECRAWL_API_KEY=${firecrawl_api_key}
%{ endif ~}
%{ if exa_api_key != "" ~}
      EXA_API_KEY=${exa_api_key}
%{ endif ~}

  # ── Docker Compose ─────────────────────────────────────────
  - path: /opt/globalink-fba/docker-compose.yml
    permissions: "0644"
    content: |
      services:
        inngest-server:
          image: inngest/inngest:latest
          container_name: globalink-fba-inngest-server-1
          restart: always
          ports:
            - "127.0.0.1:8288:8288"
          environment:
            - INNGEST_EVENT_KEY=$${INNGEST_EVENT_KEY:-fba-${client_name}-event-key}
            - INNGEST_SIGNING_KEY=$${INNGEST_SIGNING_KEY:-signkey-placeholder}
          env_file:
            - .env
          command: >
            inngest dev
            -u http://inngest-worker:3500/api/inngest
            --no-discovery
          networks:
            - inngest

        inngest-worker:
          image: ghcr.io/alastrat/globalink-amz/inngest-worker:latest
          container_name: globalink-fba-inngest-worker-1
          restart: always
          ports:
            - "0.0.0.0:8080:3500"
          env_file:
            - .env
          environment:
            - INNGEST_BASE_URL=http://inngest-server:8288
            - IPC_DIR=/opt/nanoclaw/data/ipc/owner/messages
            - CACHE_DIR=/cache
            - TOOLS_DIR=/tools
            - CHAT_JID=${owner_whatsapp}@s.whatsapp.net
          volumes:
            - /opt/nanoclaw/groups/owner/tools:/tools:ro
            - /opt/nanoclaw/data:/opt/nanoclaw/data
            - /opt/nanoclaw/groups/owner/cache:/cache
          depends_on:
            - inngest-server
          networks:
            - inngest

      networks:
        inngest:
          driver: bridge

  # ── WhatsApp QR Setup Script ───────────────────────────────
  - path: /opt/nanoclaw/setup-wa.js
    permissions: "0644"
    content: |
      import makeWASocket, {
        useMultiFileAuthState,
        fetchLatestWaWebVersion,
        Browsers,
        DisconnectReason,
      } from "@whiskeysockets/baileys";
      import qrcode from "qrcode-terminal";
      import pino from "pino";

      const logger = pino({ level: "warn" });

      async function setup() {
        const { state, saveCreds } = await useMultiFileAuthState("./store/auth");
        const { version } = await fetchLatestWaWebVersion();

        console.log("Connecting to WhatsApp...");

        const sock = makeWASocket({
          version,
          auth: { creds: state.creds, keys: state.keys },
          logger,
          browser: Browsers.macOS("Chrome"),
        });

        sock.ev.on("creds.update", saveCreds);

        sock.ev.on("connection.update", (update) => {
          const { connection, lastDisconnect, qr } = update;

          if (qr) {
            console.log("\nScan this QR code with WhatsApp:\n");
            qrcode.generate(qr, { small: true });
            console.log(
              "\nOpen WhatsApp -> Settings -> Linked Devices -> Link a Device\n"
            );
          }

          if (connection === "open") {
            console.log("\nConnected to WhatsApp successfully!");
            setTimeout(() => process.exit(0), 2000);
          }

          if (connection === "close") {
            const reason =
              lastDisconnect?.error?.output?.statusCode;
            if (reason === DisconnectReason.loggedOut) {
              console.log("Logged out.");
              process.exit(1);
            }
            setup();
          }
        });
      }

      setup().catch(console.error);

  # ── Token Auto-Refresh Script ──────────────────────────────
  - path: /opt/nanoclaw/refresh-token.sh
    permissions: "0755"
    content: |
      #!/usr/bin/env bash
      set -euo pipefail

      LOG="/var/log/token-refresh.log"
      CREDS="/root/.claude/.credentials.json"
      NANOCLAW_ENV="/opt/nanoclaw/.env"
      NANOCLAW_DOCKER_ENV="/opt/globalink-fba/.env.nanoclaw"

      log() { echo "$$(date -u '+%Y-%m-%dT%H:%M:%SZ') $$*" >> "$$LOG"; }

      if [ ! -f "$$CREDS" ]; then
        log "ERROR: credentials file not found at $$CREDS"
        exit 1
      fi

      EXPIRES_AT=$$(python3 -c "import json; print(json.load(open('$$CREDS'))['claudeAiOauth']['expiresAt'])")
      NOW=$$(date +%s)
      TWO_HOURS=7200
      REMAINING=$$((EXPIRES_AT - NOW))

      if [ "$$REMAINING" -gt "$$TWO_HOURS" ]; then
        log "Token still valid for $$REMAINING seconds, skipping refresh"
        exit 0
      fi

      log "Token expires in $$REMAINING seconds, refreshing..."

      REFRESH_TOKEN=$$(python3 -c "import json; print(json.load(open('$$CREDS'))['claudeAiOauth']['refreshToken'])")

      RESPONSE=$$(curl -s -X POST "https://console.anthropic.com/v1/oauth/token" \
        -H "Content-Type: application/json" \
        -d "{\"grant_type\":\"refresh_token\",\"refresh_token\":\"$$REFRESH_TOKEN\"}")

      NEW_ACCESS_TOKEN=$$(echo "$$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['access_token'])")
      NEW_REFRESH_TOKEN=$$(echo "$$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('refresh_token','$$REFRESH_TOKEN'))")
      NEW_EXPIRES_IN=$$(echo "$$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('expires_in',3600))")
      NEW_EXPIRES_AT=$$((NOW + NEW_EXPIRES_IN))

      if [ -z "$$NEW_ACCESS_TOKEN" ] || [ "$$NEW_ACCESS_TOKEN" = "None" ]; then
        log "ERROR: failed to obtain new access token. Response: $$RESPONSE"
        exit 1
      fi

      # Update credentials file
      python3 -c "
      import json
      creds = json.load(open('$$CREDS'))
      creds['claudeAiOauth']['accessToken'] = '$$NEW_ACCESS_TOKEN'
      creds['claudeAiOauth']['refreshToken'] = '$$NEW_REFRESH_TOKEN'
      creds['claudeAiOauth']['expiresAt'] = $$NEW_EXPIRES_AT
      json.dump(creds, open('$$CREDS','w'), indent=2)
      "

      # Update NanoClaw .env files
      for envfile in "$$NANOCLAW_ENV" "$$NANOCLAW_DOCKER_ENV"; do
        if [ -f "$$envfile" ]; then
          sed -i "s|^CLAUDE_CODE_OAUTH_TOKEN=.*|CLAUDE_CODE_OAUTH_TOKEN=$$NEW_ACCESS_TOKEN|" "$$envfile"
        fi
      done

      # Restart NanoClaw container
      docker restart globalink-fba-nanoclaw 2>/dev/null || true

      log "Token refreshed successfully, expires at $$NEW_EXPIRES_AT"

  # ── Claude Credentials ─────────────────────────────────────
  - path: /root/.claude/.credentials.json
    permissions: "0600"
    content: |
      {"claudeAiOauth":{"accessToken":"${claude_oauth_token}","refreshToken":"${claude_refresh_token}","expiresAt":0}}

runcmd:
  # ── Directory structure ──────────────────────────────────────
  - mkdir -p /opt/nanoclaw/store
  - mkdir -p /opt/nanoclaw/data/ipc/owner/messages
  - mkdir -p /opt/nanoclaw/data/ipc/owner/tasks
  - mkdir -p /opt/nanoclaw/data/ipc/owner/input
  - mkdir -p /opt/nanoclaw/data/sessions/owner/.claude
  - mkdir -p /opt/nanoclaw/groups/owner/tools
  - mkdir -p /opt/nanoclaw/groups/owner/cache
  - mkdir -p /opt/nanoclaw/groups/owner/data
  - mkdir -p /opt/nanoclaw/groups/owner/logs
  - mkdir -p /opt/globalink-fba
  - mkdir -p /root/.claude

  # ── Enable Docker ────────────────────────────────────────────
  - systemctl enable docker
  - systemctl start docker

  # ── Configure UFW ────────────────────────────────────────────
  - ufw default deny incoming
  - ufw default allow outgoing
  - ufw allow ssh
  - ufw --force enable

  # ── Docker logging config ────────────────────────────────────
  - |
    cat > /etc/docker/daemon.json << 'DOCKER_CONF'
    {
      "log-driver": "json-file",
      "log-opts": {
        "max-size": "10m",
        "max-file": "3"
      }
    }
    DOCKER_CONF
  - systemctl restart docker

  # ── Randomize Inngest signing key ────────────────────────────
  - |
    SIGNING_KEY="signkey-${client_name}-$$(openssl rand -hex 16)"
    sed -i "s|signkey-${client_name}-placeholder|$$SIGNING_KEY|" /opt/globalink-fba/.env

  # ── Login to GHCR ────────────────────────────────────────────
  - echo "${ghcr_token}" | docker login ghcr.io -u ${ghcr_user} --password-stdin

  # ── Pull images ──────────────────────────────────────────────
  - docker pull ghcr.io/alastrat/globalink-amz/nanoclaw:latest
  - docker pull ghcr.io/alastrat/globalink-amz/inngest-worker:latest
  - docker pull inngest/inngest:latest

  # ── Start Inngest stack ──────────────────────────────────────
  - cd /opt/globalink-fba && docker compose up -d

  # ── Wait for Docker network ──────────────────────────────────
  - sleep 5

  # ── Start NanoClaw ───────────────────────────────────────────
  - |
    docker run -d \
      --name globalink-fba-nanoclaw \
      --restart always \
      --env-file /opt/globalink-fba/.env.nanoclaw \
      --network globalink-fba_inngest \
      -v /var/run/docker.sock:/var/run/docker.sock \
      -v /opt/nanoclaw/store:/opt/nanoclaw/store \
      -v /opt/nanoclaw/data:/opt/nanoclaw/data \
      -v /opt/nanoclaw/groups:/opt/nanoclaw/groups \
      -v /opt/nanoclaw/.env:/opt/nanoclaw/.env:ro \
      ghcr.io/alastrat/globalink-amz/nanoclaw:latest

  # ── Setup cron for token refresh ─────────────────────────────
  - echo "0 * * * * /opt/nanoclaw/refresh-token.sh" | crontab -

  # ── Mark provisioning complete ───────────────────────────────
  - touch /opt/provisioning-complete
