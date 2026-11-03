#!/usr/bin/env python3
"""Generate an offline administrator login key and its server-side SHA-256 digest.

Run on a trusted terminal; store the raw key in a password manager. Only the
digest belongs in /opt/mebel/shared/.env.production. Never commit either one.
"""
import hashlib
import secrets


def main():
    key = "mk_" + secrets.token_urlsafe(32)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    print("Личный ключ администратора (показан один раз):")
    print(key)
    print()
    print("Добавить в закрытый файл .env.production:")
    print("MEBEL_ADMIN_KEY_SHA256=" + digest)
    print("MEBEL_ADMIN_KEY_USER=admin")
    print()
    print("Храните ключ отдельно от сервера, не отправляйте его в GitHub или чат.")


if __name__ == "__main__":
    main()
