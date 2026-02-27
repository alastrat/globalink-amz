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
