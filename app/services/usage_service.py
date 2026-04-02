import os
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta

import psycopg2
import psycopg2.extras

from app.config import get_settings

settings = get_settings()

# ---- IST timezone ----
try:
    from zoneinfo import ZoneInfo
    IST_TZ = ZoneInfo("Asia/Kolkata")
except Exception:
    IST_TZ = timezone(timedelta(hours=5, minutes=30))

# ===================== CONFIG =====================

USAGE_TABLE_NAME = os.getenv("USAGE_TABLE_NAME", "_2025_learner_usages_status")

IMAGE_BOX_WIDTH = 100
IMAGE_BOX_HEIGHT = 150

USAGE_TS_FMT = "%d-%m-%Y %H:%M:%S"

FIRST_TIME_MSG = (
    "नमस्ते {first_name}!👋\n"
    "मैं हूँ प्रगति दीदी – आपकी पढ़ाई और सपनों की साथी 💫\n\n"
)

RETURNING_MSG = (
    "Hi {first_name}! 😄 फिर मिल गए हम!\n"
    "पिछली बार आपने {last_subject} का {last_chapter} पढ़ा था 👏\n"
)

# ===================== DB =====================

def get_db_connection():
    return psycopg2.connect(
        host=settings.pg_host,
        port=settings.pg_port,
        user=settings.pg_user,
        password=settings.pg_password,
        dbname=settings.pg_database
    )

# ===================== HELPERS =====================

def extract_first_name(full_name: str) -> str:
    if not full_name:
        return ""
    return full_name.strip().split()[0]


# ✅ NO BASE_URL → direct relative path
def get_static_url(path: str) -> str:
    return f"/static/{path}"


def parse_usage_ts(ts_val: str) -> Optional[datetime]:
    if not ts_val:
        return None

    try:
        return datetime.strptime(ts_val, USAGE_TS_FMT)
    except:
        return None

# ===================== LOG =====================

def log_usage(learner_id: str, camp_id: str, mobile: str):
    try:
        query = f"""
            INSERT INTO "{USAGE_TABLE_NAME}"
            (timestamps, learner_id, camp_id, mobile, type)
            VALUES (%s, %s, %s, %s, %s)
        """

        values = (
            datetime.now(IST_TZ).strftime("%Y-%m-%d %H:%M:%S"),
            learner_id,
            camp_id,
            mobile or "",
            "session_start",
        )

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, values)
            conn.commit()

    except Exception as e:
        print("log_usage error:", e)

# ===================== VISITS =====================

def get_visits_last_subject_chapter(learner_id: str):
    try:
        query = f"""
            SELECT timestamps, chapter, subject
            FROM "{USAGE_TABLE_NAME}"
            WHERE learner_id = %s
        """

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (learner_id,))
                items = cur.fetchall()

        visits = len(items)

        items.sort(
            key=lambda x: parse_usage_ts(x.get("timestamps")) or datetime.min,
            reverse=True
        )

        for item in items:
            if item.get("chapter"):
                return visits, item.get("subject"), item.get("chapter")

        return visits, None, None

    except Exception as e:
        print("visit error:", e)
        return 0, None, None

# ===================== MAIN =====================

def build_welcome_payload(
    learner_id: str,
    camp_id: str,
    mobile: str,
    learner_name: Optional[str],
) -> Dict[str, Any]:

    first_name = extract_first_name(learner_name or "")

    visits, last_subject, last_chapter = get_visits_last_subject_chapter(learner_id)

    log_usage(learner_id, camp_id, mobile)

    is_first_time = visits == 0

    message = (
        FIRST_TIME_MSG if is_first_time else RETURNING_MSG
    ).replace("{first_name}", first_name or "मित्र") \
     .replace("{last_subject}", last_subject or "") \
     .replace("{last_chapter}", last_chapter or "")

    # ✅ STATIC FILES (no base_url)
    image_path = "media/wel_1.jpeg" if is_first_time else "media/wel_2.jpeg"
    video_path = "media/intro_video.mp4"

    return {
        "learner_id": learner_id,
        "visits": visits,
        "message": message,
        "image_url": get_static_url(image_path),
        "video_url": get_static_url(video_path),
        "image_box": {
            "width": IMAGE_BOX_WIDTH,
            "height": IMAGE_BOX_HEIGHT
        }
    }