#!/usr/bin/env bash
# Called only after all checks passed on the protected main branch.
set -Eeuo pipefail
umask 077

: "${DEPLOY_HOST:?Set DEPLOY_HOST repository variable}"
: "${DEPLOY_USER:?Set DEPLOY_USER repository variable}"
: "${DEPLOY_SSH_KEY:?Set DEPLOY_SSH_KEY production secret}"
: "${DEPLOY_SSH_KNOWN_HOSTS:?Set DEPLOY_SSH_KNOWN_HOSTS production secret}"
: "${RELEASE_SHA:?Set RELEASE_SHA}"

[[ "$DEPLOY_HOST" =~ ^[a-zA-Z0-9.-]+$ ]] || { echo "Invalid host" >&2; exit 2; }
[[ "$DEPLOY_USER" =~ ^[a-z_][a-z0-9_-]*$ ]] || { echo "Invalid username" >&2; exit 2; }
[[ "$DEPLOY_PORT" =~ ^[0-9]+$ ]] && (( DEPLOY_PORT >= 1 && DEPLOY_PORT <= 65535 )) || { echo "Invalid port" >&2; exit 2; }
[[ "$RELEASE_SHA" =~ ^[a-f0-9]{40}$ ]] || { echo "Invalid commit SHA" >&2; exit 2; }

temp="$(mktemp -d)"
trap 'rm -rf "$temp"' EXIT
printf '%s\n' "$DEPLOY_SSH_KEY" | tr -d '\r' > "$temp/key"
printf '%s\n' "$DEPLOY_SSH_KNOWN_HOSTS" > "$temp/known_hosts"
chmod 600 "$temp/key" "$temp/known_hosts"
known_host="$DEPLOY_HOST"
if [[ "$DEPLOY_PORT" != 22 ]]; then known_host="[$DEPLOY_HOST]:$DEPLOY_PORT"; fi
ssh-keygen -F "$known_host" -f "$temp/known_hosts" >/dev/null || {
  echo "Pinned SSH host key for $known_host missing. Do not use ssh-keyscan in CI." >&2
  exit 2
}

ssh_args=(-i "$temp/key" -p "$DEPLOY_PORT" -o IdentitiesOnly=yes
          -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$temp/known_hosts"
          -o BatchMode=yes -o ConnectTimeout=15)
remote() { ssh "${ssh_args[@]}" "$DEPLOY_USER@$DEPLOY_HOST" "$@"; }

echo "Staging release $RELEASE_SHA"
remote "mkdir -p /opt/mebel/releases/$RELEASE_SHA"
tar -cf - compose.production.yaml deploy/Caddyfile scripts/deploy_release.sh \
    scripts/backup_production.sh scripts/check_backup.sh |
  remote "tar -xf - -C /opt/mebel/releases/$RELEASE_SHA"

echo "Building production image on the GitHub runner"
docker build --pull -f Dockerfile.production -t "mebel-web:$RELEASE_SHA" .

echo "Sending image to the server over authenticated SSH"
docker save "mebel-web:$RELEASE_SHA" | gzip -1 |
  remote "gzip -d | docker image load"

echo "Deploying release with pre-update backup and health checks"
remote "bash /opt/mebel/releases/$RELEASE_SHA/scripts/deploy_release.sh $RELEASE_SHA"
echo "Deployment completed: $RELEASE_SHA"
