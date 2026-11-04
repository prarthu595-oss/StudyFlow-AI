import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE = os.getenv("DATABASE_PATH", str(BASE_DIR / "studyflow.db"))

def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subject TEXT NOT NULL,
            deadline TEXT NOT NULL,
            estimated_hours REAL NOT NULL,
            completed INTEGER DEFAULT 0,
            priority TEXT DEFAULT 'LOW',
            priority_score INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            exam_date TEXT NOT NULL,
            preparation_hours REAL NOT NULL,
            syllabus TEXT,
            completed INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           token TEXT UNIQUE NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS goals (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           title TEXT NOT NULL,
           target_hours REAL NOT NULL,
           completed INTEGER DEFAULT 0
        )
    """)
    
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            name TEXT NOT NULL,
            phone TEXT NOT NULL
        )
    """)

    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            study_hours INTEGER NOT NULL DEFAULT 7,
            assignment_notifications INTEGER NOT NULL DEFAULT 1,
            exam_notifications INTEGER NOT NULL DEFAULT 1,
            goal_notifications INTEGER NOT NULL DEFAULT 1
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO app_settings (id)
        VALUES (1)
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()