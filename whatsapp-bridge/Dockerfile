FROM node:22-slim

RUN apt-get update && apt-get install -y git openssh-client --no-install-recommends && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json .
RUN npm install --omit=dev

COPY index.js .

RUN mkdir -p /data/whatsapp-auth

EXPOSE 3001

CMD ["node", "index.js"]
