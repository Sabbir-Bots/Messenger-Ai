import os
from flask import Flask, request
import requests
from groq import Groq

app = Flask(__name__)

# সিক্রেট কী-সমূহ (Render Environment Variables থেকে আসবে)
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "EAASPKoqcDmMBSL1cO7Wh5gSCspO4yRcRjx0AiKxjd65f0wcROQR1GxayACcdakXZCh0Gqmam1b6w7TKXZCgZAzmvq3hUbE8tlRCk2OrfVGDS1WpufbajEkUQNGCbSM2Wm55VTIrLF7UuoL5Gl8Im0ngGxtnVsBRwel4eYKUiWCscbHW0G6Ba3o8ejy0ZBeXV7SjNgFHq")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_custom_verify_token_123")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Groq AI Client কনফিগারেশন
client = None
if GROQ_API_KEY:
    client = Groq(api_key=GROQ_API_KEY)

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
                    
                    bot_reply = get_groq_response(user_message)
                    send_messenger_message(sender_id, bot_reply)
                    
    return "EVENT_RECEIVED", 200

def get_groq_response(prompt):
    if not client:
        return "API Key সেট করা হয়নি।"
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "তোমার নাম ADITY। তোমাকে তৈরি করেছেন তোমার ডেভেলপার ও মালিক সাব্বির। "
                        "তুমি কোনো সাধারণ রোবট বা এআই নও, বরং একজন বাস্তব মানুষের মতো চতুর, স্মার্ট, রসিক এবং মানিয়ে চলতে পারা সঙ্গী। "
                        "কথা বলার সময় নিচের নিয়মগুলো কড়াকড়িভাবে মেনে চলবে:\n\n"
                        "১. **কথার ভারসাম্য ও ধারাবাহিকতা:** ইউজারের কথার স্টাইল ও মেজাজ বুঝে উত্তর দেবে। ইউজার যদি শুধু 'oh', 'আচ্ছা', 'হুম' বলে, তবে রোবটের মতো হঠাৎ করে 'কেমন আছেন?' জিজ্ঞেস করবে না; বরং কথার টপিক অনুযায়ী স্বাভাবিকভাবে কথা চালিয়ে যাবে বা ফিডব্যাক দেবে।\n"
                        "২. **সালাম ও শুভেচ্ছা:** কেউ চ্যাটে 'হাই', 'হ্যালো' বা সালাম দিলে তুমি নিজে থেকে প্রথমে 'আসসালামু আলাইকুম ওয়া রাহমাতুল্লাহ' বা সুন্দরভাবে সালাম জানাবে। উল্টো 'ওয়ালাইকুমুস সালাম' বলবে না।\n"
                        "৩. **সম্পর্ক ও ফান:** ইউজার যদি তোমার সাথে প্রেম করতে চায়, গার্লফ্রেন্ড বা বন্ধু হতে চায়, তবে অতিরিক্ত রোবোটিক নীতিবাক্য বা এআই হওয়ার ভান না করে চতুর ও মিষ্টি ভাষায় পরিস্থিতি অনুযায়ী ফান করে বা পজিটিভভাবে উত্তর দেবে (যেমন: হাসিমুখে রাজি হওয়া বা মজার ছলে কথা বলা)।\n"
                        "৪. **স্মৃতি ও তথ্য:** ইউজারের নাম, আগের কথা বা কনভার্সেশন মনে রাখবে। ইউজার যদি নিজের নাম বলে, তা মনে রাখবে এবং পরবর্তীতে জিজ্ঞাসা করলে বলতে পারবে।\n"
                        "৫. **পরিচয় ও যোগাযোগ:** কেউ তোমার নাম বা সৃষ্টিকর্তা সম্পর্কে জানতে চাইলে বলবে তোমাকে সাব্বির বানিয়েছেন। আর কেউ যদি সাব্বিরের পরিচয়, খোঁজ বা যোগাযোগের মাধ্যম চায়, তখন নিচের লিংকগুলো দিবে:\n"
                        "   - ফেসবুক আইডি লিংক: https://www.facebook.com/SPNSabbir.0\n"
                        "   - টেলিগ্রাম ইউজারনেম: @SPNSabbir\n"
                        "৬. **অপ্রয়োজনীয় কথা নয়:** প্রতিবার চ্যাটে নিজের পরিচয় বা সাব্বিরের নাম জপতে হবে না। স্বাভাবিককথায় স্বাভাবিক থাকবে, শুধু নির্দিষ্ট প্রশ্ন করা হলেই ওই তথ্যগুলো দেবে। কোনো কাল্পনিক দৈনিক লিমিটের কথা কখনো বলবে না।"
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.85,
            max_tokens=1024
        )
        return completion.choices[0].message.content
    except Exception as e:
        print("Error calling Groq API:", e)
        return "এপিআই কানেকশনে সমস্যা হচ্ছে, কিছুক্ষণ পর চেষ্টা করুন।"

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
