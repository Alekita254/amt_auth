#!/usr/bin/env bash
# Nightly backup of Keycloak's database: a pg_dump kept here for 14 days and
# copied off the server with rclone (BACKUP_REMOTE in .env, e.g. r2:amt-keycloak-backups).
#
# Run from cron, next to docker-compose.yml:
#   15 2 * * * /opt/amt-keycloak/backup.sh >> /opt/amt-keycloak/backups/backup.log 2>&1
# Restore: see "Restore a backup" in README.md.
set -euo pipefail

cd "$(dirname "$0")"
BACKUP_REMOTE="$(grep -E '^BACKUP_REMOTE=' .env 2>/dev/null | cut -d= -f2- || true)"
KEEP_DAYS=14

mkdir -p backups
file="backups/keycloak-$(date -u +%Y%m%dT%H%M%SZ).dump"

docker compose exec -T db pg_dump -U keycloak -d keycloak --format=custom > "$file.partial"
mv "$file.partial" "$file"
echo "$(date -u +%FT%TZ) wrote $file ($(du -h "$file" | cut -f1))"

find backups -name 'keycloak-*.dump' -mtime +"$KEEP_DAYS" -delete

if [ -n "$BACKUP_REMOTE" ]; then
  rclone copy "$file" "$BACKUP_REMOTE"
  rclone delete --min-age "${KEEP_DAYS}d" "$BACKUP_REMOTE"
  echo "$(date -u +%FT%TZ) copied to $BACKUP_REMOTE"
else
  echo "$(date -u +%FT%TZ) WARNING: BACKUP_REMOTE is not set; the backup exists only on this server" >&2
fi
