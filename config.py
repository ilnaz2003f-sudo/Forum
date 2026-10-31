# Конфигурация для мониторинга жалоб на форуме Radmir

# Telegram Bot API
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Форум
FORUM_URL = "https://forum.radmir.games/forums/zhaloby-na-igrokov-sost-v-kriminal-nykh-strukturakh.972/"
FORUM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Порог времени (в часах)
THRESHOLD_HOURS = 20

# Интервал проверки в секундах (по умолчанию 1 час)
CHECK_INTERVAL_SECONDS = 3600
