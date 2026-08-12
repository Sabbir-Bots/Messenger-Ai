from flask import Flask, request
import threading

from config import VERIFY_TOKEN, PORT
from logger import logger
from security import verify_signature
from rate_limiter import is_rate_limited
from dedupe import is_duplicate_message
from firebase_service import save_analytics
from gemini_service import get_gemini_response
from messenger_service import send_messenger_message, send_typing_indicator
from telegram_debug import notify_admin
import tg_service

app = Flask(__name__)


def process_user_message(sender_id, user_message):
    """
    একজন ইউজারের মেসেজ প্রসেস করে রিপ্লাই পাঠানো - এটা ব্যাকগ্রাউন্ড থ্রেডে চলে,
    যাতে Facebook কে সাথে সাথেই 200 OK রেসপন্স দেওয়া যায় (নাহলে দেরি হলে Facebook
    একই মেসেজ বারবার retry পাঠায়, ফলে একটা মেসেজের একাধিক রিপ্লাই চলে যায়)।
    """
    try:
        save_analytics(sender_id, user_message)
        send_typing_indicator(sender_id)

        try:
            bot_reply, used_ai = get_gemini_response(sender_id, user_message)
        except Exception as e:
            logger.error(f"Unhandled error in message processing: {e}")
            notify_admin(f"🚨 Unhandled error in bot:\n{e}")
            bot_reply = "কিছু একটা সমস্যা হয়েছে, একটু পরে আবার চেষ্টা করো।"

        send_messenger_message(sender_id, bot_reply)
    except Exception as e:
        logger.error(f"process_user_message এ এরর: {e}")


@app.route("/", methods=['GET'])
def verify():
    """Facebook webhook verification (Meta App সেটআপের সময় একবার কল হয়)"""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403


@app.route("/health", methods=['GET'])
def health():
    """বট জীবিত আছে কিনা চেক করার জন্য সাধারণ health-check রুট"""
    return {"status": "ok"}, 200


@app.route("/telegram-webhook", methods=['POST'])
def telegram_webhook():
    """Telegram Bot এর জন্য webhook - অ্যাডমিন কমান্ড হ্যান্ডেল করে (যেমন /active_key)"""
    try:
        update = request.get_json()
        tg_service.handle_update(update)
    except Exception as e:
        logger.error(f"Telegram webhook এ এরর: {e}")
    return "OK", 200


@app.route("/", methods=['POST'])
def webhook():
    # --- নিরাপত্তা: শুধু আসল Facebook থেকে আসা রিকোয়েস্টই গ্রহণ করা হবে ---
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_signature(request.get_data(), signature):
        logger.warning("অবৈধ webhook signature — রিকোয়েস্ট বাতিল করা হলো।")
        return "Invalid signature", 403

    data = request.get_json()

    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event.get("sender", {}).get("id")

                if messaging_event.get("message") and messaging_event["message"].get("text"):
                    user_message = messaging_event["message"]["text"]
                    message_id = messaging_event["message"].get("mid")

                    # --- ডুপ্লিকেট মেসেজ চেক (Facebook retry এর কারণে একই মেসেজ একাধিকবার আসতে পারে) ---
                    if is_duplicate_message(message_id):
                        continue

                    # --- স্প্যাম প্রোটেকশন ---
                    if is_rate_limited(sender_id):
                        logger.info(f"ইউজার {sender_id} rate-limited, মেসেজ ignore করা হলো।")
                        continue

                    # --- আসল কাজ ব্যাকগ্রাউন্ডে করা হবে, Facebook কে সাথে সাথেই রেসপন্স দেওয়া হবে ---
                    threading.Thread(
                        target=process_user_message,
                        args=(sender_id, user_message),
                        daemon=True
                    ).start()

    return "EVENT_RECEIVED", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
