FROM node:24.11-slim

RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache,sharing=locked \
    apt-get update \
    && apt-get install -y \
        wget \
        ca-certificates \
        fonts-liberation \
        libappindicator3-1 \
        libasound2 \
        libnss3 \
        libxss1 \
        libxtst6 \
        xdg-utils

ARG NODE_ENV=production
ENV NODE_ENV=${NODE_ENV}

WORKDIR /app

ENV PUPPETEER_SKIP_DOWNLOAD=true
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --verbose

# Allow any user to find chrome with puppeteer.executablePath()
ENV PUPPETEER_CACHE_DIR=/usr/local/share/puppeteer
RUN npx puppeteer browsers install chrome

COPY src/ ./

EXPOSE 8080

CMD ["node", "server.js"]

# Allow running container in readonly mode
ENV XDG_CONFIG_HOME=/tmp/.chromium \
    XDG_CACHE_HOME=/tmp/.chromium
