import os
import requests
import asyncio
from telegram import Bot
from telegram.ext import Application, CommandHandler

# ---- Зчитування токена та chat_id зі змінних середовища ----
TOKEN = os.environ["TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# ---- Налаштування ----
CHECK_INTERVAL = 60  # інтервал перевірки в секундах
SEARCH_QUERIES = {}  # словник {запит: id_останнього_товару}

bot = Bot(token=TOKEN)


# ---- Функція пошуку на Vinted ----
def search_vinted(query: str):
    """Виконує пошук на Vinted API"""
    url = "https://www.vinted.it/api/v2/catalog/items"
    params = {"search_text": query, "per_page": 1, "order": "newest_first"}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])
    except Exception as e:
        print(f"[ERROR] search_vinted: {e}")
        return []


# ---- Telegram команди ----
async def add_query(update, context):
    """Додає новий пошуковий запит"""
    if not context.args:
        await update.message.reply_text("❌ Використання: /add <запит>")
        return
    query = " ".join(context.args)
    SEARCH_QUERIES[query] = None
    await update.message.reply_text(f"✅ Додано пошук: {query}")


async def list_queries(update, context):
    """Виводить список активних пошуків"""
    if not SEARCH_QUERIES:
        await update.message.reply_text("ℹ️ Список порожній.")
        return
    queries = "\n".join(SEARCH_QUERIES.keys())
    await update.message.reply_text(f"🔍 Активні пошуки:\n{queries}")


async def remove_query(update, context):
    """Видаляє пошуковий запит"""
    if not context.args:
        await update.message.reply_text("❌ Використання: /remove <запит>")
        return
    query = " ".join(context.args)
    if query in SEARCH_QUERIES:
        del SEARCH_QUERIES[query]
        await update.message.reply_text(f"🗑 Видалено пошук: {query}")
    else:
        await update.message.reply_text("❌ Такого пошуку нема.")


# ---- Основний цикл перевірки ----
async def check_new_items():
    """Фоновий цикл перевірки нових товарів"""
    while True:
        for query in list(SEARCH_QUERIES.keys()):
            items = search_vinted(query)
            if items:
                latest_item = items[0]
                last_id = SEARCH_QUERIES[query]
                if last_id != latest_item["id"]:
                    SEARCH_QUERIES[query] = latest_item["id"]

                    msg = (
                        f"🆕 {latest_item['title']}\n"
                        f"💰 {latest_item['price']}€\n"
                        f"🔗 https://www.vinted.it{latest_item['path']}"
                    )
                    try:
                        await bot.send_message(chat_id=CHAT_ID, text=msg)
                    except Exception as e:
                        print(f"[ERROR] send_message: {e}")

        await asyncio.sleep(CHECK_INTERVAL)


# ---- Запуск бота ----
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("add", add_query))
    app.add_handler(CommandHandler("list", list_queries))
    app.add_handler(CommandHandler("remove", remove_query))

    loop = asyncio.get_event_loop()
    loop.create_task(check_new_items())

    print("✅ Бот запущений...")
    app.run_polling()


if __name__ == "__main__":
    main()
