#!/bin/sh
# Nginx cannot start without the certificate files referenced in site.conf. On the very
# first start (before Let's Encrypt has issued anything) create a short-lived self-signed
# certificate; infra/scripts/init-letsencrypt.sh replaces it with the real one.
set -eu

if [ -z "${DOMAIN:-}" ]; then
    echo "DOMAIN is not set" >&2
    exit 1
fi

live="/etc/letsencrypt/live/${DOMAIN}"
if [ ! -s "${live}/fullchain.pem" ] || [ ! -s "${live}/privkey.pem" ]; then
    mkdir -p "${live}"
    openssl req -x509 -nodes -newkey rsa:2048 -days 2 \
        -keyout "${live}/privkey.pem" -out "${live}/fullchain.pem" \
        -subj "/CN=${DOMAIN}" >/dev/null 2>&1
    echo "Created a temporary self-signed certificate for ${DOMAIN}"
fi
