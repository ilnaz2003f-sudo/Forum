import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import logging
from config import (
    FORUM_URL,
    FORUM_HEADERS,
    THRESHOLD_HOURS,
    CHECK_INTERVAL_SECONDS,
)

# Переменные окружения (GitHub Actions / локально)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("monitor.log", encoding="utf-8"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ---------- Telegram ----------

def send_telegram_message(message: str, parse_mode: str = "HTML") -> bool:
    """Отправляет сообщение в Telegram через бота."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": parse_mode,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("Сообщение в Telegram отправлено.")
            return True
        else:
            logger.error(f"Ошибка Telegram API: {resp.status_code} — {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение в Telegram: {e}")
        return False


# ---------- Парсинг форума ----------

def fetch_page(page_num: int = 0) -> str | None:
    """Загружает страницу форума (с поддержкой пагинации)."""
    params = {"page": page_num} if page_num > 0 else {}
    try:
        resp = requests.get(FORUM_URL, headers=FORUM_HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.error(f"Ошибка загрузки страницы (page={page_num}): {e}")
        return None


# Шаблоны для XenForo-форумов — нужно подстроить под реальную разметку
THREAD_SELECTORS = [
    "li.discuss-item",            # стандартный блок темы XenForo
    "data-xf-key='thread.title'", # атрибут XenForo 2.x
    "li.structItem--discussion",  # новый формат XenForo 2.3+
    "article.thread",
    "div.structItem",
]

DATE_SELECTORS = [
    "time.js-lastPost",
    "time[data-time]",
    "span.symbolLatestNewest",
    "data-last-date",
    "time.timestamp",
    "span.structItem-meta",
    "div.structItem-meta time",
]


def parse_threads(html: str) -> list[dict]:
    """
    Извлекает список тем с датами и ссылками.
    Нужно будет подстроить селекторы под реальную разметку форума.
    """
    soup = BeautifulSoup(html, "html.parser")
    threads = []

    # Пробуем разные селекторы
    thread_el = None
    for selector in THREAD_SELECTORS:
        thread_el = soup.select_one(selector)
        if thread_el:
            logger.info(f"Найдена тема через селектор: {selector}")
            break

    if not thread_el:
        logger.warning("Не удалось найти элементы тем на странице.")
        return threads

    # Определяем родительские контейнеры тем
    items = soup.select(", ".join(THREAD_SELECTORS))
    if not items:
        return threads

    for item in items:
        try:
            # Ссылка на тему
            link_el = item.select_one("a.link, a.structItem-link, a.title")
            title_el = item.select_one("a.link, a.structItem-link, a.title")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            if not href.startswith("http"):
                href = "https://forum.radmir.games" + href

            # Дата — ищем внутри элемента темы
            date_str = None
            for ds in DATE_SELECTORS:
                time_el = item.select_one(ds)
                if time_el:
                    # XenForo хранит время в data-time (Unix timestamp)
                    ts = time_el.get("data-time")
                    if ts:
                        date_str = datetime.fromtimestamp(int(ts))
                    else:
                        date_str = datetime.fromisoformat(
                            time_el.get_text(strip=True).replace(",", "")
                        )
                    break

            # Если не нашли через data-time — парсим текст
            if date_str is None:
                # Пытаемся найти любые временные метки
                times = item.select("time")
                if times:
                    # Обычно последний time — это дата последнего сообщения
                    last_time = times[-1]
                    date_str = _parse_time_text(last_time.get_text(strip=True))

            threads.append({
                "title": title,
                "url": href,
                "date": date_str,
            })
        except Exception as e:
            logger.warning(f"Не удалось распарсить тему: {e}")
            continue

    return threads


def _parse_time_text(text: str) -> datetime | None:
    """Пытается распарсить дату из текста (разные форматы)."""
    formats = [
        "%d %b %Y в %H:%M",       # 15 окт 2025 в 14:30
        "%d.%m.%Y %H:%M",         # 15.10.2025 14:30
        "%d.%m.%Y",               # 15.10.2025
        "%b %d, %Y at %H:%M",     # Oct 15, 2025 at 14:30
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def paginate_count() -> int:
    """Определяет количество страниц на форуме."""
    # Пробуем загрузить 2 страницу — если 404, значит страниц нет
    html = fetch_page(1)
    if html is None:
        return 0
    soup = BeautifulSoup(html, "html.parser")
    nav = soup.select_one("div.pagenav")
    if nav:
        pages = nav.select("a.pagenav-page")
        if pages:
            # Берём последнюю страницу
            try:
                return int(pages[-1].get_text(strip=True))
            except (ValueError, IndexError):
                pass
        # Пробуем data-page-range
        last = nav.select_one("a.pagenav-page[data-page-range='last']")
        if last:
            try:
                return int(last.get("data-page-value", "1"))
            except (ValueError, AttributeError):
                pass
    return 1


# ---------- Основной цикл ----------

def check_forum():
    """Основной цикл мониторинга."""
    logger.info("=" * 50)
    logger.info("Старт мониторинга жалоб на форуме Radmir")
    logger.info(f"Порог: {THRESHOLD_HOURS} часов")
    logger.info("=" * 50)

        try:
            total_pages = paginate_count()
            logger.info(f"Найдено страниц: {total_pages}")

            all_threads = []
            for page in range(total_pages):
                html = fetch_page(page)
                if html:
                    threads = parse_threads(html)
                    all_threads.extend(threads)
                    logger.info(f"Страница {page + 1}: найдено {len(threads)} тем")

            if not all_threads:
                logger.warning("Темы не найдены. Возможно, нужно настроить селекторы.")
                # Сохраним HTML для отладки
                html = fetch_page()
                if html:
                    with open("forum_page.html", "w", encoding="utf-8") as f:
                        f.write(html)
                    logger.info("Сохранена разметка страницы: forum_page.html")

            now = datetime.now()
            threshold = now - timedelta(hours=THRESHOLD_HOURS)

            old_threads = []
            for t in all_threads:
                if t["date"] and t["date"] < threshold:
                    old_threads.append(t)

            if old_threads:
                msg = (
                    f"⚠️ <b>Жалоба висит более {THRESHOLD_HOURS} часов!</b>\n\n"
                    f"Найдено {len(old_threads)} жалоб(а):\n"
                )
                for t in old_threads:
                    msg += f"• <b>{t['title']}</b>\n"
                    msg += f"  📅 {t['date'].strftime('%d.%m.%Y %H:%M')}\n"
                    msg += f"  🔗 <a href='{t['url']}'>открыть</a>\n\n"
                send_telegram_message(msg)
            else:
                logger.info("Актуальных жалоб старше 20 часов не найдено.")

        except Exception as e:
            logger.error(f"Ошибка в цикле мониторинга: {e}", exc_info=True)

        logger.info(f"Следующая проверка через {CHECK_INTERVAL_SECONDS // 60} мин...")


if __name__ == "__main__":
    run_once()
