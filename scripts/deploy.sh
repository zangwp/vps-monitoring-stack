#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ -f .env ]] || { echo 'Run bash scripts/init.sh first.' >&2; exit 1; }
if grep -Eq '^(ACME_EMAIL|KOMARI_DOMAIN|UMAMI_DOMAIN)=.*example\.com' .env; then
  echo 'Replace example email and domains in .env first.' >&2
  exit 1
fi
docker compose version >/dev/null
docker compose config --quiet
docker compose pull
docker compose run --rm --no-deps caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
docker compose up -d --wait --wait-timeout 240
docker compose ps
echo 'Containers started. Complete Komari setup and change the Umami admin password immediately.'
echo 'Verify HTTPS and agent/tracking data manually; container startup is not a functional check.'
