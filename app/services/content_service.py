import re
import unicodedata
import traceback
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime, timezone, timedelta

import boto3
import psycopg2
import psycopg2.extras

from app.config import get_settings

settings = get_settings()

# ----------- Config -----------
BUCKET_NAME = settings.bucket_name
BASE_FOLDER = "Prayaas_2025"
AV_TABLE_NAME = "_2025_prayaas_av_link"
USAGE_TABLE_NAME = "_2025_learner_usages_status"

# ---- S3 client ----
s3 = boto3.client("s3", region_name=settings.aws_region)


def get_db_connection():
    return psycopg2.connect(
        host=settings.pg_host,
        port=settings.pg_port,
        user=settings.pg_user,
        password=settings.pg_password,
        dbname=settings.pg_database
    )


# ---- IST timezone setup ----
try:
    from zoneinfo import ZoneInfo
    IST_TZ = ZoneInfo("Asia/Kolkata")
except Exception:
    IST_TZ = timezone(timedelta(hours=5, minutes=30))


def normalize_text(x: str) -> str:
    return unicodedata.normalize("NFC", str(x)).strip() if x is not None else ""


def list_under_prefix(bucket: str, prefix: str, cap: int = 300) -> List[str]:
    keys = []
    token = None

    while True:
        limit = min(1000, max(1, cap - len(keys)))
        if token:
            resp = s3.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=limit,
                ContinuationToken=token
            )
        else:
            resp = s3.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=limit
            )

        for item in resp.get("Contents", []):
            keys.append(item["Key"])
            if len(keys) >= cap:
                return keys

        if resp.get("IsTruncated") and "NextContinuationToken" in resp:
            token = resp["NextContinuationToken"]
        else:
            break

    return keys


def presigned_get_url(bucket: str, key: str, expires_in: int = 3600) -> Optional[str]:
    try:
        return s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in
        )
    except Exception as e:
        print(f"Error generating presigned URL for {key}: {e}")
        return None


def canonical_chapter(ch: str) -> str:
    ch = normalize_text(ch)
    tokens = [t for t in re.split(r"[\s_]+", ch) if t]
    return "_" + "_".join(tokens) if tokens else ch


def log_learning_usage(
    learner_id: str,
    camp_id: str,
    subject: str,
    chapter: str,
    mobile: str
) -> None:
    try:
        if not learner_id:
            print("Usage log skipped: learner_id missing")
            return

        ts = datetime.now(IST_TZ)
        timestamp_str = ts.strftime("%Y-%m-%d %H:%M:%S")

        query = f"""
            INSERT INTO "{USAGE_TABLE_NAME}"
            (timestamps, learner_id, camp_id, subject, chapter, mobile, type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            timestamp_str,
            str(learner_id),
            str(camp_id or ""),
            subject or "",
            chapter or "",
            mobile or "",
            "पढ़ना",
        )

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, values)
            conn.commit()

        print("Usage log written successfully")

    except Exception as e:
        print("Unknown error while logging usage:", str(e))
        traceback.print_exc()


def find_pdf_by_suffix(
    bucket: str,
    state: str,
    subject: str,
    chapter: str,
    type_char: str
) -> Tuple[Optional[str], Optional[str]]:

    state = normalize_text(state)
    subject = normalize_text(subject)
    chapter = normalize_text(chapter)

    prefix = f"{BASE_FOLDER}/{state}/{subject}/"
    files = list_under_prefix(bucket, prefix, cap=300)

    # Normalize chapter for matching
    chapter_clean = chapter.replace("_", " ").lower()

    for key in files:
        file_name = key.split("/")[-1].lower()

        # Check type (S or V)
        if not file_name.endswith(f"{type_char.lower()}.pdf"):
            continue

        # Loose match: check if any word from chapter exists in filename
        chapter_words = chapter_clean.split()

        match_count = sum(1 for w in chapter_words if w in file_name)

        if match_count >= 1:   # at least one word matches
            url = presigned_get_url(bucket, key)
            return url, key

    return None, None


def _find_url_in_value(value) -> Optional[str]:
    url_re = re.compile(r"https?://\S+")

    if isinstance(value, str):
        m = url_re.search(value)
        return m.group(0) if m else None

    if isinstance(value, dict):
        for v in value.values():
            found = _find_url_in_value(v)
            if found:
                return found
        return None

    if isinstance(value, list):
        for v in value:
            found = _find_url_in_value(v)
            if found:
                return found
        return None

    return None


def _first_url_from_item(item: dict) -> Optional[str]:
    candidate_keys = [
        "link", "url", "media_url", "s3_url", "presigned_url", "audio_url", "video_url",
        "audio-url", "video-url", "media-url", "presigned-url", "file-url", "file_url",
        "audio", "video", "A_url", "V_url", "A-url", "V-url", "A", "V", "FileURL", "FileUrl",
        "links", "media", "files",
    ]

    for k in candidate_keys:
        if k in item:
            v = item.get(k)
            if isinstance(v, str) and v.strip():
                if v.strip().lower().startswith(("http://", "https://")):
                    return v.strip()
            if isinstance(v, (dict, list)):
                found = _find_url_in_value(v)
                if found:
                    return found

    return _find_url_in_value(item)


def get_av_link(state: str, subject: str, chapter: str, av_type: str) -> Optional[str]:
    st = normalize_text(state)
    subj = normalize_text(subject)
    chap = normalize_text(chapter)
    t_in = normalize_text(av_type)

    if t_in.lower().startswith("a"):
        type_candidates = ["A", "a", "audio", "Audio", "AUDIO"]
    elif t_in.lower().startswith("v"):
        type_candidates = ["V", "v", "video", "Video", "VIDEO"]
    else:
        type_candidates = [t_in]

    chap_no_lead = chap.lstrip("_")
    chap_spaces = chap.replace("_", " ")
    chap_no_lead_spaces = chap_no_lead.replace("_", " ")
    chapter_candidates = list(dict.fromkeys([chap, chap_no_lead, chap_spaces, chap_no_lead_spaces]))

    # First try exact SQL match
    for tval in type_candidates:
        for cval in chapter_candidates:
            try:
                query = f"""
                    SELECT *
                    FROM "{AV_TABLE_NAME}"
                    WHERE state = %s
                      AND subject = %s
                      AND chapter = %s
                      AND type = %s
                    LIMIT 1
                """

                with get_db_connection() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                        cur.execute(query, (st, subj, cval, tval))
                        row = cur.fetchone()

                if row:
                    url = _first_url_from_item(dict(row))
                    if url:
                        return url

            except Exception as e:
                print(f"SQL exact match error (state={st}, subject={subj}, chapter={cval}, type={tval}): {e}")

    # Fallback: fetch matching state+subject and filter in Python
    try:
        query = f"""
            SELECT *
            FROM "{AV_TABLE_NAME}"
            WHERE (state = %s OR "State" = %s)
              AND (subject = %s OR "Subject" = %s)
        """

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (st, st, subj, subj))
                items = cur.fetchall()

        def _norm(s: str) -> str:
            return normalize_text(s).replace(" ", "_").lstrip("_").lower()

        want_types = {_norm(t) for t in type_candidates}
        want_chaps = {_norm(c) for c in chapter_candidates}

        for it in items:
            it = dict(it)
            it_type = (
                it.get("type") or it.get("Type") or
                it.get("media_type") or it.get("mediaType") or ""
            )
            it_chap = (
                it.get("chapter") or it.get("Chapter") or
                it.get("chap") or it.get("Chap") or ""
            )

            if _norm(it_type) in want_types and _norm(it_chap) in want_chaps:
                url = _first_url_from_item(it)
                if url:
                    return url

    except Exception as e:
        print(f"SQL fallback scan error: {e}")

    return None


def fetch_learning_content(
    state: str,
    subject: str,
    chapter: str,
    mobile: str = "",
    learner_id: str = "",
    camp_id: str = "",
) -> Dict[str, Any]:
    subject = normalize_text(str(subject).replace('"', ""))
    chapter = normalize_text(chapter)
    state = normalize_text(state)
    mobile = normalize_text(mobile)
    learner_id = normalize_text(learner_id)
    camp_id = normalize_text(camp_id)

    print(f"Request received - state: {state}, subject: {subject}, chapter: {chapter}")

    summary_pdf, summary_key = find_pdf_by_suffix(BUCKET_NAME, state, subject, chapter, "S")
    vocab_pdf, vocab_key = find_pdf_by_suffix(BUCKET_NAME, state, subject, chapter, "V")

    audio_url = get_av_link(state, subject, chapter, "audio")
    video_url = get_av_link(state, subject, chapter, "video")

    log_learning_usage(
        learner_id=learner_id,
        camp_id=camp_id,
        subject=subject,
        chapter=chapter,
        mobile=mobile
    )

    if not any([summary_pdf, vocab_pdf, audio_url, video_url]):
        prefix = f"{BASE_FOLDER}/{state}/{subject}/"
        return {
            "status_code": 404,
            "data": {
                "message": "Requested resources not found",
                "expected_suffixes": {
                    "summary": f"{canonical_chapter(chapter)}S.pdf",
                    "vocab": f"{canonical_chapter(chapter)}V.pdf",
                },
                "available_under_subject": list_under_prefix(BUCKET_NAME, prefix, cap=300),
            },
        }

    missing = []
    if not summary_pdf:
        missing.append("bodypdfS")
    if not vocab_pdf:
        missing.append("bodypdfV")
    if not audio_url:
        missing.append("audio_url")
    if not video_url:
        missing.append("video_url")

    response = {
        "bodypdfS": summary_pdf or "",
        "bodypdfV": vocab_pdf or "",
        "audio_url": audio_url or "",
        "video_url": video_url or "",
    }

    if missing:
        prefix = f"{BASE_FOLDER}/{state}/{subject}/"
        response["missing"] = missing
        response["expected_suffixes"] = {
            "summary": f"{canonical_chapter(chapter)}S.pdf",
            "vocab": f"{canonical_chapter(chapter)}V.pdf",
        }
        response["available_under_subject"] = list_under_prefix(BUCKET_NAME, prefix, cap=300)
        if summary_key:
            response["matched_summary_key"] = summary_key
        if vocab_key:
            response["matched_vocab_key"] = vocab_key

    return {
        "status_code": 200,
        "data": response,
    }