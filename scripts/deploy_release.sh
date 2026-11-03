#!/usr/bin/env bash
# Server-side, idempotent deployment. Persistent volumes are never deleted.
set -Eeuo pipefail
umask 077
sha="${1:?Usage: deploy_release.sh GIT_SHA}"
[[ "$sha" =~ ^[a-f0-9]{40}$ ]] || { echo "Invalid SHA" >&2; exit 2; }
base=/opt/mebel
release="$base/releases/$sha"
env_file="$base/shared/.env.production"
current="$base/current"
image="mebel-web:$sha"

test -f "$env_file" || { echo "Missing $env_file" >&2; exit 2; }
test -f "$release/compose.production.yaml" || { echo "Missing release compose file" >&2; exit 2; }
test -f "$release/deploy/Caddyfile" || { echo "Missing Caddyfile" >&2; exit 2; }
docker image inspect "$image" >/dev/null

mkdir -p "$base/backups"
chmod 700 "$base/backups"
exec 9>"$base/deploy.lock"
flock -n 9 || { echo "Another deployment is running" >&2; exit 1; }

# Link private configuration without copying it into the release archive.
if [ -L "$release/.env.production" ]; then
  [[ "$(readlink -f "$release/.env.production")" == "$env_file" ]] || { echo "Unexpected env link" >&2; exit 2; }
elif [ -e "$release/.env.production" ]; then
  echo "Refusing existing non-link .env.production" >&2
  exit 2
else
  ln -s "$env_file" "$release/.env.production"
fi

prev=""
prev_sha=""
if [ -L "$current" ]; then
  prev="$(readlink -f "$current")"
  [[ "$prev" == "$base/releases/"* ]] || { echo "Invalid current release" >&2; exit 2; }
  prev_sha="${prev##*/}"
  [[ "$prev_sha" =~ ^[a-f0-9]{40}$ ]] || { echo "Invalid current SHA" >&2; exit 2; }
fi

if [[ "$prev" == "$release" ]]; then
  echo "Release already active: $sha"
  exit 0
fi

new_compose() {
  COMPOSE_PROJECT_NAME=mebel MEBEL_WEB_IMAGE="$image" \
    docker compose --env-file "$env_file" -f "$release/compose.production.yaml" "$@"
}
old_compose() {
  COMPOSE_PROJECT_NAME=mebel MEBEL_WEB_IMAGE="mebel-web:$prev_sha" \
    docker compose --env-file "$env_file" -f "$prev/compose.production.yaml" "$@"
}
new_compose config --quiet

available_mb="$(df -Pm "$base" | awk 'NR==2 {print $4}')"
if (( available_mb < 1800 )); then
  echo "Less than 1.8 GB free; remove verified off-host backups or unused images first" >&2
  exit 1
fi

# Never migrate without a fresh, integrity-checked backup of existing data.
if [[ -n "$prev" ]]; then
  echo "Backing up existing database and photos"
  (
    cd "$prev"
    COMPOSE_PROJECT_NAME=mebel MEBEL_WEB_IMAGE="mebel-web:$prev_sha" \
      sh scripts/backup_production.sh "$base/backups"
  )
  archive="$(ls -1t "$base"/backups/backup-*.tar.gz | head -n 1)"
  sh "$prev/scripts/check_backup.sh" "$archive"
fi

started=0
on_error() {
  rc="$1"
  trap - ERR
  if [[ "$started" == 1 ]]; then
    if [[ -n "$prev" ]]; then
      echo "Deployment failed; attempting application rollback to $prev_sha" >&2
      if ! old_compose up -d --no-build --wait web caddy; then
        echo "ALERT: automatic rollback also failed; inspect the server immediately" >&2
      fi
      echo "Database migrations are NOT reversed; old code may need a compatible schema." >&2
    else
      echo "First deployment failed. Stopping the unverified public services." >&2
      new_compose stop web caddy || true
    fi
  fi
  exit "$rc"
}
trap 'on_error $?' ERR

echo "Starting persistent services"
new_compose up -d --no-build --wait db cache
started=1
if [[ -n "$prev" ]]; then
  old_compose stop web
fi
echo "Applying schema migrations"
new_compose run --rm --no-deps -T web python manage.py migrate --noinput
echo "Starting the new application and HTTPS proxy"
new_compose up -d --no-build --wait web caddy

domain="$(sed -n 's/^SITE_DOMAIN=//p' "$env_file" | tail -n 1)"
[[ "$domain" =~ ^[a-z0-9][a-z0-9.-]+$ ]] || { echo "Invalid SITE_DOMAIN" >&2; false; }

echo "Checking HTTPS from the server"
healthy=0
for attempt in $(seq 1 24); do
  if curl -fsS --max-time 8 --resolve "$domain:443:127.0.0.1" \
       "https://$domain/readyz/" >/dev/null 2>&1; then
    healthy=1
    break
  fi
  sleep 5
done
[[ "$healthy" == 1 ]] || { echo "HTTPS healthcheck failed" >&2; false; }

next_link="$base/.current-next"
rm -f "$next_link"
ln -s "$release" "$next_link"
mv -Tf "$next_link" "$current"
trap - ERR
echo "Release active: $sha. Database and media volumes preserved."
