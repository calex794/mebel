#!/bin/sh
set -eu
if [ "$#" -ne 1 ]; then echo "Usage: $0 backup.tar.gz" >&2; exit 2; fi
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
tar -xzf "$1" -C "$tmp"
( cd "$tmp" && sha256sum -c SHA256SUMS )
test -s "$tmp/database.dump"
test -s "$tmp/media.tar"
tar -tf "$tmp/media.tar" >/dev/null
echo "Archive hashes and media tar OK; restore rehearsal still required."
