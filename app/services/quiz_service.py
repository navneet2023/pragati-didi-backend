import json
import os
import decimal
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

import psycopg2
import psycopg2.extras
from decimal import Decimal

from app.config import get_settings

settings = get_settings()

# ---- IST timezone setup ----
try:
    from zoneinfo import ZoneInfo
    IST_TZ = ZoneInfo("Asia/Kolkata")
except Exception:
    IST_TZ = timezone(timedelta(hours=5, minutes=30))

QUESTIONS_TABLE = "_2025_prayaas_quiz_questions"
RESPONSES_TABLE = "_2025_prayaas_quiz_responses"
USAGE_TABLE_NAME = "_2025_learner_usages_status"
ATTEMPT_SEQUENCE_START = 1001

# ✅ Thank you image config (sent after each correct answer)
THANK_YOU_FOLDER = "Neev_2025/Thanks"
THANK_YOU_MAX = 6  # thank_you_1.png to thank_you_6.png


def get_thank_you_image_url(bucket_name: str, region: str, correct_count: int):
    """
    Returns S3 URL for thank_you_N.png based on cumulative correct answers.
    N increments with each correct answer, capped at THANK_YOU_MAX.
    Returns None if correct_count is 0.
    """
    if correct_count <= 0:
        return None
    n = min(correct_count, THANK_YOU_MAX)
    key = f"{THANK_YOU_FOLDER}/Thank_you_{n}.png"
    base_url = f"https://{bucket_name}.s3.{region}.amazonaws.com"
    return f"{base_url}/{key}"


def get_db_connection():
    return psycopg2.connect(
        host=settings.pg_host,
        port=settings.pg_port,
        dbname=settings.pg_database,
        user=settings.pg_user,
        password=settings.pg_password
    )


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def safe_int(v, default=0):
    try:
        s = str(v).strip()
        if s.isdigit():
            return int(s)
        return default
    except Exception:
        return default


def _log_usage(learner_id: str, camp_id: str, subject: str, chapter: str, mobile: str) -> None:
    try:
        ts = datetime.now(IST_TZ)
        timestamp_str = ts.strftime("%Y-%m-%d %H:%M:%S")

        if not learner_id or not camp_id:
            print("Usage log skipped: learner_id or camp_id missing")
            return

        query = f"""
            INSERT INTO "{USAGE_TABLE_NAME}"
            (timestamps, learner_id, camp_id, subject, chapter, mobile, type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            timestamp_str,
            str(learner_id),
            str(camp_id),
            subject or "",
            chapter or "",
            mobile or "",
            "🧩 सवाल-जवाब करें",
        )

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, values)
            conn.commit()

        print(f"Usage logged for learner: {learner_id}, camp: {camp_id}")

    except Exception as e:
        print(f"Usage log error: {e}")


def generate_attempt_id_sequence(learner_id: str) -> str:
    query = f"""
        SELECT attempt_id
        FROM "{RESPONSES_TABLE}"
        WHERE learner_id = %s
    """

    seen = set()

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, (learner_id,))
            rows = cur.fetchall()

    for row in rows:
        aid = row.get("attempt_id")
        if aid and str(aid).isdigit():
            seen.add(int(aid))

    return str((max(seen) + 1) if seen else ATTEMPT_SEQUENCE_START)


def fetch_slice(state: str, subject: str, chapter: str) -> List[Dict[str, Any]]:
    state = str(state).strip()
    subject = str(subject).strip()
    chapter = str(chapter).strip()

    query = f"""
        SELECT *
        FROM "{QUESTIONS_TABLE}"
        WHERE state = %s
          AND subject = %s
          AND chapter = %s
        ORDER BY CAST(question_no AS INTEGER)
    """

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, (state, subject, chapter))
            items = cur.fetchall()

    for q in items:
        try:
            q["question_no"] = int(str(q.get("question_no")).strip())
        except Exception:
            q["question_no"] = 0

    items.sort(key=lambda x: x.get("question_no", 0))

    for idx, q in enumerate(items, start=1):
        q["_display_no"] = idx

    print("QUIZ DEBUG filter:", {"state": state, "subject": subject, "chapter": chapter})
    print("QUIZ DEBUG total fetched:", len(items))
    print("QUIZ DEBUG question_nos:", [q["question_no"] for q in items])

    return items


def find_by_qno(items: List[Dict[str, Any]], qno: int) -> Optional[Dict[str, Any]]:
    for q in items:
        if safe_int(q.get("question_no")) == int(qno):
            return q

    if 1 <= int(qno) <= len(items):
        return items[int(qno) - 1]

    return None


def next_unanswered(items: List[Dict[str, Any]], answered_set: set) -> Optional[Dict[str, Any]]:
    for q in items:
        if str(q.get("question_id")) not in answered_set:
            return q
    return None


def save_response(
    learner_id: str,
    attempt_id: str,
    question_id: str,
    selected_value: str,
    question: Dict[str, Any]
) -> bool:
    try:
        is_correct = selected_value == question["right_answer"]
        sk = f"{attempt_id}#{question_id}#{learner_id}"

        ts = datetime.now(IST_TZ)
        timestamp_str = ts.strftime("%Y-%m-%d %H:%M:%S")

        query = f"""
            INSERT INTO "{RESPONSES_TABLE}" (
                learner_id,
                attempt_question_key,
                attempt_id,
                question_id,
                state,
                subject,
                chapter,
                question_no,
                question,
                selected_option,
                right_answer,
                is_correct,
                score,
                timestamp
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            learner_id,
            sk,
            attempt_id,
            str(question_id),
            question["state"],
            question["subject"],
            question["chapter"],
            safe_int(question["question_no"]),
            question["question"],
            selected_value,
            question["right_answer"],
            bool(is_correct),
            Decimal("1.0") if is_correct else Decimal("0.0"),
            timestamp_str
        )

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, values)
            conn.commit()

        return True

    except Exception as e:
        print("save_response error:", e)
        return False


def get_attempt_score_summary(learner_id: str, attempt_id: str) -> Dict[str, Any]:
    query = f"""
        SELECT score
        FROM "{RESPONSES_TABLE}"
        WHERE learner_id = %s
          AND attempt_question_key LIKE %s
    """

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, (learner_id, f"{attempt_id}#%"))
            items = cur.fetchall()

    total_questions = len(items)
    score = 0

    for item in items:
        value = item.get("score", 0)
        try:
            score += float(value)
        except Exception:
            pass

    percentage = round((score / total_questions) * 100) if total_questions > 0 else 0

    return {
        "score": int(score) if float(score).is_integer() else score,
        "max_question": total_questions,
        "percentage": percentage,
    }


def get_correct_count(learner_id: str, attempt_id: str) -> int:
    """Return total correct answers saved so far for this attempt."""
    query = f"""
        SELECT score
        FROM "{RESPONSES_TABLE}"
        WHERE learner_id = %s
          AND attempt_question_key LIKE %s
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, (learner_id, f"{attempt_id}#%"))
            items = cur.fetchall()

    count = 0
    for item in items:
        try:
            count += int(float(item.get("score", 0)))
        except Exception:
            pass
    return count


def fetch_or_submit_quiz(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        state = payload.get("state")
        subject = payload.get("subject")
        chapter = payload.get("chapter")
        learner_id = payload.get("learner_id")
        camp_id = payload.get("camp_id", "")
        mobile = payload.get("mobile", "")

        attempt_id = payload.get("attempt_id") or generate_attempt_id_sequence(learner_id)

        question_no_raw = payload.get("question_no")
        sel_opt_raw = payload.get("selected_option")
        selected_option = str(sel_opt_raw).strip() if sel_opt_raw is not None else None
        submitting = selected_option not in (None, "")

        if not all([state, subject, chapter, learner_id]):
            return {
                "status_code": 400,
                "data": {"message": "❌ Missing: state, subject, chapter, learner_id"}
            }

        _log_usage(
            learner_id=learner_id,
            camp_id=camp_id,
            subject=subject,
            chapter=chapter,
            mobile=mobile
        )

        answered_query = f"""
            SELECT question_id
            FROM "{RESPONSES_TABLE}"
            WHERE learner_id = %s
              AND attempt_question_key LIKE %s
        """

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(answered_query, (learner_id, f"{attempt_id}#%"))
                resp = cur.fetchall()

        answered_qids = {str(i["question_id"]) for i in resp}

        slice_qs = fetch_slice(state, subject, chapter)

        if not slice_qs:
            return {
                "status_code": 404,
                "data": {
                    "message": "❌ No questions found for given state/subject/chapter",
                    "attempt_id": attempt_id,
                    "completed": True,
                    "max_question_no": 0,
                    "total_questions": 0,
                    "remaining_questions": 0
                }
            }

        max_qno = max((safe_int(q.get("question_no")) for q in slice_qs), default=0)
        total_q = len(slice_qs)

        qno = int(question_no_raw) if question_no_raw is not None else None

        if submitting:
            if qno is None:
                return {
                    "status_code": 400,
                    "data": {
                        "message": "❌ question_no is required when submitting an answer",
                        "attempt_id": attempt_id
                    }
                }

            q_cur = find_by_qno(slice_qs, qno)
            if not q_cur:
                return {
                    "status_code": 400,
                    "data": {
                        "message": "❌ Could not find question for question_no",
                        "attempt_id": attempt_id
                    }
                }

            qid = str(q_cur["question_id"])
            is_correct = selected_option == q_cur["right_answer"]

            if not save_response(learner_id, attempt_id, qid, selected_option, q_cur):
                return {
                    "status_code": 500,
                    "data": {
                        "message": "❌ Failed to save response",
                        "attempt_id": attempt_id
                    }
                }

            answered_qids.add(qid)

            # ✅ Count correct answers so far & pick thank_you image
            correct_count = get_correct_count(learner_id, attempt_id)
            thank_you_image_url = (
                get_thank_you_image_url(settings.bucket_name, settings.aws_region, correct_count)
                if is_correct else None
            )

            feedback = {
                "selected_option": selected_option,
                "right_answer": q_cur["right_answer"],
                "is_correct": is_correct,
                "question_id": qid,
                "thank_you_image_url": thank_you_image_url,
            }

            next_q = next_unanswered(slice_qs, answered_qids)

            if not next_q:
                summary = get_attempt_score_summary(learner_id, attempt_id)
                return {
                    "status_code": 200,
                    "data": {
                        "message": "✅ Quiz completed",
                        "attempt_id": attempt_id,
                        "completed": True,
                        "max_question_no": max_qno,
                        "total_questions": total_q,
                        "remaining_questions": 0,
                        "result": summary,
                        "feedback": feedback
                    }
                }

            remaining = max(0, total_q - len(answered_qids) - 1)

            return {
                "status_code": 200,
                "data": {
                    "message": "✅ Answer saved, next question fetched",
                    "attempt_id": attempt_id,
                    "completed": False,
                    "state": next_q["state"],
                    "subject": next_q["subject"],
                    "chapter": next_q["chapter"],
                    "question_list": {
                        "question_id": next_q["question_id"],
                        "question_no": safe_int(next_q["question_no"]),
                        "display_no": next_q.get("_display_no"),
                        "question": next_q["question"],
                        "option_1": next_q["option_1"],
                        "option_2": next_q["option_2"],
                        "option_3": next_q["option_3"],
                        "option_4": next_q["option_4"],
                        "right_answer": next_q["right_answer"]
                    },
                    "max_question_no": max_qno,
                    "total_questions": total_q,
                    "remaining_questions": remaining,
                    "feedback": feedback
                }
            }

        next_q = next_unanswered(slice_qs, answered_qids)
        if not next_q:
            summary = get_attempt_score_summary(learner_id, attempt_id)
            return {
                "status_code": 200,
                "data": {
                    "message": "✅ No more questions in this attempt",
                    "attempt_id": attempt_id,
                    "completed": True,
                    "max_question_no": max_qno,
                    "total_questions": total_q,
                    "remaining_questions": 0,
                    "result": summary
                }
            }

        selected_already_answered = str(next_q["question_id"]) in answered_qids
        remaining = max(0, total_q - len(answered_qids) - (0 if selected_already_answered else 1))

        return {
            "status_code": 200,
            "data": {
                "message": "✅ Quiz question fetched",
                "attempt_id": attempt_id,
                "completed": False,
                "state": next_q["state"],
                "subject": next_q["subject"],
                "chapter": next_q["chapter"],
                "question_list": {
                    "question_id": next_q["question_id"],
                    "question_no": safe_int(next_q["question_no"]),
                    "display_no": next_q.get("_display_no"),
                    "question": next_q["question"],
                    "option_1": next_q["option_1"],
                    "option_2": next_q["option_2"],
                    "option_3": next_q["option_3"],
                    "option_4": next_q["option_4"],
                    "right_answer": next_q["right_answer"]
                },
                "max_question_no": max_qno,
                "total_questions": total_q,
                "remaining_questions": remaining
            }
        }

    except Exception as e:
        return {
            "status_code": 500,
            "data": {
                "message": "Server Error",
                "error": str(e)
            }
        }