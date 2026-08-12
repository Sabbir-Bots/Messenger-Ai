import requests

import gemini_service
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_CHAT_ID
from logger import logger

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_telegram_message(chat_id, text):
    if not TELEGRAM_BOT_TOKEN:
        return
    try:
        requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=5
        )
    except Exception as e:
        logger.error(f"Telegram মেসেজ পাঠাতে সমস্যা হয়েছে: {e}")


def handle_update(update):
    """Telegram থেকে আসা webhook update প্রসেস করে"""
    message = update.get("message")
    if not message:
        return

    chat_id = message.get("chat", {}).get("id")
    text = (message.get("text") or "").strip()

    # নিরাপত্তা: শুধু অ্যাডমিনের (সাব্বিরের) চ্যাট থেকে আসা কমান্ডেই সাড়া দেওয়া হবে
    if str(chat_id) != str(TELEGRAM_ADMIN_CHAT_ID):
        logger.warning(f"অপরিচিত চ্যাট আইডি ({chat_id}) থেকে কমান্ড এসেছে, ignore করা হলো।")
        return

    if text == "/active_key":
        total_keys = len(gemini_service.gemini_clients)
        if total_keys == 0:
            send_telegram_message(chat_id, "⚠️ কোনো Gemini API key লোডই হয়নি।")
            return
        reply = (
            f"📦 মোট লোড হওয়া key: {total_keys}টা\n\n"
            "এখন প্রতিটা ইউজারকে তার আইডি অনুযায়ী একটা নির্দিষ্ট key বরাদ্দ করা হয় "
            "(লোড ব্যালান্স করার জন্য), তাই কোনো একটা 'গ্লোবাল অ্যাক্টিভ key' নেই। "
            "কোনো নির্দিষ্ট ইউজার কোন key ব্যবহার করছে তা Render লগে "
            "'✅ রেসপন্স তৈরি হয়েছে key #X' লাইন দেখে বোঝা যাবে।"
        )
        send_telegram_message(chat_id, reply)

    elif text == "/start":
        send_telegram_message(chat_id, "👋 ADITY Bot Admin Panel চালু আছে।\n\nউপলব্ধ কমান্ড:\n/active_key - বর্তমানে কোন Gemini key সক্রিয় আছে দেখাবে")

    else:
        send_telegram_message(chat_id, "❓ অজানা কমান্ড। /start লিখে কমান্ড লিস্ট দেখো।")
