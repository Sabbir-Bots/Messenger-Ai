import os
from flask import Flask, request
import requests

app = Flask(__name__)

# আপনার সিক্রেট কী-গুলো সংজ্ঞায়িত করুন
PAGE_ACCESS_TOKEN = "EAASPKoqcDmMBSL1cO7Wh5gSCspO4yRcRjx0AiKxjd65f0wcROQR1GxayACcdakXZCh0Gqmam1b6w7TKXZCgZAzmvq3hUbE8tlRCk2OrfVGDS1WpufbajEkUQNGCbSM2Wm55VTIrLF7UuoL5Gl8Im0ngGxtnVsBRwel4eYKUiWCscbHW0G6Ba3o8ejy0ZBeXV7SjNgFHq"
GEMINI_API_KEY = "AQ.Ab8RN6I5J7gi5VpT7kDR1Yl1PvEygFuS0kfZxSb_YkQjXv9YEQ"
VERIFY_TOKEN = "my_custom_verify_token_123"  # এটি আপনি নিজের মতো রাখতে পারেন

# ১. মেটা ওয়েবহুক ভেরিফিকেশন (GET Request)
@app.route("/", methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403

# ২. মেসেজ গ্রহণ ও উত্তর দেওয়া (POST Request)
@app.route("/", methods=['POST'])
def webhook():
    data = request.get_json()
    
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event.get("sender", {}).get("id")
                
                # যদি ব্যবহারকারী টেক্সট মেসেজ পাঠায়
                if messaging_event.get("message") and messaging_event["message"].get("text"):
                    user_message = messaging_event["message"]["text"]
                    
                    # Gemini API থেকে রেসপন্স জেনারেট করা
                    bot_reply = get_gemini_response(user_message)
                    
                    # মেসেঞ্জারে রিপ্লাই পাঠানো
                    send_messenger_message(sender_id, bot_reply)
                    
    return "EVENT_RECEIVED", 200

# Gemini API কল করার ফাংশন
def get_gemini_response(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        res_data = response.json()
        return res_data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("Error calling Gemini API:", e)
        return "দুঃখিত, কোনো সমস্যা হয়েছে। একটু পর আবার চেষ্টা করুন।"

# মেসেঞ্জারে রিপ্লাই পাঠানোর ফাংশন
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
  
