# -*- coding: utf-8 -*-
import os
import io
from typing import Optional, Dict, Any
from datetime import timezone, timedelta

import boto3
from PIL import Image, ImageDraw, ImageFont

from app.config import get_settings

settings = get_settings()

OUTPUT_BUCKET = settings.bucket_name
REGION_NAME = settings.aws_region
FOLDER = os.getenv("IMG_PREFIX", "Prayaas_2025/learner_badges")
PRESIGN_SECS = int(os.getenv("PRESIGN_EXPIRES", "604800"))

s3 = boto3.client("s3", region_name=REGION_NAME)

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30))

# ---------------- FONT CANDIDATES ----------------
# Add or remove paths depending on your environment.
FONT_CANDIDATES = [
    "/opt/fonts/NotoSansDevanagari-Regular.ttf",
    "C:/Windows/Fonts/Mangal.ttf",
    "C:/Windows/Fonts/Nirmala.ttf",
    "C:/Windows/Fonts/arial.ttf",
]

# ---------------- BADGE IMAGE KEYS ----------------
BADGE_KEY_MAP = {
    "gold": "Prayaas_2025/badges/gold_badge.png",
    "silver": "Prayaas_2025/badges/silver_badge.png",
    "bronze": "Prayaas_2025/badges/bronze_badge.png",
}

# ---------------- TEXT / COLOR SETTINGS ----------------
NAME_COLOR = (61, 90, 128, 255)      # blue
META_COLOR = (80, 80, 80, 255)       # gray
BOTTOM_COLOR = (16, 56, 96, 255)     # dark blue

NAME_Y = 34
NAME_FONT_SIZE = 44

SUBJECT_CHAPTER_Y = 105
SUBJECT_CHAPTER_FONT_SIZE = 28

SCORE_Y_BY_BADGE = {
    "gold": 610,
    "silver": 610,
    "bronze": 610,
}

BOTTOM_TEXT_Y = 705
BOTTOM_TEXT_FONT_SIZE = 34

MAX_TEXT_WIDTH_RATIO = 0.82


def load_font(size: int):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def sanitize_for_key(text: str) -> str:
    if not text:
        return "unknown"

    cleaned = text.strip().replace(" ", "_")
    safe = []
    for ch in cleaned:
        if ch.isalnum() or ch in ["_", "-", "."]:
            safe.append(ch)
        else:
            safe.append("-")

    result = "".join(safe).strip("-_")
    return result or "unknown"


def text_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]
    except Exception:
        return int(font.getlength(text)) if hasattr(font, "getlength") else len(text) * font.size


def fit_font_size(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int, min_size: int = 16):
    size = start_size
    while size >= min_size:
        font = load_font(size)
        if text_width(draw, text, font) <= max_width:
            return font
        size -= 1
    return load_font(min_size)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int):
    words = str(text).split()
    if not words:
        return [""]

    lines = []
    current = words[0]

    for word in words[1:]:
        trial = current + " " + word
        if text_width(draw, trial, font) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word

    lines.append(current)
    return lines


def draw_centered_text(draw: ImageDraw.ImageDraw, canvas_width: int, y: int, text: str, font, fill):
    w = text_width(draw, text, font)
    x = (canvas_width - w) / 2
    draw.text((x, y), text, font=font, fill=fill)


def draw_multiline_centered_text(
    draw: ImageDraw.ImageDraw,
    canvas_width: int,
    y: int,
    text: str,
    start_font_size: int,
    max_width: int,
    fill,
    line_gap: int = 8,
    min_font_size: int = 16
):
    size = start_font_size
    final_font = load_font(size)
    final_lines = [text]

    while size >= min_font_size:
        font = load_font(size)
        lines = wrap_text(draw, text, font, max_width)

        too_wide = any(text_width(draw, line, font) > max_width for line in lines)
        if not too_wide and len(lines) <= 2:
            final_font = font
            final_lines = lines
            break

        size -= 1

    current_y = y
    line_height = final_font.size + line_gap

    for line in final_lines:
        draw_centered_text(draw, canvas_width, current_y, line, final_font, fill)
        current_y += line_height

    return current_y


def build_badge_key(learner_id: str, learner_name: str, subject: str, chapter: str) -> str:
    learner_seg = sanitize_for_key(learner_name)
    subject_seg = sanitize_for_key(subject)
    chapter_seg = sanitize_for_key(chapter)

    base_name = f"{learner_seg}_{subject_seg}_{chapter_seg}"
    prefix = f"{FOLDER}/{learner_id}/{base_name}_"

    resp = s3.list_objects_v2(Bucket=OUTPUT_BUCKET, Prefix=prefix)
    max_n = 0

    for obj in resp.get("Contents", []):
        key = obj["Key"]
        tail = key[len(prefix):]
        num_part = tail.split(".", 1)[0]
        try:
            n = int(num_part)
            if n > max_n:
                max_n = n
        except ValueError:
            continue

    next_n = max_n + 1 if max_n > 0 else 1
    return f"{prefix}{next_n}.jpg"


def load_base_badge(message_key: str) -> Image.Image:
    if message_key not in BADGE_KEY_MAP:
        raise ValueError(f"Invalid message_key '{message_key}'. Must be gold/silver/bronze")

    key = BADGE_KEY_MAP[message_key]
    obj = s3.get_object(Bucket=OUTPUT_BUCKET, Key=key)
    return Image.open(io.BytesIO(obj["Body"].read())).convert("RGBA")


def determine_badge_key(score: float, max_question: float) -> str:
    if max_question <= 0:
        return "bronze"

    percentage = (score / max_question) * 100

    if percentage >= 80:
        return "gold"
    if percentage >= 50:
        return "silver"
    return "bronze"


def get_appreciation_text(message_key: str, percentage: int) -> str:
    if message_key == "gold":
        return f""
    if message_key == "silver":
        return f""
    return f""


def merge_edits(
    base_img: Image.Image,
    name: str,
    subject: str,
    chapter: str,
    message_key: Optional[str] = None,
    score_pct: Optional[int] = None,
) -> Image.Image:
    canvas = base_img.copy()
    draw = ImageDraw.Draw(canvas)
    W, H = canvas.size

    max_width = int(W * MAX_TEXT_WIDTH_RATIO)

    # -------- 1) Learner Name --------
    name_font = fit_font_size(draw, name, max_width, NAME_FONT_SIZE, min_size=24)
    draw_centered_text(draw, W, NAME_Y, name, name_font, NAME_COLOR)

    # -------- 2) Subject + Chapter (text only, no PNG) --------
    subject_chapter_text = f"{subject} : {chapter}"
    draw_multiline_centered_text(
        draw=draw,
        canvas_width=W,
        y=SUBJECT_CHAPTER_Y,
        text=subject_chapter_text,
        start_font_size=SUBJECT_CHAPTER_FONT_SIZE,
        max_width=max_width,
        fill=META_COLOR,
        line_gap=6,
        min_font_size=18
    )

    # -------- 3) Score % --------
    if score_pct is not None:
        score_text = f"{score_pct}%"
        score_font = fit_font_size(draw, score_text, 180, 42, min_size=26)
        score_y = SCORE_Y_BY_BADGE.get(message_key or "bronze", 610)
        draw_centered_text(draw, W, score_y, score_text, score_font, META_COLOR)

    # -------- 4) Bottom appreciation text --------
    appreciation = get_appreciation_text(message_key or "bronze", score_pct or 0)
    draw_multiline_centered_text(
        draw=draw,
        canvas_width=W,
        y=BOTTOM_TEXT_Y,
        text=appreciation,
        start_font_size=BOTTOM_TEXT_FONT_SIZE,
        max_width=int(W * 0.9),
        fill=BOTTOM_COLOR,
        line_gap=8,
        min_font_size=20
    )

    return canvas


def save_to_s3(img: Image.Image, learner_id: str, learner_name: str, subject: str, chapter: str) -> dict:
    key = build_badge_key(learner_id, learner_name, subject, chapter)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=95, optimize=True)

    s3.put_object(
        Bucket=OUTPUT_BUCKET,
        Key=key,
        Body=buf.getvalue(),
        ContentType="image/jpeg",
        CacheControl="no-store",
    )

    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": OUTPUT_BUCKET, "Key": key},
        ExpiresIn=PRESIGN_SECS,
    )

    return {
        "key": key,
        "presigned_url": url,
    }


def generate_badge(payload: dict) -> Dict[str, Any]:
    learner_id = payload.get("learner_id")
    name_raw = payload.get("name")
    subject_raw = payload.get("subject")
    chapter = payload.get("chapter")
    score_raw = payload.get("score")
    max_q_raw = payload.get("max_question")
    message_key = payload.get("message_key")

    required_fields = {
        "learner_id": learner_id,
        "name": name_raw,
        "subject": subject_raw,
        "chapter": chapter,
    }
    missing_fields = [k for k, v in required_fields.items() if not v]

    if missing_fields:
        return {
            "status_code": 400,
            "data": {
                "ok": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}",
                "missing_fields": missing_fields,
            }
        }

    try:
        score_pct = None
        if score_raw is not None and max_q_raw is not None:
            s = float(score_raw)
            m = float(max_q_raw)
            if m > 0:
                score_pct = round((s / m) * 100)

        if not message_key:
            message_key = determine_badge_key(float(score_raw or 0), float(max_q_raw or 0))

        base_img = load_base_badge(message_key)
        out_img = merge_edits(
            base_img=base_img,
            name=str(name_raw),
            subject=str(subject_raw),
            chapter=str(chapter),
            message_key=message_key,
            score_pct=score_pct
        )

        result = save_to_s3(out_img, learner_id, name_raw, subject_raw, chapter)

        return {
            "status_code": 200,
            "data": {
                "presigned_url": result["presigned_url"],
                "message_key": message_key,
                "score_percentage": score_pct
            }
        }

    except Exception as e:
        return {
            "status_code": 400,
            "data": {
                "ok": False,
                "error": str(e)
            }
        }