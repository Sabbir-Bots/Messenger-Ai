from google import genai
from google.genai import types

from config import GEMINI_API_KEYS, GEMINI_MODEL, MAX_HISTORY_TURNS
from prompt import SYSTEM_PROMPT
from logger import logger
from telegram_debug import notify_admin

# --- একাধিক Gemini ক্লায়েন্ট তৈরি (key rotation এর জন্য) ---
gemini_clients = []
for key in GEMINI_API_KEYS:
    try:
        gemini_clients.append(genai.Client(api_key=key))
    except Exception as e:
        logger.error(f"একটা Gemini key দিয়ে client বানাতে সমস্যা হয়েছে: {e}")

if gemini_clients:
    logger.info(f"✅ মোট {len(gemini_clients)}টা Gemini API key লোড হয়েছে।")
else:
    logger.warning("⚠️ কোনো Gemini API key পাওয়া যায়নি! GEMINI_API_KEYS সেট করো।")

# কোন key এখন ডিফল্ট হিসেবে ব্যবহার হচ্ছে
current_key_index = 0

# ইউজারের চ্যাট হিস্ট্রি (RAM এ), ফরম্যাট: { sender_id: [ {"role": "user"/"model", "text": "..."} ] }
user_chats = {}


def is_quota_error(error_msg):
    """এরর মেসেজ দেখে বোঝা যে এটা rate-limit / quota-exceeded এরর কিনা"""
    error_msg_lower = error_msg.lower()
    quota_signals = ["429", "resource_exhausted", "quota", "rate limit", "rate_limit"]
    return any(signal in error_msg_lower for signal in quota_signals)


def build_contents(history, new_prompt):
    """ইউজারের হিস্ট্রি + নতুন প্রম্পট থেকে Gemini এর জন্য contents লিস্ট বানানো"""
    contents = []
    for turn in history:
        contents.append(
            types.Content(role=turn["role"], parts=[types.Part(text=turn["text"])])
        )
    contents.append(types.Content(role="user", parts=[types.Part(text=new_prompt)]))
    return contents


def get_gemini_response(sender_id, prompt):
    global current_key_index

    if not gemini_clients:
        return "Gemini API Client is not initialized properly.", "Error"

    history = user_chats.get(sender_id, [])
    contents = build_contents(history, prompt)
    generation_config = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)

    total_keys = len(gemini_clients)
    last_error = None

    # বর্তমান key দিয়ে শুরু করে, দরকার হলে একে একে বাকি key গুলো ট্রাই করবে
    for attempt in range(total_keys):
        key_index = (current_key_index + attempt) % total_keys
        client = gemini_clients[key_index]

        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=generation_config
            )

            if response and response.text:
                current_key_index = key_index  # কাজ করা key-ই এখন থেকে ডিফল্ট

                history.append({"role": "user", "text": prompt})
                history.append({"role": "model", "text": response.text})
                user_chats[sender_id] = history[-MAX_HISTORY_TURNS:]

                return response.text, f"Google GenAI ({GEMINI_MODEL}, key #{key_index + 1})"
            else:
                return (
                    "দুঃখিত, এই বিষয়টি ফিল্টারড হয়েছে। অন্য কিছু জিজ্ঞেস করতে পারেন।",
                    "Safety Blocked"
                )

        except Exception as e:
            error_msg = str(e)
            last_error = error_msg
            logger.error(f"❌ Gemini key #{key_index + 1} এ এরর: {error_msg}")

            if is_quota_error(error_msg):
                continue  # এই key এর কোটা শেষ, পরের key দিয়ে ট্রাই
            else:
                if sender_id in user_chats:
                    del user_chats[sender_id]
                return (
                    f"টেকনিক্যাল ত্রুটি দেখা দিয়েছে। বিস্তারিত: {error_msg[:100]}",
                    "Error Handled"
                )

    # সব key ই কোটা শেষ হয়ে গেলে
    notify_admin(f"⚠️ সবগুলো ({total_keys}টা) Gemini API key exhausted হয়ে গেছে!\nশেষ এরর: {str(last_error)[:200]}")
    return (
        "এই মুহূর্তে অনেক বেশি চাপ যাচ্ছে, একটু পরে আবার চেষ্টা করো।",
        f"All Keys Exhausted (last error: {str(last_error)[:80]})"
    )
