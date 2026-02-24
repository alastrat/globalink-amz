FROM node:22-slim

# Install Chromium for whatsapp-web.js (Puppeteer)
RUN apt-get update && apt-get install -y \
    chromium \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /app

COPY package.json .
RUN npm install --production

COPY index.js .

RUN mkdir -p /data/whatsapp-auth

EXPOSE 3001

CMD ["node", "index.js"]
