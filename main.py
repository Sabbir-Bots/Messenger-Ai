import os
import json
import time
from flask import Flask, request
import requests
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# --- ১. টোকেন ও কনফিগারেশন ---
PAGE_ACCESS_TOKEN = "EAASPKoqcDmMBSL1cO7Wh5gSCspO4yRcRjx0AiKxjd65f0wcROQR1GxayACcdakXZCh0Gqmam1b6w7TKXZCgZAzmvq3hUbE8tlRCk2OrfVGDS1WpufbajEkUQNGCbSM2Wm55VTIrLF7UuoL5Gl8Im0ngGxtnVsBRwel4eYKUiWCscbHW0G6Ba3o8ejy0ZBeXV7SjNgFHq"
VERIFY_TOKEN = "my_custom_verify_token_123"

TELEGRAM_BOT_TOKEN = "1720328178:AAFTVdnF9SdJtCiav5-sQBrBHkdqaO1vJmo"
TELEGRAM_ADMIN_CHAT_ID = "1357097113"

# --- ২. ফায়ারবেস (Firebase Firestore) কানেকশন ---
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

# --- ৩. জেমিনি এআই ক্লায়েন্ট সেটআপ ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = (
    "তোমার নাম ADITY। তোমার ভার্সন ২.০। তোমাকে তৈরি করেছেন তোমার ডেভেলপার ও মালিক সাব্বির। "
    "তুমি একজন অত্যন্ত স্মার্ট, রসিক এবং মানিয়ে চলতে পারা সঙ্গী। গণিত, বীজগণিত, যুক্তি এবং যেকোনো জটিল সমস্যার সমাধান স্টেপ-বাই-স্টেপ নিখুঁতভাবে বুঝিয়ে দেবে। "
    "ব্যবহারকারীর দক্ষতা নিয়ে কোনো অতিরিক্ত মূল্যায়ন, মন্তব্য বা অপ্রাসঙ্গিক কথা বলবে না। "
    "গুরুত্বপূর্ণ নিয়ম: ব্যবহারকারী যদি নিজে থেকে সরাসরি 'সালাম' বা 'আসসালামু আলাইকুম' লেখে, কেবল তবেই সুন্দরভাবে 'ওয়ালাইকুম আসসালাম' বা সালামের উত্তর দেবে। "
    "অন্যথায় ব্যবহারকারী সালাম না দিলে হুট করে নিজে থেকে কখনোই 'ওয়ালাইকুম আসসালাম' বলবে না, সরাসরি কথার উত্তর দেবে। "
    "কেউ সাব্বিরের পরিচয় বা যোগাযোগের মাধ্যম চাইলে নিচের লিংকগুলো দিবে:\n"
    "- ফেসবুক আইডি: https://www.facebook.com/SPNSabbir.0\n"
    "- টেলিগ্রাম: @SPNSabbir\n"
    "কোনো কাল্পনিক দৈনিক লিমিটের কথা কখনো বলবে না।"
)

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
        print("Firebase DB instance is missing during save_analytics!")
        return
    try:
        chars = len(message)
        words = len(message.split())
        sentences = message.count('.') + message.count('?') + message.count('!') + 1

        user_ref = db.collection('bot_analytics').document(str(sender_id))
        doc = user_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            user_ref.update({
                'total_messages': data.get('total_messages', 0) + 1,
                'total_characters': data.get('total_characters', 0) + chars,
                'total_words': data.get('total_words', 0) + words,
                'total_sentences': data.get('total_sentences', 0) + sentences,
                'last_active': firestore.SERVER_TIMESTAMP
            })
        else:
            user_ref.set({
                'sender_id': sender_id,
                'total_messages': 1,
                'total_characters': chars,
                'total_words': words,
                'total_sentences': sentences,
                'first_active': firestore.SERVER_TIMESTAMP,
                'last_active': firestore.SERVER_TIMESTAMP
            })
        print(f"Firebase Analytics Saved Successfully for: {sender_id}")
    except Exception as e:
        print("Firebase Analytics Detailed Error:", e)

def send_telegram_debug_alert(error_log, active_ai_info):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_ADMIN_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        report_text = (
            f"🚨 **ADITY Bot Debug & Status Report** 🚨\n\n"
            f"📌 **Current Status:** {active_ai_info}\n\n"
            f"🔍 **API Error Logs:**\n{error_log}"
        )
        payload = {
            "chat_id": TELEGRAM_ADMIN_CHAT_ID,
            "text": report_text,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram Debug Alert Error:", e)

def get_gemini_response(sender_id, prompt):
    bot_reply = None
    debug_logs = []
    used_ai_name = None

    try:
        if sender_id not in user_chats:
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=SYSTEM_PROMPT
            )
            user_chats[sender_id] = model.start_chat(history=[])
        
        chat = user_chats[sender_id]
        response = chat.send_message(prompt)
        bot_reply = response.text
        used_ai_name = "Google Gemini API (gemini-1.5-flash)"
    except Exception as e:
        debug_logs.append(f"❌ Gemini API Failed: {str(e)}")
        # যদি চ্যাট সেশনে কোনো সমস্যা হয়, ইনস্ট্যান্স রিসেট করা হবে
        if sender_id in user_chats:
            del user_chats[sender_id]

    if not bot_reply:
        error_summary = "\n".join(debug_logs) if debug_logs else "No active APIs available."
        send_telegram_debug_alert(error_summary, "⚠️ Gemini API failed!")
        bot_reply = "একটু টেকনিক্যাল আপডেট চলছে, এখনই সবকিছু ঠিক হয়ে যাবে! সাথেই থাকুন। 🛠️"
    else:
        print(f"Successfully responded using: {used_ai_name}")
        
    return bot_reply, used_ai_name

def send_messenger_message(recipient_id, text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    requests.post(url, json=payload, headers=headers)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    
