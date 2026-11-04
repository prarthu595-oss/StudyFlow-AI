import json
import os
from datetime import datetime
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, messaging
from database import get_connection


def create_notification(task):
    priority = str(task.get("priority", "LOW")).upper()
    title = task.get("title", "Study Task")
    subject = task.get("subject", "")
    if priority == "CRITICAL":
        body = f"🔴 URGENT: {title} for {subject} needs your attention today."
    elif priority == "HIGH":
        body = f"🟠 HIGH PRIORITY: Start studying {title} soon."
    elif priority == "MEDIUM":
        body = f"🟡 REMINDER: You have upcoming {title} preparation."
    else:
        body = f"🔵 StudyFlow reminder: Keep progressing on {title}."
    return {
        "title": "StudyFlow AI",
        "message": body,
        "priority": priority,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def initialize_firebase():
    if firebase_admin._apps:
        return True
    raw = os.getenv("FIREBASE_SERVICE_ACCOUNT", "").strip()
    if raw:
        try:
            firebase_admin.initialize_app(credentials.Certificate(json.loads(raw)))
            print("Firebase initialized from environment credentials.")
            return True
        except Exception as error:
            print("Firebase configuration error:", type(error).__name__, str(error))
            return False

    local_file = Path(__file__).resolve().parent / "firebase-service-account.json"
    if local_file.is_file():
        try:
            firebase_admin.initialize_app(credentials.Certificate(str(local_file)))
            print("Firebase initialized from local credentials file.")
            return True
        except Exception as error:
            print("Firebase local configuration error:", type(error).__name__, str(error))
            return False

    print("Firebase is not configured. Set FIREBASE_SERVICE_ACCOUNT in Render.")
    return False


def send_notification(title, body, category=None):
    connection = get_connection()
    try:
        if category in ("assignment", "exam", "goal"):
            settings = connection.execute(
                "SELECT assignment_notifications, exam_notifications, goal_notifications "
                "FROM app_settings WHERE id = 1"
            ).fetchone()
            if settings:
                column = {
                    "assignment": "assignment_notifications",
                    "exam": "exam_notifications",
                    "goal": "goal_notifications",
                }[category]
                if not settings[column]:
                    print(f"Notifications disabled for {category}.")
                    return False

        device = connection.execute(
            "SELECT token FROM devices ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not device:
            print("No registered Firebase device token found.")
            return False
        if not initialize_firebase():
            return False

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=device["token"],
        )
        message_id = messaging.send(message)
        print("Firebase push notification sent:", message_id)
        return True
    except Exception as error:
        print("Firebase notification error:", type(error).__name__, str(error))
        return False
    finally:
        connection.close()
