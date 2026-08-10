import os

# --- ফেসবুক মেসেঞ্জার সম্পর্কিত ---
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_custom_verify_token_123")

# App Secret - webhook signature verify করার জন্য (Meta App Dashboard > Settings > Basic এ পাবে)
APP_SECRET = os.environ.get("APP_SECRET")

# --- টেলিগ্রাম অ্যাডমিন ডিবাগ/নোটিফিকেশন সিস্টেম ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_ADMIN_CHAT_ID = os.environ.get("TELEGRAM_ADMIN_CHAT_ID")

# --- Gemini API Key(গুলো) ---
# Render Environment এ GEMINI_API_KEYS নামে একটা ভ্যারিয়েবল বসাও,
# ভ্যালুতে কমা (,) দিয়ে আলাদা করে একাধিক key দাও, যেমন: key1,key2,key3
_raw_keys = os.environ.get("GEMINI_API_KEYS", "")
GEMINI_API_KEYS = [k.strip() for k in _raw_keys.split(",") if k.strip()]

# পুরনো সিঙ্গেল-কী ভ্যারিয়েবলও ব্যাকওয়ার্ড কম্প্যাটিবিলিটির জন্য সাপোর্ট করা হচ্ছে
_single_key = os.environ.get("GEMINI_API_KEY")
if _single_key and _single_key not in GEMINI_API_KEYS:
    GEMINI_API_KEYS.append(_single_key)

# বর্তমানে চালু (GA / স্ট্যাবল) মডেল
GEMINI_MODEL = "gemini-3.6-flash"

# --- ফায়ারবেস ---
FIREBASE_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

# --- বট বিহেভিয়ার কনফিগারেশন ---
MAX_HISTORY_TURNS = 20          # প্রতি ইউজারের সর্বোচ্চ কতগুলো মেসেজ মনে রাখা হবে
USER_COOLDOWN_SECONDS = 3       # স্প্যাম প্রোটেকশন: প্রতি ইউজারের দুই মেসেজের মধ্যে ন্যূনতম গ্যাপ
MESSENGER_MAX_CHARS = 1900      # একটা মেসেঞ্জার মেসেজে সর্বোচ্চ ক্যারেক্টার (নিরাপদ সীমা)

# --- সার্ভার ---
PORT = int(os.environ.get("PORT", 5000))
