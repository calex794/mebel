# Production runbook — operator action required

The deployment configuration has not been deployed. Use a host appropriate for Russian personal-data localisation requirements after legal review. Configure public DNS, Docker Compose, inbound TCP 80/443 and the operator identity, retention and privacy notice before using real leads.

1. Run python scripts/prepare_production.py furniture.example.org admin@example.org, using your real domain and email. NEVER commit .env.production or share its contents.
2. Run docker compose --env-file .env.production -f compose.production.yaml up -d --build.
3. Run docker compose --env-file .env.production -f compose.production.yaml exec web python manage.py migrate --noinput.
4. Run docker compose --env-file .env.production -f compose.production.yaml exec web python manage.py createsuperuser (interactive only).
5. Verify HTTPS and login at https://YOUR_DOMAIN/upravlenie/. Test a sample lead, photo upload and persistence.
6. Keep only Caddy ports 80/443 public; DB, Redis and Gunicorn are private. Restrict admin access by VPN or network controls. Monitor login failures.
7. Verify the backup and restore procedure on a SEPARATE isolated test host before accepting leads.

Caddy manages HTTPS certificates. PostgreSQL and uploaded photos use named persistent volumes. Stopping the stack with docker compose down retains volumes; do NOT use down -v with real data.

Backup: bash scripts/backup_production.sh /secure/backup/directory saves a consistent PostgreSQL logical export plus an archive of media files. The output must be copied to encrypted external storage, with monitored backup failures and rotation. The script DOES NOT send it off-host. Protect backup directory permissions.

Restore: stop all writes; create an empty PostgreSQL instance and media volume in an isolated environment; restore the SQL dump using pg_restore --no-owner --no-privileges --clean --if-exists; copy media directory into media_data and verify photo URLs; verify migrations, lead counts, owners and access; only then switch over. Never restore to a live site with ongoing writes.

Before public launch: replace the placeholder privacy page with full operator details and legal review; set retention and deletion process, configure monitoring, confirm image use rights, harden SSH/host firewall, test recovery, and ensure production secrets are stored off-host.
