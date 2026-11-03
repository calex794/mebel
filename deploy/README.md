# Автоматическое развёртывание — shabanovmebel.ru

Сайт: `https://shabanovmebel.ru`, VPS: `141.98.188.181`, Ubuntu 24.04, 1 vCPU / 1 ГБ RAM / 25 ГБ SSD.
Сборка образа выполняется **на GitHub**, а не на малом VPS. После успешного прогона трёх заданий CI на `main` GitHub по SSH передаёт образ и файлы запуска. Новая версия применяется после резервной копии, миграций и проверки HTTPS; при неудаче предпринимается откат приложения.

**Автоматический выпуск выключен**, пока не установлена переменная репозитория `PRODUCTION_DEPLOY_ENABLED=true`. Не включать при незавершённой политике обработки персональных данных или непроверенном размещении БД в нужной юрисдикции.

## 1. Однократная подготовка сервера

Зайдите в VPS через консоль хостера или SSH под существующим администратором. Установите пакеты Ubuntu (включите репозиторий `universe`, если пакета Compose нет):

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 curl git python3
sudo systemctl enable --now docker
docker compose version
sudo adduser --disabled-password --gecos '' mebeldeploy
sudo usermod -aG docker mebeldeploy
sudo install -d -m 700 -o mebeldeploy -g mebeldeploy /opt/mebel /opt/mebel/shared /opt/mebel/releases /opt/mebel/backups
```

Членство в группе `docker` практически равно административному доступу к серверу. Дайте его только отдельному пользователю `mebeldeploy` с ограниченным SSH-ключом. Парольный вход отключайте лишь после проверки входа по ключу.

Для 1 ГБ RAM рекомендуется выделить 2 ГБ подкачки, если её ещё нет:

```bash
swapon --show
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Не повторяйте создание `/swapfile`, если файл подкачки уже существует. Для исходящего трафика необходим доступ к контейнерным образам PostgreSQL, Redis и Caddy. Откройте TCP 80/443, SSH только с доверенных адресов; UDP 443 необязателен. Учитывайте, что опубликованные Docker-порты могут обходить обычные правила UFW: наружу в `compose.production.yaml` опубликованы лишь порты Caddy.

Создайте закрытый конфигурационный файл с **действующим адресом почты** для сертификата:

```bash
sudo -u mebeldeploy git clone --depth 1 https://github.com/calex794/mebel.git /opt/mebel/setup
sudo -u mebeldeploy python3 /opt/mebel/setup/scripts/prepare_production.py shabanovmebel.ru YOUR_EMAIL@example.ru
sudo -u mebeldeploy mv /opt/mebel/setup/.env.production /opt/mebel/shared/.env.production
sudo -u mebeldeploy chmod 600 /opt/mebel/shared/.env.production
sudo -u mebeldeploy rm -rf /opt/mebel/setup
```

Файл `.env.production` никогда не передаётся на GitHub и не перезаписывается обновлениями. Сначала проверьте, что A-запись домена `shabanovmebel.ru` указывает на `141.98.188.181`; для сертификата должны быть доступны TCP 80 и 443. Запись `www` отдельно не настроена.

## 2. SSH-доступ для GitHub Actions

Создайте отдельную пару ключей Ed25519 на своём доверенном компьютере, установите **публичную** часть в `/home/mebeldeploy/.ssh/authorized_keys` с разрешениями 700 для каталога и 600 для файла; владельцем должен быть `mebeldeploy`. Приватный ключ хранится только в секрете GitHub `DEPLOY_SSH_KEY` среды `production`.

Из **консоли провайдера** получите публичный ключ самого сервера `/etc/ssh/ssh_host_ed25519_key.pub` и его отпечаток через `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`. Составьте строку `141.98.188.181 ssh-ed25519 AAAA...` и сохраните её в секрете `DEPLOY_SSH_KNOWN_HOSTS` среды `production`. Для нестандартного порта используйте `[141.98.188.181]:PORT ssh-ed25519 AAAA...`. Ключ нельзя без проверки брать командой `ssh-keyscan` из рабочего процесса.

Настройте GitHub → Settings → Environments → `production` (желательно требовать подтверждение выпуска). Затем GitHub → Settings → Secrets and variables → Actions:

| Тип | Имя | Значение |
| --- | --- | --- |
| Переменная репозитория | `DEPLOY_HOST` | `141.98.188.181` |
| Переменная репозитория | `DEPLOY_USER` | `mebeldeploy` |
| Переменная репозитория | `DEPLOY_PORT` | `22` (если не меняли) |
| Секрет среды `production` | `DEPLOY_SSH_KEY` | приватный ключ Ed25519 |
| Секрет среды `production` | `DEPLOY_SSH_KNOWN_HOSTS` | проверенная запись ключа VPS |
| Переменная репозитория | `PRODUCTION_DEPLOY_ENABLED` | первоначально не задавать; `true` — после допуска к запуску |

Проверьте, что соединение `ssh -i PATH_TO_KEY mebeldeploy@141.98.188.181 'docker compose version'` работает, а каталог `/opt/mebel/releases` доступен на запись.

## 3. Выпуск, проверка и восстановление

Когда оформлены политика данных, действительные сведения оператора и подтверждено допустимое местонахождение хранения персональных данных, установите `PRODUCTION_DEPLOY_ENABLED=true`. В GitHub → Actions → «Проверка сайта» → Run workflow выберите `main`. Впоследствии каждый успешный `push` в `main` сам запускает выпуск. PR не могут развёртывать сайт.

Проверьте `https://shabanovmebel.ru/readyz/`, главную, административную панель `/upravlenie/`, отправку пробной заявки, загрузку фотографии и сохранение содержимого после нового выпуска. Администратора создайте вручную после первого успешного запуска:

```bash
cd /opt/mebel/current
COMPOSE_PROJECT_NAME=mebel MEBEL_WEB_IMAGE=mebel-web:$(basename "$(readlink -f /opt/mebel/current)") docker compose --env-file /opt/mebel/shared/.env.production -f compose.production.yaml exec web python manage.py createsuperuser
```

Тома `mebel_pg_data` и `mebel_media_data` сохраняются между выпусками; никаких `down -v` на VPS. Перед обновлением делается резервная копия БД и фотографий, затем проверяется её целостность. На 25 ГБ архивы быстро заполнят диск: наладьте ежедневное копирование в **зашифрованное внешнее хранилище**, контроль успешности и удаление локальных архивов только после подтверждённого внешнего копирования. Проверка архива не заменяет восстановление на отдельном сервере.

После неудачного обновления сценарий пытается вернуть предыдущий образ приложения и конфигурацию. **Миграции БД автоматически не отменяются**; изменять структуру следует с обратной совместимостью. Если откат не восстановил работу, проверьте журнал `docker compose -p mebel logs --tail 100 web caddy db` и восстанавливайте копию на отдельном сервере.

Перед публичным приёмом заявок нужно завершить `/privacy/`, определить оператора, сроки и место обработки персональных данных, продумать защиту административной панели и оповещения о сбоях. Наличие SSH-деплоя само по себе не означает готовность к публичному запуску.

---

## Новые требования к согласию и отзыву

### Consent gate
Before accepting personal data: create and publish a reviewed PrivacyPolicy revision in Django admin, with real operator identity/contact, legal basis, purposes, data categories, retention/deletion and withdrawal procedures. This change intentionally does not populate or legally approve any text. Without a published revision, both public forms are suppressed and POST /zayavka/ returns 503. Existing leads survive the migration and have an empty historic consent version. Test revision rotation and archive links and confirm retention/deletion procedures (including backups) before opening the site. No automatic deletion or withdrawal processing is implemented.

### Withdrawal workflow
After authenticating the person who requests withdrawal, an authorized admin can select the relevant lead and use "Подтвердить отзыв согласия". It records the time, moves the lead to "Согласие отозвано", and prevents reopening it as an ordinary lead in the admin and via the database status constraint. Repeating the action preserves the original timestamp. No public unverified revocation endpoint is exposed. This is not erasure: determine the lawful retention and response procedure, handle necessary deletion (also backups) and document the outcome separately. Do not treat an admin action as proof that all legal obligations were fulfilled.


## Очистка заявки после подтверждённого отзыва

В Django admin после проверки личности заявителя и регистрации отзыва оператор выбирает **одну** заявку, действие «Очистить личные данные отозванной заявки», подтверждает отсутствие иных оснований для хранения, принимает к сведению обработку архивов и вводит контрольную фразу. В основной базе очищаются имя, телефон, текст обращения и URL источника. Поля `erased_at`, `consent_withdrawn_at`, `consent_at`, `consent_version` и ссылка на версию политики остаются как ограниченная запись учёта без исходных контактов. DB-ограничение запрещает восстановление контактных данных в такой записи. Эта операция не предназначена для массовой очистки.

**Важно:** процесс не удаляет старые резервные копии, журналы, выгрузки или данные в сторонних системах. Оператор должен иметь закрытую внешнюю ведомость выполненных очисток (например, номер заявки и дату, без ФИО и телефона), устанавливать срок и порядок хранения архивов и проверять их после восстановления. Восстановление прежней копии базы может вернуть стёртые сведения: до подключения восстановленной базы к сайту повторно применить подтверждённые очистки из внешней ведомости и убедиться, что контактные поля пусты. Юридическую допустимость сохранения ограниченной служебной записи и срок её хранения определить отдельно.
