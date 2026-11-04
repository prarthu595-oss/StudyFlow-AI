import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from pathlib import Path
from database import initialize_database, get_connection
from planner import generate_study_plan, add_goals_to_schedule
from priority_engine import calculate_priority
from scheduler import start_scheduler
from apscheduler.schedulers.background import BackgroundScheduler
from notifications import send_notification
from ai_engine import get_ai_recommendation ,get_ai_priority_order

app = Flask(__name__)

import os
import json

# Initialize database
initialize_database()

# ---------------- HOME PAGE ----------------
@app.route("/")
def home():
    connection = get_connection()

    profile = connection.execute(
        "SELECT name FROM student_profile WHERE id = 1"
    ).fetchone()

    connection.close()

    student_name = profile["name"] if profile else "Student"

    return render_template(
        "index.html",
        student_name=student_name
    )

# ---------------- ASSIGNMENTS PAGE ----------------
@app.route("/assignments", methods=["GET", "POST"])
def assignments():

    # When user clicks "Add Assignment"
    if request.method == "POST":

        # Get data from the form
        title = request.form.get("title")
        subject = request.form.get("subject")
        deadline = request.form.get("deadline")
        estimated_hours = request.form.get("estimated_hours")

        # Calculate priority
        priority, score = calculate_priority(
            deadline,
            float(estimated_hours)
        )

        # Connect to database
        connection = get_connection()

        # Save assignment
        connection.execute("""
            INSERT INTO assignments
            (
                title,
                subject,
                deadline,
                estimated_hours,
                priority,
                priority_score
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            title,
            subject,
            deadline,
            float(estimated_hours),
            priority,
            score
        ))

        # Save changes
        connection.commit()

        # Close database
        connection.close()

        # Go back to assignments page
        return redirect(url_for("assignments"))

    # ---------------- GET ALL ASSIGNMENTS ----------------

    connection = get_connection()

    assignments_list = connection.execute("""
        SELECT *
        FROM assignments
        WHERE completed=0
        ORDER BY priority_score DESC, deadline ASC
    """).fetchall()

    connection.close()

    # Send assignments to HTML page
    return render_template(
        "assignments.html",
        assignments=assignments_list
    )
    
@app.route("/complete-assignment/<int:assignment_id>", methods=["POST"])
def complete_assignment(assignment_id):
    connection = get_connection()

    connection.execute(
        """
        UPDATE assignments
        SET completed = 1
        WHERE id = ?
        """,
        (assignment_id,)
    )

    connection.commit()
    connection.close()

    return redirect("/plan")

@app.route("/exams", methods=["GET", "POST"])
def exams():

    connection = get_connection()

    if request.method == "POST":

        subject = request.form.get("subject")
        exam_date = request.form.get("exam_date")
        preparation_hours = request.form.get("preparation_hours")
        syllabus = request.form.get("syllabus")

        if subject and exam_date and preparation_hours:
            connection.execute(
                """
                INSERT INTO exams
                (subject, exam_date, preparation_hours, syllabus)
                VALUES (?, ?, ?, ?)
                """,
                (
                    subject,
                    exam_date,
                    float(preparation_hours),
                    syllabus
                )
            )

            connection.commit()

        connection.close()

        return redirect(url_for("exams"))

    exams_list = connection.execute(
        """
        SELECT *
        FROM exams
        WHERE completed = 0
        ORDER BY exam_date ASC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "exams.html",
        exams=exams_list
    )
    
@app.route("/complete-exam/<int:exam_id>", methods=["POST"])
def complete_exam(exam_id):
    connection = get_connection()

    connection.execute(
        """
        UPDATE exams
        SET completed = 1
        WHERE id = ?
        """,
        (exam_id,)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("plan"))
    
@app.route("/plan")
def plan():

    connection = get_connection()

    # -------------------------------
    # GET ASSIGNMENTS
    # -------------------------------

    assignment_rows = connection.execute("""
    SELECT *
    FROM assignments
    WHERE completed=0
    ORDER BY priority_score DESC, deadline ASC
    """).fetchall()
    
    # -------------------------------
    # GET EXAMS
    # -------------------------------

    exam_rows = connection.execute("""
        SELECT *
        FROM exams
        WHERE completed = 0
        ORDER BY exam_date ASC
    """).fetchall()
    
    # GET GOALS
    goal_rows = connection.execute("""
       SELECT *
       FROM goals
       ORDER BY id ASC
    """).fetchall()
    
    # GET TIMETABLE
    timetable_rows = connection.execute("""
        SELECT *
        FROM timetable
        ORDER BY day, start_time
    """).fetchall()

    connection.close()

    # Convert database rows to dictionaries
    assignments = [
        dict(row) for row in assignment_rows
    ]

    print("ASSIGNMENTS SENT TO PLANNER:", assignments)
    
    print(
    "PLANNER ASSIGNMENT TITLES:",
    [(a["title"], a["estimated_hours"], a["completed"]) for a in assignments]
    )
    
    exams = [
        dict(row) for row in exam_rows
    ]
    
    goals = [
        dict(row) for row in goal_rows
    ]
    
    timetable = [
    dict(row) for row in timetable_rows
    ]

    print("TIMETABLE:", timetable)

    # -------------------------------
    # GENERATE AI STUDY PLAN
    # -------------------------------

    schedule = generate_study_plan(
        assignments,
        exams,
        available_hours=30,
        timetable=timetable
    )
    
    print("GOALS COUNT:", len(goals))
    print("GOALS BEFORE ADD:", goals)
        
    schedule = add_goals_to_schedule(
       schedule,
       goals,
       available_hours=30,
       timetable=timetable
    )
    
    # -------------------------------
    # AI STUDY RECOMMENDATION
    # -------------------------------

    ai_tasks = []

    for assignment in assignments:
        ai_tasks.append({
            "type": "Assignment",
            "title": assignment.get("title"),
            "deadline": assignment.get("deadline"),
            "estimated_hours": assignment.get("estimated_hours")
        })

    for exam in exams:
        ai_tasks.append({
            "type": "Exam",
            "title": exam.get("subject"),
            "exam_date": exam.get("exam_date"),
            "preparation_hours": exam.get("preparation_hours")
        })

    for goal in goals:
        ai_tasks.append({
            "type": "Goal",
            "title": goal.get("title"),
            "target_hours": goal.get("target_hours")
        })

    try:
        ai_recommendation = get_ai_recommendation(ai_tasks)
    except Exception as e:
        print("AI RECOMMENDATION ERROR:", e)
        ai_recommendation = "AI recommendation is temporarily unavailable."

    print("FINAL SCHEDULE:", schedule)

    return render_template(
    "plan.html",
    schedule=schedule,
ai_recommendation=ai_recommendation
)

    
@app.route("/ai-recommendation")
def ai_recommendation():

    connection = get_connection()

    assignment_rows = connection.execute("""
        SELECT *
        FROM assignments
        WHERE completed = 0
        ORDER BY priority_score DESC, deadline ASC
    """).fetchall()

    exam_rows = connection.execute("""
        SELECT *
        FROM exams
        WHERE completed = 0
        ORDER BY exam_date ASC
    """).fetchall()

    goal_rows = connection.execute("""
        SELECT *
        FROM goals
        ORDER BY id ASC
    """).fetchall()

    connection.close()

    assignments = [dict(row) for row in assignment_rows]
    exams = [dict(row) for row in exam_rows]
    goals = [dict(row) for row in goal_rows]

    ai_tasks = []

    for assignment in assignments:
        ai_tasks.append({
            "type": "Assignment",
            "title": assignment.get("title"),
            "deadline": assignment.get("deadline"),
            "estimated_hours": assignment.get("estimated_hours"),
            "priority": assignment.get("priority"),
            "priority_score": assignment.get("priority_score")
        })

    for exam in exams:
        ai_tasks.append({
            "type": "Exam",
            "title": exam.get("subject"),
            "exam_date": exam.get("exam_date"),
            "preparation_hours": exam.get("preparation_hours"),
            "priority": exam.get("priority"),
            "priority_score": exam.get("priority_score")
        })

    for goal in goals:
        ai_tasks.append({
            "type": "Goal",
            "title": goal.get("title"),
            "target_hours": goal.get("target_hours")
        })

    try:
        recommendation = get_ai_recommendation(ai_tasks)
    except Exception as e:
        print("AI RECOMMENDATION ERROR:", e)
        recommendation = "AI recommendation is temporarily unavailable."

    return jsonify({
        "recommendation": recommendation
    })
    
@app.route("/save-token", methods=["POST"])
def save_token():
    data = request.get_json()

    token = data.get("token")

    if not token:
        return jsonify({
            "success": False,
            "message": "Token missing"
        }), 400

    connection = get_connection()

    try:
        connection.execute("DELETE FROM devices")

        connection.execute(
          "INSERT INTO devices (token) VALUES (?)",
           (token,)
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Device registered successfully"
        })

    except Exception as error:
        print("Token save error:", error)

        return jsonify({
            "success": False,
            "message": "Could not save token"
        }), 500

    finally:
        connection.close()

@app.route("/test-notification")
def test_notification():
    success = send_notification(
        "StudyFlow AI",
        "🔔 Test notification — your StudyFlow AI push notifications are working!"
    )
    if success:
        return jsonify({"success": True, "message": "Test notification sent."})
    return jsonify({
        "success": False,
        "message": "Notification not sent. Check Firebase credentials and registered device token."
    }), 503

@app.route("/firebase-messaging-sw.js")
def firebase_messaging_sw():
    sw_path = Path(__file__).resolve().parent / "firebase-messaging-sw.js"
    return send_file(sw_path, mimetype="application/javascript")
  
@app.route("/goals", methods=["GET", "POST"])
def goals():

    connection = get_connection()

    if request.method == "POST":
        title = request.form.get("title")
        target_hours = request.form.get("target_hours")

        if title and target_hours:
            connection.execute(
                """
                INSERT INTO goals (title, target_hours)
                VALUES (?, ?)
                """,
                (title, float(target_hours))
            )
            connection.commit()

        connection.close()

        return redirect("/goals")

    goals_list = connection.execute(
        """
        SELECT *
        FROM goals
        ORDER BY id DESC
        """
    ).fetchall()
    
    print("GOALS FROM DATABASE:", [dict(g) for g in goals_list])

    connection.close()

    return render_template(
        "goals.html",
        goals=goals_list
    )

@app.route("/ai-assistant", methods=["GET", "POST"])
def ai_assistant():
    answer = ""
    question = ""

    if request.method == "POST":
        question = request.form.get("question", "").strip()

        if question:
            connection = get_connection()

            try:
                assignments = connection.execute("""
                    SELECT title, subject, deadline,
                           estimated_hours, priority
                    FROM assignments
                    WHERE completed = 0
                """).fetchall()

                exams = connection.execute("""
                    SELECT *
                    FROM exams
                    WHERE completed = 0
                """).fetchall()

                goals = connection.execute("""
                    SELECT title, target_hours
                    FROM goals
                    WHERE completed = 0
                """).fetchall()

                tasks = {
                    "assignments": [dict(row) for row in assignments],
                    "exams": [dict(row) for row in exams],
                    "goals": [dict(row) for row in goals]
                }

            finally:
                connection.close()

            try:
                prompt = (
                    f"Student question: {question}\n\n"
                    f"Pending assignments, exams, and goals: {tasks}\n\n"
                    "Give personalized study advice using this data. "
                    "Prioritize urgent deadlines and upcoming exams."
                )
                answer = get_ai_recommendation(prompt)
                
                connection = get_connection()

                try:
                    connection.execute("""
                        INSERT INTO ai_chat_history (question, answer)
                        VALUES (?, ?)
                    """, (question, answer))

                    connection.commit()

                finally:
                    connection.close()

            except Exception as e:
                print("AI assistant error:", e)
                answer = "AI assistant is temporarily unavailable."

    return render_template(
        "ai_assistant.html",
        answer=answer,
        question=question
    )
    
@app.route("/ai-history")
def ai_history():
    connection = get_connection()

    try:
        history = connection.execute("""
            SELECT question, answer
            FROM ai_chat_history
            ORDER BY id DESC
        """).fetchall()

    finally:
        connection.close()

    return render_template("ai_history.html", history=history)
   
@app.route("/complete-goal/<int:goal_id>", methods=["POST"])
def complete_goal(goal_id):

    connection = get_connection()

    connection.execute(
        "DELETE FROM goals WHERE id = ?",
        (goal_id,)
    )

    connection.commit()
    connection.close()

    return redirect("/goals")

@app.route("/progress")
def progress():
    connection = sqlite3.connect("studyflow.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM assignments")
    total_assignments = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM assignments WHERE completed = 1")
    completed_assignments = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM exams")
    total_exams = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM goals")
    total_goals = cursor.fetchone()[0]

    connection.close()

    pending_assignments = total_assignments - completed_assignments

    progress_percentage = (
        round(completed_assignments / total_assignments * 100)
        if total_assignments > 0 else 0
    )

    return render_template(
        "progress.html",
        total_assignments=total_assignments,
        completed_assignments=completed_assignments,
        pending_assignments=pending_assignments,
        total_exams=total_exams,
        total_goals=total_goals,
        progress_percentage=progress_percentage
    )
 

# ---------------- NOTIFICATIONS PAGE ----------------
@app.route("/notifications")
def notifications_page():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, title, deadline, priority
        FROM assignments
        WHERE completed = 0
        ORDER BY deadline ASC
    """)
    assignments = cursor.fetchall()
    connection.close()

    return render_template(
        "notifications.html",
        assignments=assignments
    )

@app.route("/settings", methods=["GET", "POST"])
def settings():
    connection = get_connection()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()

        if not name or not phone:
            profile = connection.execute(
                "SELECT * FROM student_profile WHERE id = 1"
            ).fetchone()
            settings_data = connection.execute(
                "SELECT * FROM app_settings WHERE id = 1"
            ).fetchone()
            connection.close()

            return render_template(
                "settings.html",
                profile=profile,
                study_hours=settings_data["study_hours"],
                assignment_notifications=bool(
                    settings_data["assignment_notifications"]
                ),
                exam_notifications=bool(
                    settings_data["exam_notifications"]
                ),
                goal_notifications=bool(
                    settings_data["goal_notifications"]
                ),
                error="Please enter your name and phone number."
            )

        try:
            study_hours = int(request.form.get("study_hours", 7))
        except (ValueError, TypeError):
            study_hours = 7

        study_hours = max(1, min(study_hours, 16))

        assignment_notifications = int(
            "assignment_notifications" in request.form
        )
        exam_notifications = int(
            "exam_notifications" in request.form
        )
        goal_notifications = int(
            "goal_notifications" in request.form
        )

        connection.execute("""
            INSERT INTO student_profile (id, name, phone)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                phone = excluded.phone
        """, (name, phone))

        connection.execute("""
            UPDATE app_settings
            SET study_hours = ?,
                assignment_notifications = ?,
                exam_notifications = ?,
                goal_notifications = ?
            WHERE id = 1
        """, (
            study_hours,
            assignment_notifications,
            exam_notifications,
            goal_notifications
        ))

        connection.commit()

    profile = connection.execute(
        "SELECT * FROM student_profile WHERE id = 1"
    ).fetchone()

    settings_data = connection.execute(
        "SELECT * FROM app_settings WHERE id = 1"
    ).fetchone()

    connection.close()

    return render_template(
        "settings.html",
        profile=profile,
        study_hours=settings_data["study_hours"],
        assignment_notifications=bool(
            settings_data["assignment_notifications"]
        ),
        exam_notifications=bool(
            settings_data["exam_notifications"]
        ),
        goal_notifications=bool(
            settings_data["goal_notifications"]
        )
    )
 
# The scheduler runs inside the web process. Use one Gunicorn worker on Render.
scheduler_instance = None
if os.getenv("RUN_SCHEDULER", "1").strip().lower() not in ("0", "false", "no"):
    scheduler_instance = start_scheduler()


# ---------------- RUN APPLICATION ----------------
if __name__ == "__main__":
    app.run(debug=False, threaded=True)  