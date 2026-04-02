from typing import Dict, Any


def generate_chat_response(message: str, learner_context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    learner_context = learner_context or {}
    clean_message = (message or "").strip().lower()
    first_name = learner_context.get("first_name", "Learner")

    if not clean_message:
        return {
            "reply": "Please enter a message.",
            "next_action": "wait_for_input",
        }

    if clean_message in ["hi", "hello", "hey"]:
        return {
            "reply": f"Hello {first_name}, welcome to PragatiDidi. How can I help you today?",
            "next_action": "wait_for_input",
        }

    if "subject" in clean_message:
        subjects = []
        for i in range(1, 8):
            value = learner_context.get(f"subject{i}")
            if value:
                subjects.append(value)

        if subjects:
            subjects_text = ", ".join(subjects)
            return {
                "reply": f"Your available subjects are: {subjects_text}",
                "next_action": "wait_for_input",
            }

        return {
            "reply": "No subjects were found for your profile.",
            "next_action": "wait_for_input",
        }

    if "help" in clean_message:
        return {
            "reply": "You can ask about your subjects, learning material, or onboarding details.",
            "next_action": "wait_for_input",
        }

    return {
        "reply": f"You said: {message}",
        "next_action": "wait_for_input",
    }