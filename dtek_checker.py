from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import requests
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# 🔹 Список адрес для моніторингу
addresses = []
last_statuses = {}  # зберігає останній статус для кожної адреси

# 🔹 Надсилання тексту
def send_text_to_telegram(message, bot_token, chat_id):
    print(f"➡️ Надсилаю текст у Telegram: {message[:50]}...")
    if not message.strip():
        print("⚠️ Немає тексту для надсилання")
        return
    if len(message) > 4000:
        print("⚠️ Повідомлення занадто довге, обрізаю")
        message = message[:4000]
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}
    response = requests.post(url, data=data)
    print("📩 Відповідь Telegram:", response.status_code, response.text)

# 🔹 Надсилання зображення
def send_image_to_telegram(image_path, bot_token, chat_id):
    print(f"➡️ Надсилаю зображення {image_path} у Telegram...")
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    try:
        with open(image_path, "rb") as image:
            files = {"photo": image}
            data = {"chat_id": chat_id}
            response = requests.post(url, files=files, data=data)
            print("🖼️ Відповідь Telegram:", response.status_code, response.text)
    except FileNotFoundError:
        print("⚠️ Зображення не знайдено для надсилання")

# 🔹 Витяг тексту як є
def extract_raw_outage_text(html):
    print("➡️ Витягую текст зі сторінки...")
    soup = BeautifulSoup(html, "html.parser")
    block = soup.select_one("#showCurOutage.active")
    if not block:
        print("⚠️ Блок зі статусом не знайдено")
        return ""
    return block.get_text(separator="\n", strip=True)

# 🔹 Основна функція
def check_shutdown_status(city, street, house, bot_token, chat_id):
    print(f"➡️ Перевіряю адресу: {city}, {street}, {house}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("➡️ Відкриваю сайт DTEK...")
        page.goto("https://www.dtek-dnem.com.ua/ua/shutdowns", timeout=15000)
        print("✅ Сайт відкрито")

        try:
            page.wait_for_selector(".modal__close", timeout=5000)
            page.click(".modal__close")
            print("✅ Модальне вікно закрито")
        except:
            print("ℹ️ Модального вікна не було")

        # Місто
        page.click("#city")
        page.fill("#city", city)
        page.wait_for_selector("#cityautocomplete-list > div", timeout=5000)
        page.click("#cityautocomplete-list > div")
        print("✅ Місто вибрано")

        # Вулиця
        page.wait_for_function("!document.querySelector('#street').disabled")
        page.click("#street")
        page.fill("#street", street)
        page.wait_for_selector("#streetautocomplete-list > div", timeout=5000)
        page.click("#streetautocomplete-list > div")
        print("✅ Вулиця вибрана")

        # Будинок
        page.wait_for_function("!document.querySelector('#house_num').disabled")
        page.click("#house_num")
        page.fill("#house_num", house)
        page.wait_for_selector("#house_numautocomplete-list > div", timeout=5000)
        page.click("#house_numautocomplete-list > div")
        print("✅ Будинок вибрано")

        # Очікування графіка
        page.wait_for_selector("div#discon-fact.discon-fact.active", timeout=10000)
        page.wait_for_timeout(2000)
        html = page.content()
        print("✅ Сторінка завантажена")

        status_text = extract_raw_outage_text(html)
        if status_text:
            send_text_to_telegram(status_text, bot_token, chat_id)
        else:
            send_text_to_telegram("ℹ️ Статус електропостачання не знайдено", bot_token, chat_id)

        try:
            element = page.query_selector("div#discon-fact.discon-fact.active")
            if element:
                element.screenshot(path="schedule.png")
                send_image_to_telegram("schedule.png", bot_token, chat_id)
                print("✅ Скріншот зроблено і відправлено")
            else:
                print("⚠️ Графік не знайдено")
        except Exception as e:
            print("❌ Помилка при скріншоті:", e)

        browser.close()
        print("✅ Браузер закрито")

    return status_text

# 🔹 Команди бота
async def add_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text("Використання: /addaddress <місто> <вулиця> <будинок>")
        return
    city, street, house = context.args[0], context.args[1], " ".join(context.args[2:])
    addresses.append((city, street, house))
    await update.message.reply_text(f"✅ Адресу додано: {city}, {street}, {house}")

async def list_addresses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not addresses:
        await update.message.reply_text("ℹ️ Список адрес порожній")
        return
    text = "\n".join([f"{i+1}. {a[0]}, {a[1]}, {a[2]}" for i, a in enumerate(addresses)])
    await update.message.reply_text("📋 Адреси:\n" + text)

async def delete_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Використання: /deleteaddress <номер>")
        return
    try:
        idx = int(context.args[0]) - 1
        removed = addresses.pop(idx)
        await update.message.reply_text(f"🗑️ Видалено: {removed[0]}, {removed[1]}, {removed[2]}")
    except:
        await update.message.reply_text("⚠️ Невірний номер")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_token = os.environ.get("BOT_TOKEN")
    chat_id = update.message.chat_id
    if not context.args:
        await update.message.reply_text("Використання: /status <номер|all>")
        return
    arg = context.args[0]
    if arg == "all":
        for city, street, house in addresses:
            check_shutdown_status(city, street, house, bot_token, chat_id)
    else:
        try:
            idx = int(arg) - 1
            city, street, house = addresses[idx]
            check_shutdown_status(city, street, house, bot_token, chat_id)
        except:
            await update.message.reply_text("⚠️ Невірний номер")

async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Використання: /track <номер>")
        return
    try:
        idx = int(context.args[0]) - 1
        city, street, house = addresses[idx]
        chat_id = update.message.chat_id
        bot_token = os.environ.get("BOT_TOKEN")

        async def job_callback(ctx: ContextTypes.DEFAULT_TYPE):
            print(f"➡️ Трекінг адреси {city}, {street}, {house}")
            new_status = check_shutdown_status(city, street, house, bot_token, chat_id)
            key = f"{city}|{street}|{house}"
            old_status = last_statuses.get(key)
            if new_status != old_status:
                print("✅ Зміна статусу, надсилаю повідомлення")
                last_statuses[key] = new_status
                if new_status:
                    send_text_to_telegram(new_status, bot_token, chat_id)
            else:
                print("ℹ️ Статус не змінився, повідомлення не надсилаю")

        context.job_queue.run_repeating(job_callback, interval=900, first=0, chat_id=chat_id)
        await update.message.reply_text(f"⏱️ Запущено трекінг для адреси {city}, {street}, {house}")
    except:
        await update.message.reply_text("⚠️ Невірний номер")

# 🔹 Запуск бота
if __name__ == "__main__":
    BOT_TOKEN = os.environ.get("BOT_TOKEN")

    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не задано у змінних середовища Render")
        exit(1)

    app = Application.builder().token(BOT_TOKEN).build()

    # Реєстрація команд
    app.add_handler(CommandHandler("addaddress", add_address))
    app.add_handler(CommandHandler("listaddresses", list_addresses))
    app.add_handler(CommandHandler("deleteaddress", delete_address))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("track", track))

    print("🤖 Бот запущено. Очікую команди...")
    app.run_polling()
