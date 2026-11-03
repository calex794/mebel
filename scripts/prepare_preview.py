"""Create a local-only Django preview secret without printing or committing it."""
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / ".env.preview"

if DEST.exists():
    print(".env.preview уже существует — настройки и секрет не изменены.")
else:
    lines = [
        "# Локальный просмотр через compose.preview.yaml. Не публиковать в Git.",
        "DJANGO_SECRET_KEY=" + secrets.token_urlsafe(60),
        "",
    ]
    fd = os.open(str(DEST), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))
    print("Создан .env.preview; секрет сохранён только на этом компьютере.")

print("Запуск: docker compose -f compose.preview.yaml up -d --build --wait")
