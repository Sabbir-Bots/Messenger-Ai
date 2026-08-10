import requests
from config import PAGE_ACCESS_TOKEN, MESSENGER_MAX_CHARS
from logger import logger

GRAPH_API_URL = "https://graph.facebook.com/v18.0/me/messages"


def send_typing_indicator(recipient_id):
    """Gemini রেসপন্স জেনারেট করার সময় ইউজারকে 'টাইপিং...' দেখানো"""
    if not PAGE_ACCESS_TOKEN:
        return
    payload = {"recipient": {"id": recipient_id}, "sender_action": "typing_on"}
    try:
        requests.post(
            f"{GRAPH_API_URL}?access_token={PAGE_ACCESS_TOKEN}",
            json=payload,
            timeout=5
        )
    except Exception as e:
        logger.error(f"Typing indicator পাঠাতে সমস্যা হয়েছে: {e}")


def _split_message(text, max_chars=MESSENGER_MAX_CHARS):
    """মেসেঞ্জারের ক্যারেক্টার লিমিটের কারণে লম্বা টেক্সটকে কয়েকটা অংশে ভাগ করা"""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    while len(text) > max_chars:
        split_at = text.rfind('\n', 0, max_chars)
        if split_at == -1:
            split_at = text.rfind(' ', 0, max_chars)
        if split_at == -1:
            split_at = max_chars
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    if text:
        chunks.append(text)
    return chunks


def send_messenger_message(recipient_id, text):
    if not PAGE_ACCESS_TOKEN:
        logger.warning("PAGE_ACCESS_TOKEN is missing!")
        return

    for chunk in _split_message(text):
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": chunk}
        }
        try:
            requests.post(
                f"{GRAPH_API_URL}?access_token={PAGE_ACCESS_TOKEN}",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
        except Exception as e:
            logger.error(f"মেসেজ পাঠাতে সমস্যা হয়েছে: {e}")
