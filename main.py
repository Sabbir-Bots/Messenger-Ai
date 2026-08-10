from flask import Flask, request

from config import VERIFY_TOKEN, PORT
from logger import logger
from security import verify_signature
from rate_limiter import is_rate_limited
from firebase_service import save_analytics
from gemini_service import get_gemini_response
from messenger_service import send_messenger_message, send_typing_indicator
from telegram_debug import notify_admin

app = Flask(__name__)


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

                    # --- স্প্যাম প্রোটেকশন ---
                    if is_rate_limited(sender_id):
                        logger.info(f"ইউজার {sender_id} rate-limited, মেসেজ ignore করা হলো।")
                        continue

                    save_analytics(sender_id, user_message)
                    send_typing_indicator(sender_id)

                    try:
                        bot_reply, used_ai = get_gemini_response(sender_id, user_message)
                    except Exception as e:
                        logger.error(f"Unhandled error in webhook: {e}")
                        notify_admin(f"🚨 Unhandled error in bot:\n{e}")
                        bot_reply = "কিছু একটা সমস্যা হয়েছে, একটু পরে আবার চেষ্টা করো।"

                    send_messenger_message(sender_id, bot_reply)

    return "EVENT_RECEIVED", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
