from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from database import get_connection
from notifications import send_notification


def setup_notification_log():
    connection = get_connection()
    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS notification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_type TEXT NOT NULL,
                item_id INTEGER NOT NULL,
                notification_date TEXT NOT NULL,
                UNIQUE(item_type, item_id, notification_date)
            )
        """)
        connection.commit()
    finally:
        connection.close()


def already_notified(item_type, item_id):
    today = datetime.now().strftime("%Y-%m-%d")
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT id FROM notification_log
            WHERE item_type = ? AND item_id = ? AND notification_date = ?
        """, (item_type, item_id, today)).fetchone()
        return row is not None
    finally:
        connection.close()


def mark_notified(item_type, item_id):
    today = datetime.now().strftime("%Y-%m-%d")
    connection = get_connection()
    try:
        connection.execute("""
            INSERT OR IGNORE INTO notification_log
            (item_type, item_id, notification_date) VALUES (?, ?, ?)
        """, (item_type, item_id, today))
        connection.commit()
    finally:
        connection.close()


def check_deadlines():
    print("StudyFlow AI checking deadlines...")
    today = datetime.now().date()
    connection = get_connection()
    try:
        assignments = connection.execute(
            "SELECT * FROM assignments WHERE completed = 0"
        ).fetchall()
        for task in assignments:
            try:
                deadline = datetime.strptime(task["deadline"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                print("Skipping assignment with invalid deadline:", task["title"])
                continue

            days_left = (deadline - today).days
            priority = str(task["priority"] or "LOW").upper()

            if priority == "CRITICAL" and days_left <= 0:
                if already_notified("critical_assignment", task["id"]):
                    continue
                due_text = "is due today" if days_left == 0 else "is overdue"
                body = (
                    f"🔴 CRITICAL: {task['title']} {due_text}. "
                    f"Subject: {task['subject']}. "
                    f"Estimated work: {task['estimated_hours']} hour(s). "
                    "Please prioritize this task now."
                )
                if send_notification(
                    "StudyFlow AI — Critical Assignment Alert",
                    body,
                    category="assignment",
                ):
                    mark_notified("critical_assignment", task["id"])
                    print("Critical assignment alert sent:", task["title"])
            elif days_left in (0, 1):
                if already_notified("assignment", task["id"]):
                    continue
                timing = "is due today" if days_left == 0 else "is due tomorrow"
                body = (
                    f"🔔 {task['title']} {timing}. Priority: {priority}. "
                    f"Recommended study time: {task['estimated_hours']} hours."
                )
                if send_notification("StudyFlow AI — Assignment Reminder", body, "assignment"):
                    mark_notified("assignment", task["id"])

        exams = connection.execute(
            "SELECT * FROM exams WHERE completed = 0"
        ).fetchall()
        for exam in exams:
            try:
                exam_date = datetime.strptime(exam["exam_date"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                print("Skipping exam with invalid date:", exam["subject"])
                continue
            days_left = (exam_date - today).days
            if 0 <= days_left <= 3 and not already_notified("exam", exam["id"]):
                if days_left <= 1:
                    title = "StudyFlow AI — CRITICAL Exam Alert"
                    when = "today" if days_left == 0 else "tomorrow"
                    body = (
                        f"🔴 URGENT: {exam['subject']} exam is {when}. "
                        f"Preparation required: {exam['preparation_hours']} hours. "
                        "Review your important topics now."
                    )
                else:
                    title = "StudyFlow AI — Exam Reminder"
                    body = (
                        f"🟠 {exam['subject']} exam is in {days_left} days. "
                        f"Preparation required: {exam['preparation_hours']} hours."
                    )
                if send_notification(title, body, category="exam"):
                    mark_notified("exam", exam["id"])
                    print("Exam notification sent:", exam["subject"])

        goals = connection.execute(
            "SELECT * FROM goals WHERE completed = 0"
        ).fetchall()
        for goal in goals:
            if already_notified("goal", goal["id"]):
                continue
            body = (
                f"🎯 Reminder: Continue working on your goal "
                f"'{goal['title']}'. Stay consistent!"
            )
            if send_notification("StudyFlow AI — Goal Reminder", body, "goal"):
                mark_notified("goal", goal["id"])
                print("Goal notification sent:", goal["title"])

        print("Deadline check completed.")
    except Exception as error:
        print("Deadline checker error:", type(error).__name__, str(error))
    finally:
        connection.close()


def start_scheduler():
    setup_notification_log()
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(
        check_deadlines,
        "interval",
        minutes=5,
        id="studyflow_deadline_checker",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=120,
    )
    scheduler.start()
    print("StudyFlow AI scheduler started; checking every 5 minutes.")
    scheduler.add_job(
        check_deadlines,
        "date",
        run_date=datetime.now(),
        id="studyflow_startup_check",
        replace_existing=True,
    )
    return scheduler
