import hmac
import hashlib
from config import APP_SECRET
from logger import logger


def verify_signature(raw_body, signature_header):
    """
    ফেসবুক প্রতিটা webhook রিকোয়েস্টের সাথে একটা X-Hub-Signature-256 হেডার পাঠায়।
    এটা যাচাই করে নিশ্চিত হওয়া যায় যে রিকোয়েস্টটা আসলেই Facebook থেকে আসছে,
    অন্য কেউ ভুয়া রিকোয়েস্ট পাঠাচ্ছে না।

    APP_SECRET সেট না থাকলে verification স্কিপ হবে (শুধু ডেভেলপমেন্ট/টেস্টিং এর জন্য)।
    প্রোডাকশনে অবশ্যই APP_SECRET সেট করা উচিত।
    """
    if not APP_SECRET:
        logger.warning(
            "APP_SECRET সেট করা নেই — webhook signature verify করা হচ্ছে না। "
            "প্রোডাকশনে এটা নিরাপদ নয়, Render Environment এ APP_SECRET যোগ করো।"
        )
        return True

    if not signature_header:
        return False

    try:
        expected_signature = "sha256=" + hmac.new(
            APP_SECRET.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_signature, signature_header)
    except Exception as e:
        logger.error(f"Signature verify করতে সমস্যা হয়েছে: {e}")
        return False
