from typing import Dict, Any


def parse_turn_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    contact = payload.get("contact", {}) or {}
    message = payload.get("message", {}) or {}

    return {
        "channel": "turn_io",
        "wa_id": contact.get("wa_id", ""),
        "name": contact.get("name", ""),
        "text": message.get("text", {}).get("body", "") if isinstance(message.get("text"), dict) else "",
        "raw_payload": payload,
    }


def build_turn_reply(text: str) -> Dict[str, Any]:
    return {
        "messages": [
            {
                "type": "text",
                "text": text,
            }
        ]
    }