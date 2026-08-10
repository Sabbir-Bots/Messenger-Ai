import os
import json
from datetime import datetime, timezone, timedelta
from flask import Flask, request
import requests
from google import genai
from google.genai import types
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# --- ১. এনভায়রনমেন্ট ভ্যারিয়েবল থেকে টোকেন ও কনফিগারেশন লোড ---
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_custom_verify_token_123")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_ADMIN_CHAT_ID = os.environ.get("TELEGRAM_ADMIN_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- ২. ফায়ারবেস (Firebase Firestore) কানেকশন ---
db = None
try:
    firebase_cred_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if firebase_cred_json:
        if firebase_cred_json.strip().startswith("{"):
            cred_dict = json.loads(firebase_cred_json)
            cred = credentials.Certificate(cred_dict)
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
        else:
            cred = credentials.Certificate(firebase_cred_json)
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)

        db = firestore.client()
        print("Firebase connected successfully!")
    else:
        print("Firebase credentials not found in environment variables.")
except Exception as e:
    print("Firebase init error:", e)

# --- ৩. নতুন Google GenAI ক্লায়েন্ট সেটআপ ---
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

# বর্তমানে চালু (GA / স্ট্যাবল) মডেল - gemini-2.5-flash এখন বন্ধ হয়ে গেছে
GEMINI_MODEL = "gemini-3.6-flash"

# "আজকের" হিসাব বাংলাদেশ সময় (UTC+6) অনুযায়ী রিসেট হবে
BD_TZ = timezone(timedelta(hours=6))


def get_today_str():
    return datetime.now(BD_TZ).strftime('%Y-%m-%d')

SYSTEM_PROMPT = (
    "তোমার নাম ADITY। তোমার ভার্সন ২.০। তোমাকে তৈরি করেছেন তোমার ডেভেলপার ও মালিক সাব্বির। "
    "তুমি একজন অত্যন্ত স্মার্ট, রসিক এবং মানিয়ে চলতে পারা সঙ্গী। গণিত, বীজগণিত, যুক্তি এবং যেকোনো জটিল সমস্যার সমাধান স্টেপ-বাই-স্টেপ নিখুঁতভাবে বুঝিয়ে দেবে। "
    "ব্যবহারকারীর দক্ষতা নিয়ে কোনো অতিরিক্ত মূল্যায়ন, মন্তব্য বা অপ্রাসঙ্গিক কথা বলবে না। "
    "গুরুত্বপূর্ণ নিয়ম: ব্যবহারকারী যদি নিজে থেকে সরাসরি 'সালাম' বা 'আসসালামু আলাইকুম' লেখে, কেবল তবেই সুন্দরভাবে 'ওয়ালাইকুম আসসালাম' বা সালামের উত্তর দেবে। "
    "অন্যথায় ব্যবহারকারী সালাম না দিলে হুট করে নিজে থেকে কখনোই 'ওয়ালাইকুম আসসালাম' বলবে না, সরাসরি কথার উত্তর দেবে। "
    "কেউ সাব্বিরের পরিচয় বা যোগাযোগের মাধ্যম চাইলে নিচের লিংকগুলো দিবে:\n"
    "- ফেসবুক আইডি: https://www.facebook.com/SPNSabbir.0\n"
    "- টেলিগ্রাম: @SPNSabbir\n"
    "কোনো কাল্পনিক দৈনিক লিমিটের কথা কখনো বলবে না।"
)

# ব্যবহারকারীদের চ্যাট হিস্ট্রি সংরক্ষণের জন্য মেমোরি ডিকশনারি
user_chats = {}


@app.route("/", methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403


@app.route("/", methods=['POST'])
def webhook():
    data = request.get_json()

    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event.get("sender", {}).get("id")

                if messaging_event.get("message") and messaging_event["message"].get("text"):
                    user_message = messaging_event["message"]["text"]

                    save_analytics(sender_id, user_message)
                    bot_reply, used_ai = get_gemini_response(sender_id, user_message)
                    send_messenger_message(sender_id, bot_reply)

    return "EVENT_RECEIVED", 200


def save_analytics(sender_id, message):
    if not db:
        return
    try:
        chars = len(message)
        words = len(message.split())
        sentences = message.count('.') + message.count('?') + message.count('!') + 1
        today_str = get_today_str()

        user_ref = db.collection('bot_analytics').document(str(sender_id))
        doc = user_ref.get()

        if doc.exists:
            data = doc.to_dict()

            # আজকের হিসাব: আগের last_active_date আজকের সাথে না মিললে ০ থেকে রিসেট হবে
            if data.get('last_active_date') == today_str:
                today_messages = data.get('today_total_messages', 0) + 1
                today_characters = data.get('today_total_characters', 0) + chars
                today_sentences = data.get('today_total_sentences', 0) + sentences
            else:
                today_messages = 1
                today_characters = chars
                today_sentences = sentences

            user_ref.update({
                'total_messages': data.get('total_messages', 0) + 1,
                'total_characters': data.get('total_characters', 0) + chars,
                'total_words': data.get('total_words', 0) + words,
                'total_sentences': data.get('total_sentences', 0) + sentences,
                'today_total_messages': today_messages,
                'today_total_characters': today_characters,
                'today_total_sentences': today_sentences,
                'last_active_date': today_str,
                'last_active': firestore.SERVER_TIMESTAMP
            })
        else:
            user_ref.set({
                'sender_id': sender_id,
                'total_messages': 1,
                'total_characters': chars,
                'total_words': words,
                'total_sentences': sentences,
                'today_total_messages': 1,
                'today_total_characters': chars,
                'today_total_sentences': sentences,
                'last_active_date': today_str,
                'first_active': firestore.SERVER_TIMESTAMP,
                'last_active': firestore.SERVER_TIMESTAMP
            })
    except Exception as e:
        print("Firebase Analytics Error:", e)


def get_gemini_response(sender_id, prompt):
    bot_reply = None
    used_ai_name = None

    if not client:
        return "Gemini API Client is not initialized properly.", "Error"

    try:
        # নতুন SDK অনুযায়ী চ্যাট সেশন হ্যান্ডলিং
        if sender_id not in user_chats:
            user_chats[sender_id] = client.chats.create(
                model=GEMINI_MODEL,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT
                    # NOTE: Gemini 3.x সিরিজে temperature/top_p/top_k deprecated,
                    # তাই এখানে সেগুলো আর পাঠানো হচ্ছে না।
                )
            )

        chat = user_chats[sender_id]
        response = chat.send_message(prompt)

        if response and response.text:
            bot_reply = response.text
            used_ai_name = f"Google GenAI ({GEMINI_MODEL})"
        else:
            if sender_id in user_chats:
                del user_chats[sender_id]
            bot_reply = "দুঃখিত, এই বিষয়টি ফিল্টারড হয়েছে। অন্য কিছু জিজ্ঞেস করতে পারেন।"
            used_ai_name = "Safety Blocked"

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Gemini API Detailed Error: {error_msg}")

        # যদি চ্যাট সেশনে কোনো করাপ্টেড হিস্ট্রি থাকে তা ডিলিট করে দেওয়া
        if sender_id in user_chats:
            del user_chats[sender_id]

        bot_reply = f"টেকনিক্যাল ত্রুটি দেখা দিয়েছে। বিস্তারিত: {error_msg[:100]}"
        used_ai_name = "Error Handled"

    return bot_reply, used_ai_name


def send_messenger_message(recipient_id, text):
    if not PAGE_ACCESS_TOKEN:
        print("PAGE_ACCESS_TOKEN is missing!")
        return
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    requests.post(url, json=payload, headers=headers)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
