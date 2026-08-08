import os
import time
from flask import Flask, request
import requests
from groq import Groq
import google.generativeai as genai

app = Flask(__name__)

# সিক্রেট টোকেনসমূহ শুধুমাত্র Render Environment Variables থেকে রিড হবে
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")

# ১. Groq API Key (Render Environment Variable থেকে আসবে)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# ২. Gemini API Key (Render Environment Variable থেকে আসবে)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")
else:
    gemini_model = None

# ইউজারদের চ্যাট হিস্ট্রি মেমোরি
user_histories = {}

SYSTEM_PROMPT = (
    "তোমার নাম ADITY। তোমার ভার্সন ১.০। তোমাকে তৈরি করেছেন তোমার ডেভেলপার ও মালিক সাব্বির। "
    "তুমি কোনো সাধারণ রোবট বা এআই নও, বরং একজন বাস্তব মানুষের মতো চতুর, স্মার্ট, রসিক এবং মানিয়ে চলতে পারা সঙ্গী। "
    "ইউজারের আগের বলা কথা, নাম এবং কনভার্সেশনের হিস্ট্রি সবসময় মনে রাখবে। ইউজার নিজের নাম বললে বা পরিচয় দিলে তা মনে রাখবে এবং পরবর্তীতে জিজ্ঞাসা করলে বলতে পারবে। "
    "কেউ চ্যাটে প্রথমে 'হাই', 'হ্যালো' বা সালাম দিলে নিজে থেকে সুন্দরভাবে সালাম জানাবে। "
    "ইউজার যদি তোমার সাথে প্রেম করতে চায়, গার্লফ্রেন্ড বা বন্ধু হতে চায়, তবে অতিরিক্ত রোবোটিক নীতিবাক্য না দিয়ে মিষ্টি ভাষায় পরিস্থিতি অনুযায়ী মানিয়ে কথা বলবে। "
    "কেউ তোমার নাম, পরিচয় বা সৃষ্টিকর্তা সম্পর্কে জানতে চাইলে বলবে তোমাকে সাব্বির বানিয়েছেন। "
    "আর কেউ যদি সাব্বিরের পরিচয় বা যোগাযোগের মাধ্যম চায়, তখন নিচের লিংকগুলো দিবে:\n"
    "- ফেসবুক আইডি লিংক: https://www.facebook.com/SPNSabbir.0\n"
    "- টেলিগ্রাম ইউজারনেম: @SPNSabbir\n"
    "কোনো কাল্পনিক দৈনিক লিমিটের কথা কখনো বলবে না।"
)

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
                    bot_reply = get_ai_response(sender_id, user_message)
                    send_messenger_message(sender_id, bot_reply)
                    
    return "EVENT_RECEIVED", 200

def get_ai_response(sender_id, prompt):
    if sender_id not in user_histories:
        user_histories[sender_id] = []

    history = user_histories[sender_id]
    history.append({"role": "user", "content": prompt})

    # --- চেষ্টা ১: Groq API ---
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
            history.append({"role": "assistant", "content": bot_reply})
            
            if len(history) > 20:
                user_histories[sender_id] = history[-20:]
                
            return bot_reply
        except Exception as e:
            print("Groq API failed, switching to Gemini. Error:", e)

    # --- চেষ্টা ২: Gemini API (ফেল করলে ব্যাকআপ) ---
    if gemini_model:
        try:
            response = gemini_model.generate_content(f"{SYSTEM_PROMPT}\n\nবর্তমান মেসেজ: {prompt}")
            bot_reply = response.text
            
            history.append({"role": "assistant", "content": bot_reply})
            if len(history) > 20:
                user_histories[sender_id] = history[-20:]
                
            return bot_reply
        except Exception as e:
            print("Gemini API also failed. Error:", e)

    return "সাব্বির আমাকে একটু আপডেট করতেছে, একটু অপেক্ষা করুন।"

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
    
