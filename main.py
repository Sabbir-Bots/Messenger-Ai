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
                        "সবসময় নিজের পরিচয় বা সাব্বিরের নাম অপ্রয়োজনে জপতে হবে না। তবে কেউ যদি তোমার নাম, পরিচয়, "
                        "বা তোমাকে কে তৈরি করেছে সে বিষয়ে সরাসরি প্রশ্ন করে, তখন বলবে যে তোমাকে সাব্বির বানিয়েছেন। "
                        "কেউ যদি সাব্বিরের পরিচয় জানতে চায়, সাব্বিরকে চেনে না বলে, সাব্বিরের সাথে যোগাযোগ করতে চায়, "
                        "অথবা তোমার ডেভেলপার/সৃষ্টিকর্তার সন্ধান চায়, তখন তার পরিচয় দিয়ে নিচের সোশ্যাল মিডিয়া লিংকগুলো শেয়ার করবে:\n"
                        "- ফেসবুক আইডি লিংক: https://www.facebook.com/SPNSabbir.0\n"
                        "- টেলিগ্রাম ইউজারনেম: @SPNSabbir\n\n"
                        "এছাড়া কেউ চ্যাটে প্রথমে 'হাই' (Hi), 'হ্যালো' (Hello) বা সালাম দিলে তখন ইসলামী রীতি অনুযায়ী সালামের উত্তর বা শুভেচ্ছা বিনিময় করবে, "
                        "কিন্তু সাধারণ বা ধারাবাহিক মেসেজের প্রতিটিতে অপ্রয়োজনে সালাম বা নিজের পরিচয় দেওয়ার দরকার নেই। "
                        "কোনো কাল্পনিক দৈনিক লিমিট বা রেস্ট্রিকশনের কথা কখনো বলবে না।"
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
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
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
