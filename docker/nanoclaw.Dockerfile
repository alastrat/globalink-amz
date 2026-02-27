# Stage 1: Build — clone upstream NanoClaw and compile TypeScript
FROM node:22-slim AS builder

RUN apt-get update && \
    apt-get install -y git ca-certificates --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/nanoclaw

RUN git clone https://github.com/qwibitai/nanoclaw.git .

# Install all deps (including TypeScript) but skip husky prepare hook
RUN npm install --ignore-scripts

# Compile TypeScript → dist/
RUN npx tsc

# Stage 2: Runtime — lean image with Docker CLI and production deps only
FROM node:22-slim

RUN apt-get update && \
    apt-get install -y git ca-certificates curl --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Install Docker CLI (NanoClaw spawns agent containers via Docker socket)
RUN install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc && \
    chmod a+r /etc/apt/keyrings/docker.asc && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y docker-ce-cli --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/nanoclaw

# Copy built output, package files, and production node_modules
COPY --from=builder /opt/nanoclaw/dist dist/
COPY --from=builder /opt/nanoclaw/package.json /opt/nanoclaw/package-lock.json ./
COPY --from=builder /opt/nanoclaw/node_modules node_modules/

# Prune to production-only deps
RUN npm prune --omit=dev --ignore-scripts

# Apply our patches over the compiled upstream dist/
COPY nanoclaw/patches/channels/whatsapp.js dist/channels/whatsapp.js
COPY nanoclaw/patches/ipc.js dist/ipc.js
COPY nanoclaw/patches/container-runner.js dist/container-runner.js
COPY nanoclaw/patches/index.js dist/index.js
COPY nanoclaw/patches/agent-runner-index.ts patches/agent-runner-index.ts

CMD ["node", "dist/index.js"]
