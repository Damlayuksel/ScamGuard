#!/bin/sh
# Certbot renews certificates in its own container; reload Nginx regularly so renewed
# certificates are picked up without a restart.
(
    while :; do
        sleep 6h
        nginx -s reload >/dev/null 2>&1 || true
    done
) &
