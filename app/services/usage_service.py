import os
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta

import boto3
import psycopg2
import psycopg2.extras

from app.config import get_settings

settings = get_settings()

# ---- IST timezone setup ----
try:
    from zoneinfo import ZoneInfo
    IST_TZ = ZoneInfo("Asia/Kolkata")
except Exception:
    IST_TZ = timezone(timedelta(hours=5, minutes=30))

# ===================== Config =====================
REGION = settings.aws_region

USAGE_TABLE_NAME = os.getenv("USAGE_TABLE_NAME", "_2025_learner_usages_status")

IMAGE_BUCKET = os.getenv("IMAGE_BUCKET", settings.bucket_name)
FIRST_TIME_IMAGE_KEY = os.getenv("FIRST_TIME_IMAGE_KEY", "image/wel_1.jpeg")
RETURNING_IMAGE_KEY = os.getenv("RETURNING_IMAGE_KEY", "image/wel_2.jpeg")
VIDEO_KEY = os.getenv("VIDEO_KEY", "image/intro_video.MP4")

PRESIGN_EXPIRES_SECONDS = int(os.getenv("PRESIGN_EXPIRES", "604800"))

IMAGE_BOX_WIDTH = int(os.getenv("IMAGE_BOX_WIDTH", "100"))
IMAGE_BOX_HEIGHT = int(os.getenv("IMAGE_BOX_HEIGHT", "150"))

USAGE_TS_FMT = "%d-%m-%Y %H:%M:%S"

FIRST_TIME_MSG = (
    "नमस्ते {first_name}!👋\n"
    "मैं हूँ प्रगति दीदी – आपकी पढ़ाई और सपनों की साथी 💫\n\n"
    "यहाँ आप सुन सकते हैं कहानियाँ, सीख सकते हैं नए शब्द और खुद को 10वीं के लिए तैयार कर सकते हैं!\n\n"
)

RETURNING_MSG = (
    "Hi {first_name}! 😄 फिर मिल गए हम!\n"
    "पिछली बार आपने {last_subject} का {last_chapter} ध्यान से पढ़ा था।👏\n"
    "आज सिर्फ़ 15 मिनट निकालें — कुछ नया और मज़ेदार सीखते हैं? ✨"
)

# keep boto3 only for S3
session = boto3.Session(region_name=REGION)
s3 = session.client("s3")


def get_db_connection():
    return psycopg2.connect(
        host=settings.pg_host,
        port=settings.pg_port,
        user=settings.pg_user,
        password=settings.pg_password,
        dbname=settings.pg_database
    )


def extract_first_name(full_name: str) -> str:
    if not full_name:
        return ""
    parts = str(full_name).strip().split()
    return parts[0] if parts else ""


def coalesce_input(data: Dict[str, Any]) -> Dict[str, Any]:
    return data or {}


def parse_usage_ts(ts_val: str) -> Optional[datetime]:
    if not ts_val:
        return None

    for fmt in (USAGE_TS_FMT, "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts_val, fmt)
        except Exception:
            continue

    s = str(ts_val)
    try:
        if s.isdigit():
            if len(s) > 11:
                return datetime.fromtimestamp(int(s) / 1000.0)
            return datetime.fromtimestamp(int(s))
    except Exception:
        pass

    return None


def presign_s3_url(bucket: str, key: str) -> str:
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=PRESIGN_EXPIRES_SECONDS,
    )


def safe_format(
    template: str,
    *,
    learner_name: Optional[str],
    first_name: Optional[str],
    last_subject: Optional[str],
    last_chapter: Optional[str],
) -> str:
    safe_full_name = (learner_name or "").strip() or "मित्र"
    safe_first_name = (first_name or "").strip() or "मित्र"
    safe_subject = (last_subject or "").strip() or "पिछला विषय"
    safe_chapter = (last_chapter or "").strip() or "पिछला अध्याय"

    text = template
    text = text.replace("{first_name}", safe_first_name)
    text = text.replace("{learner_name}", safe_full_name).replace("@learner_name", safe_full_name)
    text = text.replace("{last_subject}", safe_subject)
    text = text.replace("{last_chapter}", safe_chapter)
    return text


def log_usage(learner_id: str, camp_id: str, mobile: str) -> None:
    try:
        if not learner_id or not camp_id:
            print("Usage log skipped: learner_id or camp_id missing")
            return

        ts = datetime.now(IST_TZ)
        timestamp_str = ts.strftime("%Y-%m-%d %H:%M:%S")

        query = f"""
            INSERT INTO "{USAGE_TABLE_NAME}"
            (timestamps, learner_id, camp_id, mobile, type)
            VALUES (%s, %s, %s, %s, %s)
        """

        values = (
            timestamp_str,
            str(learner_id),
            str(camp_id),
            mobile or "",
            "Prayaas Live Session Started",
        )

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, values)
            conn.commit()

        print(f"✅ Usage logged: {learner_id} | {camp_id}")

    except Exception as e:
        print(f"Usage log error: {e}")


def get_visits_last_subject_chapter(learner_id: str) -> Tuple[int, Optional[str], Optional[str]]:
    try:
        query = f"""
            SELECT learner_id, timestamps, chapter, subject
            FROM "{USAGE_TABLE_NAME}"
            WHERE learner_id = %s
        """

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (learner_id,))
                items = cur.fetchall()

        visits = len(items)

        def sort_key(x: Dict[str, Any]):
            parsed = parse_usage_ts(x.get("timestamps", ""))
            return parsed or datetime.min

        items.sort(key=sort_key, reverse=True)

        for item in items:
            chapter = (item.get("chapter") or "").strip()
            subject = (item.get("subject") or "").strip()
            if chapter:
                return visits, subject, chapter

        return visits, None, None

    except Exception as e:
        print(f"get_visits_last_subject_chapter error: {e}")
        return 0, None, None


def build_welcome_payload(
    learner_id: str,
    camp_id: str,
    mobile: str,
    learner_name: Optional[str],
) -> Dict[str, Any]:
    learner_id = (learner_id or "").strip()
    camp_id = (camp_id or "").strip()
    mobile = (mobile or "").strip()
    learner_name = (learner_name or "").strip() or None

    first_name = extract_first_name(learner_name or "")
    visits, last_subject, last_chapter = get_visits_last_subject_chapter(learner_id)

    log_usage(learner_id=learner_id, camp_id=camp_id, mobile=mobile)

    is_first_time = visits == 0
    raw_template = FIRST_TIME_MSG if is_first_time else RETURNING_MSG

    image_key = FIRST_TIME_IMAGE_KEY if is_first_time else RETURNING_IMAGE_KEY
    image_url = presign_s3_url(IMAGE_BUCKET, image_key)
    video_url = presign_s3_url(IMAGE_BUCKET, VIDEO_KEY)

    message = safe_format(
        raw_template,
        learner_name=learner_name,
        first_name=first_name,
        last_subject=last_subject,
        last_chapter=last_chapter,
    )

    return {
        "learner_id": learner_id,
        "visits": visits,
        "last_subject": last_subject or "",
        "last_chapter": last_chapter or "",
        "message": message,
        "image_bucket": IMAGE_BUCKET,
        "image_key": image_key,
        "image_url": image_url,
        "video_url": video_url,
        "video_link": "https://youtube.com/shorts/_n5iGuWrPCw",
        "image_box": {
            "width": IMAGE_BOX_WIDTH,
            "height": IMAGE_BOX_HEIGHT,
            "fit": "contain",
        },
    }