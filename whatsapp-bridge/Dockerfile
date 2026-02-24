FROM node:22-slim

RUN apt-get update && apt-get install -y git --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Force git to use HTTPS instead of SSH for GitHub (no SSH keys needed)
ENV GIT_SSH_COMMAND="echo"
RUN git config --global url."https://github.com/".insteadOf "ssh://git@github.com/" && \
    git config --global url."https://github.com/".insteadOf "git@github.com:" && \
    git config --global url."https://github.com".insteadOf "ssh://git@github.com"

WORKDIR /app

COPY package.json .
RUN npm install --omit=dev

COPY index.js .

RUN mkdir -p /data/whatsapp-auth

EXPOSE 3001

CMD ["node", "index.js"]
