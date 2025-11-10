FROM node:22.12-slim

ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache,sharing=locked \
    apt-get update \
    && apt-get install -y \
        wget \
        ca-certificates \
        fonts-liberation \
        libappindicator3-1 \
        libnss3 \
        libxss1 \
        libxtst6 \
        xdg-utils \
        chromium

ENV APPUSERID=10042
RUN groupadd -r appgroup && useradd -u $APPUSERID -r -g appgroup -m appuser

ARG NODE_ENV=production
ENV NODE_ENV=${NODE_ENV}

WORKDIR /app

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm install --verbose

COPY server.js .

USER appuser

EXPOSE 8080

CMD ["node", "server.js"]
