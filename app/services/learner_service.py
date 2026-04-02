from typing import Optional, Dict, Any, List
from sqlalchemy import text
from app.db import SessionLocal

SUBJECT_FIELDS = [f"subject{i}" for i in range(1, 8)]


def extract_first_name(full_name: Optional[str]) -> str:
    if not full_name:
        return ""
    parts = str(full_name).strip().split()
    return parts[0] if parts else ""


def build_subject_map_from_items(items: List[Dict[str, Any]]) -> Dict[str, str]:
    collected = []

    for item in items or []:
        for field in SUBJECT_FIELDS:
            value = item.get(field)
            if value is not None:
                value = str(value).strip()
            if value:
                collected.append(value)

    seen = set()
    unique_subjects = [s for s in collected if not (s in seen or seen.add(s))]
    return {f"subject{i+1}": subject for i, subject in enumerate(unique_subjects)}


# ✅ MAIN VERIFY FUNCTION (PostgreSQL ONLY)
def verify_learner_logic(learner_id: str = "", camp_id: str = "") -> Dict[str, Any]:
    learner_id = (learner_id or "").strip()
    camp_id = (camp_id or "").strip()

    db = SessionLocal()

    try:
        # 🔥 Case 1: learner_id + camp_id
        if learner_id and camp_id:
            query = text("""
                SELECT * 
                FROM "_2025_learner_details"
                WHERE LOWER(learner_id) = LOWER(:lid)
                AND LOWER(camp_id) = LOWER(:cid)
            """)

            result = db.execute(query, {"lid": learner_id, "cid": camp_id}).mappings().first()

            if not result:
                return {"status_code": 404, "data": {"message": "Learner not found"}}

            item = dict(result)

            learner_name = item.get("learner_name", "")
            first_name = extract_first_name(learner_name)
            subject_map = build_subject_map_from_items([item])

            return {
                "status_code": 200,
                "data": {
                    "message": "Learner found",
                    "state": item.get("state", ""),
                    "learner_name": learner_name,
                    "first_name": first_name,
                    "camp_id": item.get("camp_id", ""),
                    "prerak_id": item.get("prerak_id", ""),
                    "emp_type": item.get("emp_type", ""),
                    "learner_mobile_number": item.get("learner_mobile_number", ""),
                    **subject_map,
                },
            }

        # 🔥 Case 2: only learner_id
        if learner_id:
            query = text("""
                SELECT * 
                FROM "_2025_learner_details"
                WHERE LOWER(learner_id) = LOWER(:lid)
            """)

            results = db.execute(query, {"lid": learner_id}).mappings().all()

            if not results:
                return {"status_code": 404, "data": {"message": "Learner not found"}}

            items = [dict(row) for row in results]

            primary_item = items[0]
            learner_name = primary_item.get("learner_name", "")
            first_name = extract_first_name(learner_name)
            subject_map = build_subject_map_from_items(items)

            return {
                "status_code": 200,
                "data": {
                    "message": "Learner found",
                    "state": primary_item.get("state", ""),
                    "learner_name": learner_name,
                    "first_name": first_name,
                    "camp_id": primary_item.get("camp_id", ""),
                    "prerak_id": primary_item.get("prerak_id", ""),
                    "emp_type": primary_item.get("emp_type", ""),
                    "learner_mobile_number": primary_item.get("learner_mobile_number", ""),
                    **subject_map,
                },
            }

        return {
            "status_code": 400,
            "data": {"message": "Please provide learner_id to continue."},
        }

    except Exception as e:
        return {
            "status_code": 500,
            "data": {"error": str(e)}
        }

    finally:
        db.close()


# ✅ GET ALL LEARNERS BY CAMP
def get_learners_by_camp_logic(camp_id: str) -> Dict[str, Any]:
    db = SessionLocal()

    try:
        query = text("""
            SELECT
                learner_id,
                camp_id,
                learner_mobile_number,
                learner_name,
                prerak_id,
                prerak_mobile_number,
                prerak_name,
                pc_name,
                district,
                ip_name,
                state,
                subject1,
                subject2,
                subject3,
                subject4,
                subject5,
                subject6,
                subject7
            FROM "_2025_learner_details"
            WHERE LOWER(camp_id) = LOWER(:camp_id)
            ORDER BY learner_name
        """)

        result = db.execute(query, {"camp_id": camp_id.strip()})
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