import json
from datetime import datetime, timezone, timedelta

import firebase_admin
from firebase_admin import credentials, firestore

from config import FIREBASE_CREDENTIALS
from logger import logger

db = None


def _init_firebase():
    global db
    try:
        if FIREBASE_CREDENTIALS:
            if FIREBASE_CREDENTIALS.strip().startswith("{"):
                cred_dict = json.loads(FIREBASE_CREDENTIALS)
                cred = credentials.Certificate(cred_dict)
            else:
                cred = credentials.Certificate(FIREBASE_CREDENTIALS)

            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)

            db = firestore.client()
            logger.info("Firebase connected successfully!")
        else:
            logger.warning("Firebase credentials not found in environment variables.")
    except Exception as e:
        logger.error(f"Firebase init error: {e}")


_init_firebase()

# "আজকের" হিসাব বাংলাদেশ সময় (UTC+6) অনুযায়ী রিসেট হবে
BD_TZ = timezone(timedelta(hours=6))


def get_today_str():
    return datetime.now(BD_TZ).strftime('%Y-%m-%d')


def save_analytics(sender_id, message):
    if not db:
        return
    try:
        chars = len(message)
        words = len(message.split())
        sentences = message.count('.') + message.count('?') + message.count('!') + 1
        today_str = get_today_str()

        user_ref = db.collection('bot_analytics').document(str(sender_id))
        doc = user_ref.get()

        if doc.exists:
            data = doc.to_dict()

            # আজকের হিসাব: আগের last_active_date আজকের সাথে না মিললে ০ থেকে রিসেট হবে
            if data.get('last_active_date') == today_str:
                today_messages = data.get('today_total_messages', 0) + 1
                today_characters = data.get('today_total_characters', 0) + chars
                today_sentences = data.get('today_total_sentences', 0) + sentences
            else:
                today_messages = 1
                today_characters = chars
                today_sentences = sentences

            user_ref.update({
                'total_messages': data.get('total_messages', 0) + 1,
                'total_characters': data.get('total_characters', 0) + chars,
                'total_words': data.get('total_words', 0) + words,
                'total_sentences': data.get('total_sentences', 0) + sentences,
                'today_total_messages': today_messages,
                'today_total_characters': today_characters,
                'today_total_sentences': today_sentences,
                'last_active_date': today_str,
                'last_active': firestore.SERVER_TIMESTAMP
            })
        else:
            user_ref.set({
                'sender_id': sender_id,
                'total_messages': 1,
                'total_characters': chars,
                'total_words': words,
                'total_sentences': sentences,
                'today_total_messages': 1,
                'today_total_characters': chars,
                'today_total_sentences': sentences,
                'last_active_date': today_str,
                'first_active': firestore.SERVER_TIMESTAMP,
                'last_active': firestore.SERVER_TIMESTAMP
            })
    except Exception as e:
        logger.error(f"Firebase Analytics Error: {e}")
