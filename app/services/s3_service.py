import json
import datetime
from typing import Dict, Any, Optional

import boto3

from app.config import get_settings

settings = get_settings()

session = boto3.Session(region_name=settings.aws_region)
s3_client = session.client("s3")


def log_json_to_s3(payload: Dict[str, Any], prefix: str = "fastapi-logs") -> Optional[str]:
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        key = f"{prefix}/event_{ts}.json"

        s3_client.put_object(
            Bucket=settings.bucket_name,
            Key=key,
            Body=json.dumps(payload, indent=2, ensure_ascii=False),
            ContentType="application/json",
        )
        return key
    except Exception as e:
        print(f"[S3 log] {e}")
        return None


def fetch_pdf_bytes(bucket: str, key: str) -> bytes:
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()