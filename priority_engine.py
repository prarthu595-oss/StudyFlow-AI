from datetime import datetime


def calculate_priority(deadline, estimated_hours):

    today = datetime.now().date()
    target_date = datetime.strptime(deadline, "%Y-%m-%d").date()

    days_left = (target_date - today).days

    score = 0

    # Deadline priority
    if days_left <= 0:
        score += 80
    elif days_left == 1:
        score += 70
    elif days_left <= 3:
        score += 55
    elif days_left <= 7:
        score += 35
    elif days_left <= 14:
        score += 20
    else:
        score += 5

    # Study workload
    if estimated_hours >= 5:
        score += 25
    elif estimated_hours >= 3:
        score += 20
    elif estimated_hours >= 2:
        score += 10
    else:
        score += 5

    # Priority level
    if score >= 80:
        priority = "CRITICAL"
    elif score >= 60:
        priority = "HIGH"
    elif score >= 30:
        priority = "MEDIUM"
    else:
        priority = "LOW"

    return priority, score