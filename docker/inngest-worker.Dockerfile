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
