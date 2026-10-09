#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
command -v openssl >/dev/null || { echo 'Install openssl first.' >&2; exit 1; }
if [[ -e .env ]]; then
  echo '.env exists; preserved without changing any secrets.'
  exit 0
fi
umask 077
tmp=$(mktemp .env.tmp.XXXXXX)
trap 'rm -f "$tmp"' EXIT
while IFS= read -r line || [[ -n "$line" ]]; do
  case "$line" in
    POSTGRES_PASSWORD=*) line="POSTGRES_PASSWORD=$(openssl rand -hex 32)" ;;
    APP_SECRET=*) line="APP_SECRET=$(openssl rand -hex 32)" ;;
    TWO_FACTOR_ENCRYPTION_KEY=*) line="TWO_FACTOR_ENCRYPTION_KEY=$(openssl rand -hex 32)" ;;
  esac
  printf '%s\n' "$line" >> "$tmp"
done < .env.example
# noclobber also protects against concurrent init executions.
(set -C; cat "$tmp" > .env)
echo 'Generated .env (0600). Edit the email and both domains before deploying.'
