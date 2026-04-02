from datetime import datetime
from typing import Dict, Any
import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

TABLE_NAME = '"_2025_learner_usages_status"'


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "pgadmin"),
        dbname=os.getenv("POSTGRES_DATABASE", "postgres"),
    )


def log_learning_action(payload: Dict[str, Any]) -> Dict[str, Any]:
    item = {
        "timestamps": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "learner_id": str(payload.get("learner_id", "")),
        "camp_id": str(payload.get("camp_id", "")),
        "mobile": str(payload.get("mobile", "")),
        "subject": str(payload.get("subject", "")),
        "chapter": str(payload.get("chapter", "")),
        "type": str(payload.get("action_type", "")),
    }

    print("LOG ACTION ITEM:", item)

    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        insert_sql = f"""
            INSERT INTO {TABLE_NAME}
            (timestamps, learner_id, camp_id, mobile, subject, chapter, type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        cur.execute(
            insert_sql,
            (
                item["timestamps"],
                item["learner_id"],
                item["camp_id"],
                item["mobile"],
                item["subject"],
                item["chapter"],
                item["type"],
            ),
        )

        conn.commit()
        print("LOG ACTION SAVED")

        return {"message": "Action logged successfully"}

    except Exception as e:
        if conn:
            conn.rollback()

        print("LOG ACTION ERROR:", str(e))
        return {
            "message": "Action log failed",
            "error": str(e),
        }

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()