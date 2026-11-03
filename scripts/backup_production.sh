#!/bin/sh
# Stop writes briefly, then capture a consistent DB and media snapshot.
set -eu
umask 077
if [ "$#" -ne 1 ] || [ ! -d "$1" ] || [ -L "$1" ]; then echo "Usage: $0 /existing/private/backup-dir" >&2; exit 2; fi
test -f .env.production || { echo "Missing .env.production" >&2; exit 2; }
dest="$1"
compose() { docker compose --env-file .env.production -f compose.production.yaml "$@"; }
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
tmp="$(mktemp -d "$dest/.pending-$stamp-XXXXXX")"
stopped=0
cleanup() {
  if [ "$stopped" = 1 ]; then compose start web >/dev/null 2>&1 || echo "WARNING: failed to restart web" >&2; fi
  [ ! -d "$tmp" ] || rm -rf "$tmp"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
compose stop web >/dev/null
stopped=1
compose exec -T db pg_dump -U mebel -d mebel --format=custom > "$tmp/database.dump"
test -s "$tmp/database.dump"
compose run --rm -T --no-deps --entrypoint tar web -C /data -cf - media > "$tmp/media.tar"
test -s "$tmp/media.tar"
printf '%s\n' "$stamp" > "$tmp/created_utc.txt"
( cd "$tmp" && sha256sum database.dump media.tar > SHA256SUMS )
archive="$dest/backup-$stamp.tar.gz"
[ ! -e "$archive" ] || { echo "Backup archive already exists" >&2; exit 1; }
tar -czf "$tmp/archive.tar.gz" -C "$tmp" database.dump media.tar created_utc.txt SHA256SUMS
mv "$tmp/archive.tar.gz" "$archive"
compose start web >/dev/null
stopped=0
echo "Backup created: $archive"
echo "Copy to encrypted off-host storage and test restore."
