import os
from google import genai

_api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=_api_key) if _api_key else None


def get_ai_recommendation(tasks):
    if client is None:
        return "Gemini API key is not configured. Add GEMINI_API_KEY to your environment."
    prompt = f"""
You are StudyFlow AI, a helpful and accurate student AI assistant.
The student has asked this question or provided this task:
{tasks}

Instructions:
1. Answer the student's actual question directly.
2. For academic questions, explain the concept accurately in simple words.
3. For programming questions, provide correct code and explain it briefly.
4. For exam questions, give clear, exam-oriented answers.
5. Give study-planning advice only when the student asks for it.
6. Do not invent deadlines, subjects, priorities, or task details.
7. If the question is unclear, ask for clarification.
8. Keep the answer relevant to the student's question.
"""
    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite", contents=prompt
        )
        return response.text or "No response received from Gemini."
    except Exception as error:
        print("Gemini API error:", type(error).__name__, str(error))
        return "Sorry, the AI assistant is temporarily unavailable."


def get_ai_priority_order(tasks):
    if client is None:
        return "[]"
    prompt = f"""
You are StudyFlow AI, an intelligent student study planner.
Rank these tasks from highest priority to lowest priority.
Consider deadline, workload, urgency, exam proximity, and available preparation time.
Student tasks: {tasks}
Return ONLY a Python-style list of task titles in priority order.
"""
    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite", contents=prompt
        )
        return (response.text or "[]").strip()
    except Exception as error:
        print("Gemini priority error:", type(error).__name__, str(error))
        return "[]"
