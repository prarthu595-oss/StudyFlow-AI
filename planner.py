import math
from datetime import datetime, timedelta

def is_timetable_conflict(start_time, end_time, timetable):
    """Check whether a study session overlaps college timetable."""

    day = start_time.strftime("%A")

    for item in timetable:
        if item["day"] != day:
            continue

        class_start = datetime.strptime(
            item["start_time"], "%H:%M"
        ).time()

        class_end = datetime.strptime(
            item["end_time"], "%H:%M"
        ).time()

        session_start = start_time.time()
        session_end = end_time.time()

        if session_start < class_end and session_end > class_start:
            return True

    return False
def has_timetable_conflict(start_time, end_time, timetable):
    """Check timetable conflict and return the conflict end time."""

    day = start_time.strftime("%A")

    for item in timetable:
        if item["day"] != day:
            continue

        class_start = datetime.strptime(
            item["start_time"], "%H:%M"
        ).time()

        class_end = datetime.strptime(
            item["end_time"], "%H:%M"
        ).time()

        session_start = start_time.time()
        session_end = end_time.time()

        if session_start < class_end and session_end > class_start:
            conflict_end = datetime.combine(
                start_time.date(),
                class_end
            )

            return True, conflict_end

    return False, None

def generate_study_plan(assignments, exams=None, available_hours=5, timetable=None):
    
    if exams is None:
        exams = []
    
    if timetable is None:
        timetable = []
            
    # Priority ranking
    priority_order = {
        "CRITICAL": 1,
        "HIGH": 2,
        "MEDIUM": 3,
        "LOW": 4
    }

    tasks = []

    # ------------------------------------------------
    # 1. ADD ASSIGNMENTS
    # ------------------------------------------------

    for assignment in assignments:

        tasks.append({
            "type": "Assignment",
            "title": assignment["title"],
            "subject": assignment["subject"],
            "deadline": assignment["deadline"],
            "priority": assignment["priority"],
            "priority_score": assignment.get("priority_score", 0),
            "hours": float(assignment["estimated_hours"])
        })

    # ------------------------------------------------
    # 2. ADD EXAMS
    # ------------------------------------------------

    today = datetime.now().date()

    for exam in exams:

        exam_date = datetime.strptime(
            exam["exam_date"],
            "%Y-%m-%d"
        ).date()

        days_left = (exam_date - today).days

        preparation_hours = float(
            exam["preparation_hours"]
        )

        # Determine exam priority
        if days_left <= 1:
            priority = "CRITICAL"
            score = 100

        elif days_left <= 3:
            priority = "HIGH"
            score = 85

        elif days_left <= 7:
            priority = "HIGH"
            score = 70

        elif days_left <= 14:
            priority = "MEDIUM"
            score = 50

        else:
            priority = "LOW"
            score = 25

        tasks.append({
            "type": "Exam Preparation",
            "title": f"{exam['subject']} Exam Preparation",
            "subject": exam["subject"],
            "deadline": exam["exam_date"],
            "priority": priority,
            "priority_score": score,
            "hours": preparation_hours,
            "days_left": days_left,
            "syllabus": exam.get("syllabus", "")
        })

    # ------------------------------------------------
    # 3. SORT BY PRIORITY
    # ------------------------------------------------

    tasks.sort(
        key=lambda task: (
            priority_order.get(task["priority"], 5),
            -task["priority_score"],
            task["deadline"]
        )
    )

    # ------------------------------------------------
    # 4. AVAILABLE STUDY TIME
    # ------------------------------------------------

    remaining_hours = float(available_hours)

    current_time = datetime.now().replace(
        minute=0,
        second=0,
        microsecond=0
    )

    schedule = []

    # ------------------------------------------------
    # 5. CREATE SMART SCHEDULE
    # ------------------------------------------------

    for task in tasks:

        if remaining_hours <= 0:
           break

        required_hours = float(task["hours"])

        # Maximum 2 hours per study session
        session_count = math.ceil(required_hours / 2.0)

        for session in range(session_count):

            if remaining_hours <= 0:
                break

            session_hours = min(
                2.0,
                required_hours - (session * 2.0),
                remaining_hours
            )

        if session_hours <= 0:
            break

        start_time = current_time

        end_time = current_time + timedelta(
            hours=session_hours
        )
        
        # Check college timetable conflict
        conflict, conflict_end = has_timetable_conflict(
           start_time,
           end_time,
           timetable
        )

        if conflict:
            print(
              "⚠️ Timetable conflict detected. "
              "Moving study session."
            )

            current_time = conflict_end + timedelta(minutes=30)

            # Recalculate this session after the college class
            start_time = current_time
            end_time = current_time + timedelta(
                hours=session_hours
            )

        schedule.append({
            "type": task["type"],
            "title": task["title"],
            "subject": task["subject"],
            "deadline": task["deadline"],
            "priority": task["priority"],
            "hours": round(session_hours, 1),
            "start_time": start_time.strftime("%I:%M %p"),
            "end_time": end_time.strftime("%I:%M %p"),
            "days_left": task.get("days_left"),
            "syllabus": task.get("syllabus", "")
        })

        current_time = end_time
        remaining_hours -= session_hours
        
        # Add a 30-minute break after every study session
        current_time += timedelta(minutes=30)
    return schedule

def add_goals_to_schedule(schedule, goals, available_hours,timetable=None):
    """
    Add study goals using maximum 2-hour study sessions
    with real start and end times.
    """

    remaining_hours = float(available_hours)
    if timetable is None:
        timetable = []
    
    # Calculate hours already used
    for item in schedule:
        remaining_hours -= float(item.get("hours", 0))

    print("REMAINING HOURS BEFORE GOALS:", remaining_hours)

    # Start goal sessions after the last scheduled session
    if schedule and schedule[-1].get("end_time"):
        try:
            current_time = datetime.strptime(
                schedule[-1]["end_time"],
                "%I:%M %p"
            )
        except ValueError:
            current_time = datetime.now().replace(
                minute=0,
                second=0,
                microsecond=0
            )
    else:
        current_time = datetime.now().replace(
            minute=0,
            second=0,
            microsecond=0
        )

    for goal in goals:

        if remaining_hours <= 0:
            break

        goal_hours = float(goal.get("target_hours", 0))

        if goal_hours <= 0:
            continue

        session_count = math.ceil(goal_hours / 2.0)
        remaining_goal_hours = goal_hours

        for session in range(session_count):

            if remaining_hours <= 0:
                break
            # Keep study sessions within 5 AM - 11 PM
            if current_time.hour >= 23:
                current_time = (current_time + timedelta(days=1)).replace(
                   hour=5,
                   minute=0,
                   second=0,
                   microsecond=0
                )

            if current_time.hour < 5:
                current_time = current_time.replace(
                   hour=5,
                   minute=0,
                   second=0,
                   microsecond=0
                )

            # Do not start a 2-hour session if it would cross 10 PM
            if current_time + timedelta(hours=2) > current_time.replace(
                hour=23,
                minute=0,
                second=0,
                microsecond=0
            ):
                current_time = (current_time + timedelta(days=1)).replace(
                    hour=5,
                    minute=0,
                    second=0,
                    microsecond=0
                )
    
            # Avoid college timetable conflicts
            while is_timetable_conflict(
                current_time,
                current_time + timedelta(hours=min(2.0, remaining_hours)),
                timetable
            ):
                
                current_time += timedelta(minutes=30)

            planned_hours = min(
                remaining_goal_hours,
                remaining_hours,
                2.0
            )

            start_time = current_time

            end_time = current_time + timedelta(
                hours=planned_hours
            )

            schedule.append({
                "type": "Goal",
                "title": goal["title"],
                "subject": "Study Goal",
                "deadline": "Goal",
                "priority": "MEDIUM",
                "hours": round(planned_hours, 1),
                "start_time": start_time.strftime("%I:%M %p"),
                "end_time": end_time.strftime("%I:%M %p"),
                "days_left": None,
                "syllabus": ""
            })

            remaining_goal_hours -= planned_hours
            remaining_hours -= planned_hours

            # 30-minute break before the next session
            current_time = end_time + timedelta(minutes=30)

            if remaining_goal_hours <= 0:
                break

    print("REMAINING HOURS AFTER GOALS:", remaining_hours)

    return schedule