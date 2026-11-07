#!/bin/sh
# Updates the server and restarts the stack.
#
#   sh infra/scripts/deploy.sh          deploy the latest origin/main (manual deploys)
#   sh infra/scripts/deploy.sh <sha>    deploy exactly this commit (GitHub Actions passes
#                                       the commit whose CI run succeeded); it must be on
#                                       origin/main
. "$(dirname "$0")/common.sh"

ref="${1:-}"

git fetch --quiet origin main
if [ -n "${ref}" ]; then
    if ! git merge-base --is-ancestor "${ref}" origin/main 2>/dev/null; then
        echo "Refusing to deploy ${ref}: it is not a commit on origin/main." >&2
        exit 1
    fi
    target="${ref}"
else
    target="origin/main"
fi
git checkout --quiet -B main "${target}"

# Build first, then migrate, then (re)start the app: the worker runs its start-up jobs
# immediately, so the tables must exist before it starts.
compose build
compose up -d db redis
compose run --rm api alembic upgrade head
compose up -d --remove-orphans
docker image prune -f >/dev/null

echo "Deployed $(git rev-parse --short HEAD)"
