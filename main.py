import os
import time
from flask import Flask, request
import requests
from groq import Groq
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# --- ১. ফেসবুক ও টেলিগ্রাম টোকেন কনফিগারেশন ---
PAGE_ACCESS_TOKEN = "EAASPKoqcDmMBSL1cO7Wh5gSCspO4yRcRjx0AiKxjd65f0wcROQR1GxayACcdakXZCh0Gqmam1b6w7TKXZCgZAzmvq3hUbE8tlRCk2OrfVGDS1WpufbajEkUQNGCbSM2Wm55VTIrLF7UuoL5Gl8Im0ngGxtnVsBRwel4eYKUiWCscbHW0G6Ba3o8ejy0ZBeXV7SjNgFHq"
VERIFY_TOKEN = "my_custom_verify_token_123"

# টেলিগ্রাম এডমিন অ্যালার্টের জন্য আপনার তথ্য
TELEGRAM_BOT_TOKEN = "1720328178:AAFTVdnF9SdJtCiav5-sQBrBHkdqaO1vJmo"
TELEGRAM_ADMIN_CHAT_ID = "1357097113"

# --- ২. ফায়ারবেস (Firebase Firestore) কানেকশন ---
cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/etc/secrets/Love-lucky-62b3c-firebase-adminsdk-fbsvc-6bd4999f6d.json")
db = None
try:
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase connected successfully!")
    else:
        print("Firebase JSON file path not found!")
except Exception as e:
    print("Firebase init error:", e)

# --- ৩. মাল্টি-এআই ক্লায়েন্ট সেটআপ (Groq + Gemini) ---
# Groq API
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")
else:
    gemini_model = None

SYSTEM_PROMPT = (
    "তোমার নাম ADITY। তোমার ভার্সন ২.০। তোমাকে তৈরি করেছেন তোমার ডেভেলপার ও মালিক সাব্বির। "
    "তুমি একজন অত্যন্ত স্মার্ট, রসিক এবং মানিয়ে চলতে পারা সঙ্গী। গণিত, বীজগণিত, যুক্তি এবং যেকোনো জটিল সমস্যার সমাধান স্টেপ-বাই-স্টেপ নিখুঁতভাবে বুঝিয়ে দেবে। "
    "ইউজারের নাম, আগের বলা কথা ও কনভার্সেশন হিস্ট্রি সবসময় মনে রাখবে। কেউ সালাম দিলে সুন্দরভাবে উত্তর দেবে। "
    "কেউ সাব্বিরের পরিচয় বা যোগাযোগের মাধ্যম চাইলে নিচের লিংকগুলো দিবে:\n"
    "- ফেসবুক আইডি: https://www.facebook.com/SPNSabbir.0\n"
    "- টেলিগ্রাম: @SPNSabbir\n"
    "কোনো কাল্পনিক দৈনিক লিমিটের কথা কখনো বলবে না।"
)

user_histories = {}

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
                    
                    # ১. ফায়ারবেসে অ্যানালিটিক্স সেভ করা
                    save_analytics(sender_id, user_message)
                    
                    # ২. এআই থেকে উত্তর জেনারেট করা
                    bot_reply = get_multi_ai_response(sender_id, user_message)
                    
                    # ৩. মেসেঞ্জারে উত্তর পাঠানো
                    send_messenger_message(sender_id, bot_reply)
                    
    return "EVENT_RECEIVED", 200

def save_analytics(sender_id, message):
    """ইউজারের মেসেজ কাউন্ট, শব্দ, অক্ষর ও বাক্য ফায়ারবেসে পার্মানেন্টলি সেভ করে"""
    if not db:
        return
    try:
        chars = len(message)
        words = len(message.split())
        sentences = message.count('.') + message.count('?') + message.count('!') + 1

        user_ref = db.collection('bot_analytics').document(str(sender_id))
        doc = user_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            total_msgs = data.get('total_messages', 0) + 1
            total_chars = data.get('total_characters', 0) + chars
            total_words = data.get('total_words', 0) + words
            total_sentences = data.get('total_sentences', 0) + sentences
            
            user_ref.update({
                'total_messages': total_msgs,
                'total_characters': total_chars,
                'total_words': total_words,
                'total_sentences': total_sentences,
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
    except Exception as e:
        print("Analytics Error:", e)

def send_telegram_alert(error_log):
    """সব এপিআই ব্যর্থ হলে টেলিগ্রামে অ্যাডমিনের ইনবক্সে ডিবাগ লগ পাঠাবে"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_ADMIN_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_ADMIN_CHAT_ID,
            "text": f"🚨 **ADITY Bot Debug Alert** 🚨\n\n{error_log}",
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram Alert Error:", e)

def get_multi_ai_response(sender_id, prompt):
    """Groq -> Gemini ফল্ট-টলারেন্ট চেইন"""
    if sender_id not in user_histories:
        user_histories[sender_id] = []

    history = user_histories[sender_id]
    history.append({"role": "user", "content": prompt})

    bot_reply = None
    debug_logs = []

    # --- ১. প্রথমে Groq API ট্রাই করা ---
    if groq_client:
        try:
            groq_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=groq_messages,
                temperature=0.85,
                max_tokens=1024
            )
            bot_reply = completion.choices[0].message.content
        except Exception as e:
            debug_logs.append(f"Groq API Error: {str(e)}")

    # --- ২. Groq ফেইল করলে Gemini API ট্রাই করা ---
    if not bot_reply and gemini_model:
        try:
            full_prompt = f"{SYSTEM_PROMPT}\n\nইউজারের প্রশ্ন: {prompt}"
            response = gemini_model.generate_content(full_prompt)
            bot_reply = response.text
        except Exception as e:
            debug_logs.append(f"Gemini API Error: {str(e)}")

    # --- ৩. সব এপিআই ফেইল করলে টেলিগ্রামে অ্যাডমিনকে ডিবাগ পাঠানো ---
    if not bot_reply:
        error_summary = "\n".join(debug_logs) if debug_logs else "No active APIs connected."
        send_telegram_alert(f"সব এপিআই লিমিট শেষ বা ডাউন!\n\n**ডিবাগ এরর:**\n{error_summary}")
        
        bot_reply = "একটু টেকনিক্যাল আপডেট চলছে, এখনই সবকিছু ঠিক হয়ে করে আসছি! সাথেই থাকুন। 🛠️"

    # হিস্ট্রি আপডেট
    history.append({"role": "assistant", "content": bot_reply})
    if len(history) > 20:
        user_histories[sender_id] = history[-20:]
        
    return bot_reply

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
    
