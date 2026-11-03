"""Check a running local preview without creating any client data."""
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
PAGES = {
    "/": "Корпусная мебель",
    "/mebel/": "Мебель",
    "/raboty/": "Наши работы",
    "/stati/": "Статьи",
    "/kontakty/": "Контакты",
    "/privacy/": "Обработка персональных данных",
    "/upravlenie/login/": "name=\"username\"",
    "/sitemap.xml": "<urlset",
    "/robots.txt": "User-agent:",
}

for attempt in range(24):
    try:
        with urllib.request.urlopen(BASE + "/", timeout=3):
            break
    except (urllib.error.URLError, TimeoutError):
        if attempt == 23:
            sys.exit("Сайт не отвечает на 127.0.0.1:8000.")
        time.sleep(2)

for path, expected in PAGES.items():
    try:
        with urllib.request.urlopen(BASE + path, timeout=8) as response:
            body = response.read().decode("utf-8")
            if response.status != 200 or expected not in body:
                sys.exit(f"Ошибка проверки страницы {path}: status={response.status}")
    except urllib.error.URLError as exc:
        sys.exit(f"Страница {path} недоступна: {exc}")

print("Локальная проверка: главная, услуги, работы, статьи, контакты, вход в панель, карта сайта — OK.")
