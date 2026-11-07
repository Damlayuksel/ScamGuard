#!/bin/sh
# Nightly Postgres backup, kept for 7 days on this server only (decided 2026-10-14).
# The database holds no message text; only blacklist entries, domain statistics and
# hashes. Install with cron (see infra/README.md).
. "$(dirname "$0")/common.sh"

BACKUP_DIR="${BACKUP_DIR:-/var/backups/scamshield}"
KEEP_DAYS="${KEEP_DAYS:-7}"
USER_NAME="$(env_value POSTGRES_USER)"
DB_NAME="$(env_value POSTGRES_DB)"

umask 077
mkdir -p "${BACKUP_DIR}"

file="${BACKUP_DIR}/scamshield-$(date +%Y%m%d-%H%M%S).sql.gz"
partial="${file}.partial"

# Dump to a file first: in a "pg_dump | gzip" pipe a failing pg_dump would go unnoticed
# and leave an empty backup.
if ! compose exec -T db pg_dump -U "${USER_NAME}" -d "${DB_NAME}" --no-owner > "${partial}"; then
    rm -f "${partial}"
    echo "Backup failed: pg_dump returned an error." >&2
    exit 1
fi
gzip -c "${partial}" > "${file}"
rm -f "${partial}"

find "${BACKUP_DIR}" -name 'scamshield-*.sql.gz' -mtime "+${KEEP_DAYS}" -delete
echo "Backup written: ${file} ($(du -h "${file}" | cut -f1))"
