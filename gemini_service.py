from google import genai
from google.genai import types
import hashlib

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

# ইউজারের চ্যাট হিস্ট্রি (RAM এ), ফরম্যাট: { sender_id: [ {"role": "user"/"model", "text": "..."} ] }
user_chats = {}


def get_assigned_key_index(sender_id):
    """
    প্রতিটা ইউজারকে তার sender_id অনুযায়ী একটা নির্দিষ্ট key বরাদ্দ করা হয় (sticky assignment)।
    এতে একই ইউজার সবসময় একই key ব্যবহার করে (ধারাবাহিকতা বজায় থাকে),
    কিন্তু আলাদা আলাদা ইউজার আলাদা আলাদা key-তে ছড়িয়ে যায় (load balancing)।
    """
    total_keys = len(gemini_clients)
    if total_keys == 0:
        return 0
    hash_value = int(hashlib.sha256(str(sender_id).encode("utf-8")).hexdigest(), 16)
    return hash_value % total_keys


def is_quota_error(error_msg):
    """এরর মেসেজ দেখে বোঝা যে এটা rate-limit / quota-exceeded এরর কিনা"""
    error_msg_lower = error_msg.lower()
    quota_signals = ["429", "resource_exhausted", "quota", "rate limit", "rate_limit"]
    return any(signal in error_msg_lower for signal in quota_signals)


def is_recoverable_key_error(error_msg):
    """
    এরর মেসেজ দেখে বোঝা যে এটা key/project-লেভেল সমস্যা কিনা,
    যেখানে অন্য key দিয়ে ট্রাই করলে কাজ হতে পারে।
    quota-exceeded (429) এবং permission-denied (403) দুটোই এর মধ্যে পড়ে।
    """
    error_msg_lower = error_msg.lower()
    signals = [
        "429", "resource_exhausted", "quota", "rate limit", "rate_limit",
        "403", "permission_denied", "denied access"
    ]
    return any(signal in error_msg_lower for signal in signals)


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
    if not gemini_clients:
        return "Gemini API Client is not initialized properly.", "Error"

    history = user_chats.get(sender_id, [])
    contents = build_contents(history, prompt)
    generation_config = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)

    total_keys = len(gemini_clients)
    last_error = None

    # এই ইউজারের জন্য বরাদ্দকৃত key দিয়ে শুরু, দরকার হলে পরের key গুলোতে fallback করবে
    assigned_index = get_assigned_key_index(sender_id)

    for attempt in range(total_keys):
        key_index = (assigned_index + attempt) % total_keys
        client = gemini_clients[key_index]

        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=generation_config
            )

            if response and response.text:
                logger.info(f"✅ রেসপন্স তৈরি হয়েছে key #{key_index + 1} দিয়ে (sender: {sender_id})")

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

            if is_recoverable_key_error(error_msg):
                continue  # এই key তে সমস্যা (quota/permission), পরের key দিয়ে fallback ট্রাই
            else:
                if sender_id in user_chats:
                    del user_chats[sender_id]
                return (
                    f"টেকনিক্যাল ত্রুটি দেখা দিয়েছে। বিস্তারিত: {error_msg[:100]}",
                    "Error Handled"
                )

    # সবগুলো key-তেই সমস্যা হলে
    notify_admin(f"⚠️ এই ইউজারের জন্য চেষ্টা করা সবগুলো ({total_keys}টা) Gemini API key ব্যর্থ হয়েছে!\nশেষ এরর: {str(last_error)[:200]}")
    return (
        "এই মুহূর্তে অনেক বেশি চাপ যাচ্ছে, একটু পরে আবার চেষ্টা করো।",
        f"All Keys Failed (last error: {str(last_error)[:80]})"
    )
