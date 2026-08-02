import os
import time
from flask import Flask, request
import requests
from groq import Groq

app = Flask(__name__)

# সিক্রেট কী-সমূহ
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "EAASPKoqcDmMBSL1cO7Wh5gSCspO4yRcRjx0AiKxjd65f0wcROQR1GxayACcdakXZCh0Gqmam1b6w7TKXZCgZAzmvq3hUbE8tlRCk2OrfVGDS1WpufbajEkUQNGCbSM2Wm55VTIrLF7UuoL5Gl8Im0ngGxtnVsBRwel4eYKUiWCscbHW0G6Ba3o8ejy0ZBeXV7SjNgFHq")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_custom_verify_token_123")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = None
if GROQ_API_KEY:
    client = Groq(api_key=GROQ_API_KEY)

# ইউজারদের চ্যাট হিস্ট্রি ডিকশনারি
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
                    bot_reply = get_groq_response(sender_id, user_message)
                    send_messenger_message(sender_id, bot_reply)
                    
    return "EVENT_RECEIVED", 200

def get_groq_response(sender_id, prompt):
    if not client:
        return "সাব্বির আমাকে একটু আপডেট করতেছে, একটু অপেক্ষা করুন।"
    
    if sender_id not in user_histories:
        user_histories[sender_id] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    history = user_histories[sender_id]
    history.append({"role": "user", "content": prompt})

    for attempt in range(2):
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=history,
                temperature=0.85,
                max_tokens=1024
            )
            bot_reply = completion.choices[0].message.content
            
            history.append({"role": "assistant", "content": bot_reply})
            
            # হিস্ট্রি সাইজ সীমিত রাখা
            if len(history) > 21:
                user_histories[sender_id] = [history[0]] + history[-20:]

            return bot_reply

        except Exception as e:
            print(f"Error (Attempt {attempt+1}):", e)
            time.sleep(1)

    return "দুঃখিত, এই মুহূর্তে সার্ভারে একটু সমস্যা হচ্ছে। একটু পরে আবার চেষ্টা করো!"

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
    
