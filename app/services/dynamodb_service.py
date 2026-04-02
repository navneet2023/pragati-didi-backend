from typing import Optional, List, Dict, Any

import psycopg2
import psycopg2.extras

from app.config import get_settings

settings = get_settings()

LEARNER_TABLE = "_2025_learner_details"


def get_db_connection():
    return psycopg2.connect(
        host=settings.pg_host,
        port=settings.pg_port,
        user=settings.pg_user,
        password=settings.pg_password,
        dbname=settings.pg_database
    )


def get_learner_by_id_and_camp(learner_id: str, camp_id: str) -> Optional[Dict[str, Any]]:
    try:
        query = f"""
            SELECT *
            FROM "{LEARNER_TABLE}"
            WHERE learner_id = %s
              AND camp_id = %s
            LIMIT 1
        """

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (learner_id, camp_id))
                row = cur.fetchone()

        return dict(row) if row else None

    except Exception as e:
        print(f"[PostgreSQL get_learner_by_id_and_camp] {e}")
        return None


def get_learners_by_learner_id(learner_id: str) -> Optional[List[Dict[str, Any]]]:
    try:
        query = f"""
            SELECT *
            FROM "{LEARNER_TABLE}"
            WHERE learner_id = %s
        """

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, (learner_id,))
                rows = cur.fetchall()

        return [dict(row) for row in rows]

    except Exception as e:
        print(f"[PostgreSQL get_learners_by_learner_id] {e}")
        return None