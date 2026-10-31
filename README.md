# Мониторинг жалоб на форуме Radmir Games

## Вариант 1: GitHub Actions (рекомендуется)

ПК не нужен — бот работает на GitHub-серверах по расписанию.

### 1. Создай репозиторий на GitHub

```powershell
cd C:\Users\ilnaz\forum_monitor
git init
git add .
git commit -m "init"
# Создай новый публичный репозиторий на github.com и push:
git remote add origin https://github.com/ТВОЙ_НИК/forum-monitor.git
git branch -M main
git push -u origin main
```

### 2. Настрой Secret'ы

В репозитории перейди: **Settings → Secrets and variables → Actions → New repository secret**

Добавь два секрета:

| Имя | Где взять |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Напиши `@BotFather` → `/newbot` → получи токен |
| `TELEGRAM_CHAT_ID` | Напиши `@userinfobot` → получи свой ID |

### 3. Расписание

В `.github/workflows/monitor.yml` строка `cron` задаёт расписание:

```yaml
- cron: '0 */2 * * *'   # каждые 2 часа
```

Другие варианты:
| Расписание | Значение |
|---|---|
| Каждый час | `0 * * * *` |
| Каждый день в 9:00 | `0 9 * * *` |
| Каждые 6 часов | `0 */6 * * *` |

### 4. Ручной запуск

Вкладка **Actions** → выбери **Forum Monitor** → **Run workflow**

---

## Вариант 2: Локально (твой ПК)

### 1. Установка зависимостей
```powershell
cd C:\Users\ilnaz\forum_monitor
pip install -r requirements.txt
```

### 2. Вставь токен и ID в `config.py`
```python
TELEGRAM_BOT_TOKEN = "ВАШ_ТОКЕН"
TELEGRAM_CHAT_ID = "ВАШ_CHAT_ID"
```

### 3. Запуск
```powershell
python monitor.py
```

---

## ⚠️ Важно: Подстройка селекторов форума

После первого запуска проверь файл `forum_page.html` — в нём сохраняется
разметка страницы форума. Открой его и найди, как выглядят темы:

1. Правой кнопкой на HTML → "Посмотреть код"
2. Найди селекторы для заголовка темы и даты
3. Обновь `THREAD_SELECTORS` и `DATE_SELECTORS` в `monitor.py`

Пример:
```python
# Если на форуме темы выглядят так:
# <div class="my-custom-thread">
#     <a href="/threads/123/">Жалоба на игрока</a>
#     <time data-time="1700000000">15 окт 2025</time>
# </div>

# То селекторы:
THREAD_SELECTORS = ["div.my-custom-thread"]
DATE_SELECTORS = ["time[data-time]"]
```

### Планировщик Windows (опционально)

Чтобы запустить мониторинг автоматически при старте Windows:

1. Открой "Планировщик задач"
2. Создать задачу → триггер "При входе в систему"
3. Действие: `python C:\Users\ilnaz\forum_monitor\monitor.py`

### Параметры в config.py

| Параметр | Описание |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен от @BotFather |
| `TELEGRAM_CHAT_ID` | Твой Telegram Chat ID |
| `THRESHOLD_HOURS` | Порог в часах (по умолчанию 20) |
| `CHECK_INTERVAL_SECONDS` | Интервал проверки (по умолчанию 3600 = 1 час) |

## Лог-файл

Лог всех проверок сохраняется в `monitor.log`.
