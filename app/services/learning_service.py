from typing import Optional, Dict, Any
import psycopg2
import psycopg2.extras

from app.config import get_settings

settings = get_settings()

CHAPTER_TABLE = "_2025_prayaas_subject_chapter"

# ===================== DB CONNECTION =====================

def get_db_connection():
    try:
        print("DB CONNECT:", settings.pg_host, settings.pg_port)

        return psycopg2.connect(
            host=settings.pg_host,
            port=settings.pg_port,
            user=settings.pg_user,
            password=settings.pg_password,
            dbname=settings.pg_database
        )
    except Exception as e:
        print("DB CONNECTION ERROR:", str(e))
        raise e


# ===================== MAIN API =====================

def fetch_phases_or_chapters(
    state: str,
    subject: str,
    phase: Optional[str] = None
) -> Dict[str, Any]:

    state = (state or "").strip()
    subject = (subject or "").strip()
    phase = (phase or "").strip()

    if not state:
        return {"status_code": 400, "data": {"message": "⚠️ Missing 'state' parameter"}}

    if not subject:
        return {"status_code": 400, "data": {"message": "⚠️ Missing 'subject' parameter"}}

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

                # ================= PHASE LIST =================
                if not phase:
                    query = f"""
                        SELECT DISTINCT phase
                        FROM "{CHAPTER_TABLE}"
                        WHERE LOWER(TRIM(state)) = LOWER(TRIM(%s))
                          AND LOWER(TRIM(subject)) = LOWER(TRIM(%s))
                        ORDER BY phase
                    """

                    cur.execute(query, (state, subject))
                    items = cur.fetchall()

                    if not items:
                        return {
                            "status_code": 404,
                            "data": {
                                "message": f"❌ No phases found",
                                "total_phases": 0
                            }
                        }

                    phase_list = {
                        f"phase{i+1}": item["phase"]
                        for i, item in enumerate(items)
                        if item.get("phase")
                    }

                    return {
                        "status_code": 200,
                        "data": {
                            "total_phases": len(phase_list),
                            **phase_list
                        }
                    }

                # ================= CHAPTER LIST =================
                query = f"""
                    SELECT DISTINCT chapter, chap_id
                    FROM "{CHAPTER_TABLE}"
                    WHERE LOWER(TRIM(state)) = LOWER(TRIM(%s))
                      AND LOWER(TRIM(subject)) = LOWER(TRIM(%s))
                      AND LOWER(TRIM(phase)) = LOWER(TRIM(%s))
                """

                cur.execute(query, (state, subject, phase))
                items = cur.fetchall()

                if not items:
                    return {
                        "status_code": 404,
                        "data": {
                            "message": f"❌ No chapters found",
                            "total_chapters": 0
                        }
                    }

                # Sort by chap_id safely
                def safe_id(x):
                    try:
                        return float(x.get("chap_id", 999))
                    except:
                        return 999

                items.sort(key=safe_id)

                chapter_list = {
                    f"chapter{i+1}": item["chapter"]
                    for i, item in enumerate(items)
                    if item.get("chapter")
                }

                return {
                    "status_code": 200,
                    "data": {
                        "total_chapters": len(chapter_list),
                        **chapter_list
                    }
                }

    except Exception as e:
        print("fetch_phases_or_chapters error:", str(e))
        return {
            "status_code": 500,
            "data": {
                "message": "⚠️ Internal error occurred",
                "error": str(e)
            }
        }


# ===================== EXTRA APIs =====================

def fetch_subject_chapter_rows(state: str):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

                query = f"""
                    SELECT state, subject, phase, chapter
                    FROM "{CHAPTER_TABLE}"
                    WHERE state = %s
                    ORDER BY subject, phase, chapter
                """

                cur.execute(query, (state,))
                rows = cur.fetchall()

                return {
                    "status_code": 200,
                    "data": rows
                }

    except Exception as e:
        return {
            "status_code": 500,
            "data": {"error": str(e)}
        }


def fetch_quiz_questions(state: str, subject: str, chapter: str):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

                query = """
                    SELECT
                        question_id,
                        question_no,
                        question,
                        option_1,
                        option_2,
                        option_3,
                        option_4,
                        right_answer,
                        chapter,
                        subject,
                        state
                    FROM _2025_prayaas_quiz_questions
                    WHERE LOWER(TRIM(state)) = LOWER(TRIM(%s))
                      AND LOWER(TRIM(subject)) = LOWER(TRIM(%s))
                      AND LOWER(TRIM(chapter)) = LOWER(TRIM(%s))
                    ORDER BY question_no
                """

                cur.execute(query, (state, subject, chapter))
                rows = cur.fetchall()

                return {
                    "status_code": 200,
                    "data": rows
                }

    except Exception as e:
        return {
            "status_code": 500,
            "data": {"error": str(e)}
        }