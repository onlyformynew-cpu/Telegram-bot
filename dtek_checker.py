from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import requests

# 🔹 Надсилання тексту
def send_text_to_telegram(message, bot_token, chat_id):
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
    soup = BeautifulSoup(html, "html.parser")
    block = soup.select_one("#showCurOutage.active")
    if not block:
        return ""
    return block.get_text(separator="\n", strip=True)

# 🔹 Основна функція
def check_shutdown_status(city, street, house, bot_token, chat_id):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://www.dtek-dnem.com.ua/ua/shutdowns")

        # 🔹 Закриття модального вікна
        try:
            page.wait_for_selector(".modal__close", timeout=5000)
            page.click(".modal__close")
            print("✅ Модальне вікно закрито")
        except:
            print("ℹ️ Модального вікна не було або вже закрите")

        # 🔹 Вибір міста
        page.click("#city")
        page.fill("#city", city)
        page.wait_for_selector("#cityautocomplete-list > div", timeout=5000)
        page.click("#cityautocomplete-list > div")

        # 🔹 Вулиця
        page.wait_for_function("!document.querySelector('#street').disabled")
        page.click("#street")
        page.fill("#street", street)
        page.wait_for_selector("#streetautocomplete-list > div", timeout=5000)
        page.click("#streetautocomplete-list > div")

        # 🔹 Будинок
        page.wait_for_function("!document.querySelector('#house_num').disabled")
        page.click("#house_num")
        page.fill("#house_num", house)
        page.wait_for_selector("#house_numautocomplete-list > div", timeout=5000)
        page.click("#house_numautocomplete-list > div")

        # 🔹 Очікування оновлення графіка
        page.wait_for_selector("div#discon-fact.discon-fact.active", timeout=10000)
        page.wait_for_timeout(2000)
        html = page.content()

        # 🔹 Витяг тексту як є
        status_text = extract_raw_outage_text(html)
        if status_text:
            send_text_to_telegram(status_text, bot_token, chat_id)
        else:
            send_text_to_telegram("ℹ️ Статус електропостачання не знайдено", bot_token, chat_id)

        # 🔹 Скріншот графіка
        try:
            element = page.query_selector("div#discon-fact.discon-fact.active")
            if element:
                element.screenshot(path="schedule.png")
                send_image_to_telegram("schedule.png", bot_token, chat_id)
            else:
                print("⚠️ Графік не знайдено")
        except Exception as e:
            print("❌ Помилка при скріншоті:", e)

        browser.close()

# 🔹 Виклик
check_shutdown_status(
    city="м. Дніпро",
    street="ж/м Тополя-1",
    house="24",
    bot_token="8408105487:AAEqwvKEY5ayjVz_mJZ1wcHB7JjnfdkuauI",
    chat_id="365485892"
)
