# Production web image: builds the Expo static site and serves it with Nginx.
# Build context: repository root (see infra/docker-compose.prod.yml).

FROM node:24-bookworm-slim AS build
WORKDIR /app/mobile

COPY mobile/package.json mobile/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY mobile/ ./
# Same origin in production: the API is served under /api by Nginx.
ENV EXPO_PUBLIC_API_URL=""
RUN npx expo export --platform web

COPY infra/nginx/check-csp.mjs infra/nginx/templates/security-headers.inc.template /tmp/
RUN node /tmp/check-csp.mjs dist /tmp/security-headers.inc.template

FROM nginx:stable-alpine

RUN apk add --no-cache openssl \
    && rm -f /etc/nginx/conf.d/default.conf \
    && mkdir -p /var/www/certbot

COPY infra/nginx/nginx.conf /etc/nginx/nginx.conf
COPY infra/nginx/templates/ /etc/nginx/templates/
COPY infra/nginx/docker-entrypoint.d/ /docker-entrypoint.d/
RUN chmod +x /docker-entrypoint.d/*.sh

COPY --from=build /app/mobile/dist /usr/share/nginx/html
