import time
from config import USER_COOLDOWN_SECONDS

# ইউজার আইডি অনুযায়ী শেষ মেসেজের টাইমস্ট্যাম্প (RAM এ)
_last_message_time = {}


def is_rate_limited(sender_id):
    """
    একজন ইউজার যদি খুব দ্রুত পরপর মেসেজ পাঠায় (স্প্যাম), তাহলে True রিটার্ন করবে।
    এটা দিয়ে Gemini API key গুলো দ্রুত exhaust হওয়া থেকে বাঁচানো যায়।
    """
    now = time.time()
    last_time = _last_message_time.get(sender_id, 0)

    if now - last_time < USER_COOLDOWN_SECONDS:
        return True

    _last_message_time[sender_id] = now
    return False
