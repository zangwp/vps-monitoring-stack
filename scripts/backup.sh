#!/usr/bin/env bash
# PostgreSQL logical dump + stopped Komari data; no live database directory tar.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
umask 077
command -v flock >/dev/null
mkdir -p backups
exec 9> backups/.backup.lock
flock -n 9 || { echo 'Another backup is running.' >&2; exit 1; }
docker compose config --quiet
for service in komari umami-db; do
  [[ -n "$(docker compose ps --status running -q "$service")" ]] || {
    echo "$service must be running before backup." >&2; exit 1;
  }
done
backup=$(mktemp -d "backups/$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")
komari_stopped=0
cleanup() {
  if [[ "$komari_stopped" == 1 ]]; then docker compose start komari; fi
}
trap cleanup EXIT
docker compose exec -T umami-db pg_dump -U umami -d umami -Fc > "$backup/umami.dump"
docker compose exec -T umami-db pg_restore --list < "$backup/umami.dump" > "$backup/umami.contents"
komari_stopped=1
docker compose stop komari
tar -czf "$backup/komari.tar.gz" -C data komari
tar -tzf "$backup/komari.tar.gz" >/dev/null
docker compose start komari
komari_stopped=0
cp .env compose.yaml compose.dns.yaml Caddyfile Caddyfile.manual Caddyfile.dns "$backup/"
docker compose images > "$backup/images.txt"
(cd "$backup"; sha256sum umami.dump komari.tar.gz .env compose.yaml compose.dns.yaml Caddyfile Caddyfile.manual Caddyfile.dns images.txt umami.contents > SHA256SUMS)
touch "$backup/COMPLETE"
echo "Backup complete: $backup"
echo 'Contains secrets and personal data. Keep an encrypted off-server copy; incomplete folders lack COMPLETE.'
