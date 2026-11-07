#!/bin/sh
# Forced command for the GitHub Actions deploy key. In ~/.ssh/authorized_keys of the
# deploy user the key is installed as:
#
#   restrict,command="/home/deploy/scamshield/infra/scripts/ssh-deploy-entry.sh" ssh-ed25519 AAAA... github-actions
#
# so even a leaked key can only run "deploy <commit sha>", and deploy.sh only accepts
# commits that are on origin/main.
set -eu

request="${SSH_ORIGINAL_COMMAND:-}"

case "${request}" in
    "deploy "*) sha="${request#deploy }" ;;
    *)
        echo "Only 'deploy <commit sha>' is allowed." >&2
        exit 1
        ;;
esac

# Exactly 40 lowercase hex characters; rejects spaces, newlines and shell syntax.
case "${sha}" in
    "" | *[!0-9a-f]*)
        echo "Invalid commit sha." >&2
        exit 1
        ;;
esac
if [ "${#sha}" -ne 40 ]; then
    echo "Invalid commit sha." >&2
    exit 1
fi

exec sh "$(dirname "$0")/deploy.sh" "${sha}"
