#!/bin/sh
# One-time: replaces the temporary self-signed certificate with a Let's Encrypt one.
# Requires DNS A/AAAA records for DOMAIN and www.DOMAIN pointing to this server.
# Use STAGING=1 for a test run (avoids Let's Encrypt rate limits).
. "$(dirname "$0")/common.sh"

DOMAIN="$(env_value DOMAIN)"
EMAIL="$(env_value LETSENCRYPT_EMAIL)"

if [ -z "${DOMAIN}" ] || [ -z "${EMAIL}" ]; then
    echo "Set DOMAIN and LETSENCRYPT_EMAIL in infra/.env.prod first." >&2
    exit 1
fi

staging=""
if [ "${STAGING:-0}" = "1" ]; then
    staging="--staging"
fi

echo "Starting Nginx (it serves the ACME challenge on port 80)..."
compose up -d --build web

echo "Removing the temporary certificate for ${DOMAIN}..."
compose run --rm --entrypoint /bin/sh certbot -c \
    "rm -rf /etc/letsencrypt/live/${DOMAIN} /etc/letsencrypt/archive/${DOMAIN} /etc/letsencrypt/renewal/${DOMAIN}.conf"

echo "Requesting a certificate for ${DOMAIN} and www.${DOMAIN}..."
compose run --rm --entrypoint certbot certbot certonly ${staging} \
    --webroot -w /var/www/certbot \
    -d "${DOMAIN}" -d "www.${DOMAIN}" \
    --email "${EMAIL}" --agree-tos --no-eff-email --non-interactive

compose exec web nginx -s reload
compose up -d certbot
echo "Done: https://${DOMAIN}"
