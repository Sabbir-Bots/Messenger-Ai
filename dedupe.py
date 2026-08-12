import time
from logger import logger

# ইতিমধ্যে প্রসেস হওয়া মেসেজ আইডি (mid) গুলো, টাইমস্ট্যাম্প সহ
_processed_messages = {}

# কতক্ষণ পর্যন্ত একটা mid মনে রাখা হবে (সেকেন্ডে) - এর বেশি পুরনো হলে মেমোরি থেকে মুছে ফেলা হয়
_EXPIRY_SECONDS = 300  # ৫ মিনিট


def is_duplicate_message(mid):
    """
    Facebook একই মেসেজ একাধিকবার webhook এ পাঠাতে পারে (retry এর কারণে)।
    এই ফাংশন সেটা ধরে ফেলে - একই mid দ্বিতীয়বার এলে True রিটার্ন করবে।
    """
    if not mid:
        return False

    now = time.time()

    # পুরনো এন্ট্রি পরিষ্কার করা (মেমোরি লিক এড়াতে)
    expired = [m for m, t in _processed_messages.items() if now - t > _EXPIRY_SECONDS]
    for m in expired:
        del _processed_messages[m]

    if mid in _processed_messages:
        logger.info(f"🔁 ডুপ্লিকেট মেসেজ (mid: {mid}) - Facebook retry, ignore করা হলো।")
        return True

    _processed_messages[mid] = now
    return False
