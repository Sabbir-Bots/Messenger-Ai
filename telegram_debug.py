import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_CHAT_ID
from logger import logger


def notify_admin(message):
    """
    গুরুত্বপূর্ণ ঘটনা (যেমন: সব Gemini key exhausted, Unhandled error) হলে
    টেলিগ্রামে অ্যাডমিনকে (সাব্বিরকে) নোটিফিকেশন পাঠানো হবে।
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_ADMIN_CHAT_ID:
        logger.info("Telegram debug system কনফিগার করা নেই, নোটিফিকেশন স্কিপ করা হলো।")
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_ADMIN_CHAT_ID, "text": f"🤖 ADITY Bot Alert:\n\n{message}"}
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        logger.error(f"Telegram এ নোটিফিকেশন পাঠাতে সমস্যা হয়েছে: {e}")
