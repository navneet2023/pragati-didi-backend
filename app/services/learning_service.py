from typing import Optional, Dict, Any, List
from sqlalchemy import text          # ✅ REQUIRED
from app.db import SessionLocal      # ✅ REQUIRED

import psycopg2
import psycopg2.extras

from app.config import get_settings

settings = get_settings()

CHAPTER_TABLE = "_2025_prayaas_subject_chapter"


def get_db_connection():
    return psycopg2.connect(
        host=settings.pg_host,
        port=settings.pg_port,
        user=settings.pg_user,
        password=settings.pg_password,
        dbname=settings.pg_database
    )


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
        # Case 1: no phase -> return phases
        if not phase:
            query = f"""
                SELECT phase
                FROM "{CHAPTER_TABLE}"
                WHERE state = %s
                  AND subject = %s
            """

            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(query, (state, subject))
                    items = cur.fetchall()

            if not items:
                return {
                    "status_code": 404,
                    "data": {
                        "message": f"❌ No data found for State: {state}, Subject: {subject}",
                        "total_phases": 0,
                    },
                }

            unique_phases = set()
            for item in items:
                p = item.get("phase")
                if p:
                    unique_phases.add(p)

            sorted_phases = sorted(unique_phases)

            phase_list = {
                f"phase{i}": phase_name
                for i, phase_name in enumerate(sorted_phases, 1)
            }

            return {
                "status_code": 200,
                "data": {
                    "total_phases": len(phase_list),
                    **phase_list,
                },
            }

        # Case 2: phase provided -> return chapters
        query = f"""
            SELECT chapter, chap_id
            FROM "{CHAPTER_TABLE}"
            WHERE state = %s
              AND subject = %s
              AND phase = %s
        """

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (state, subject, phase))
                items = cur.fetchall()

        if not items:
            return {
                "status_code": 404,
                "data": {
                    "message": f"❌ No chapters found for State: {state}, Subject: {subject}, Phase: {phase}",
                    "total_chapters": 0,
                },
            }

        unique_chapters = {}
        for item in items:
            name = item.get("chapter")
            raw_id = item.get("chap_id", "999.0")

            try:
                c_id = float(raw_id)
            except (ValueError, TypeError):
                c_id = 999.0

            if name:
                if name not in unique_chapters or c_id < unique_chapters[name]:
                    unique_chapters[name] = c_id

        sorted_chapters = sorted(unique_chapters.items(), key=lambda x: x[1])

        chapter_list = {
            f"chapter{i}": name
            for i, (name, _) in enumerate(sorted_chapters, 1)
        }

        return {
            "status_code": 200,
            "data": {
                "total_chapters": len(chapter_list),
                **chapter_list,
            },
        }

    except Exception as e:
        print("fetch_phases_or_chapters error:", str(e))
        return {
            "status_code": 500,
            "data": {
                "message": "⚠️ Internal error occurred",
                "error": str(e),
            },
        }
    
def fetch_subject_chapter_rows(state: str):
    db = SessionLocal()

    try:
        query = text("""
            SELECT
                state,
                subject,
                phase,
                chapter
            FROM _2025_prayaas_subject_chapter
            WHERE state = :state
            ORDER BY subject, phase, chapter
        """)

        result = db.execute(query, {"state": state})
        rows = result.mappings().all()

        return {
            "status_code": 200,
            "data": [dict(row) for row in rows]
        }

    except Exception as e:
        return {
            "status_code": 500,
            "data": {"error": str(e)}
        }

    finally:
        db.close()


def fetch_quiz_questions(state: str, subject: str, chapter: str):
    db = SessionLocal()

    try:
        query = text("""
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
            WHERE LOWER(TRIM(state)) = LOWER(TRIM(:state))
              AND LOWER(TRIM(subject)) = LOWER(TRIM(:subject))
              AND LOWER(TRIM(chapter)) = LOWER(TRIM(:chapter))
            ORDER BY question_no
        """)

        result = db.execute(query, {
            "state": state,
            "subject": subject,
            "chapter": chapter
        })
        rows = result.mappings().all()

        return {
            "status_code": 200,
            "data": [dict(row) for row in rows]
        }

    except Exception as e:
        return {
            "status_code": 500,
            "data": {"error": str(e)}
        }

    finally:
        db.close()