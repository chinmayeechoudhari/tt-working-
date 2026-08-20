import json
import os

from google import genai

from app.constraints.schemas import GeneratedConstraint
from app.constraints.llm.base import LLMProvider


SYSTEM_PROMPT = """
You are a constraint-generation engine for an academic timetable optimization system.

Convert the user's natural-language timetable requirement into exactly ONE JSON object representing the logical constraint.
Return ONLY JSON. Do not use Markdown, Python, OR-Tools code, or database IDs.

The JSON object MUST have:
{
  "constraint_type": "hard" or "soft",
  "weight": number or null,
  "expression": {...},
  "explanation": "plain English explanation",
  "assumptions": []
}

HARD constraints use weight=null. SOFT constraints require a positive weight.

ATOMIC CONDITION:
{"kind":"atomic","field":"...","operator":"...","value":...}
Allowed fields: teacher, subject, class, room, room_type, subject_type, day, period, slot.
Allowed operators: eq, neq, lt, lte, gt, gte.

LOGICAL CONDITIONS:
{"kind":"and","conditions":[condition,...]}
{"kind":"or","conditions":[condition,...]}
{"kind":"not","condition":condition}

NUMERIC/STRUCTURAL EXPRESSIONS:
{"kind":"count","source":"assignments","filter":condition}
{"kind":"constant","value":number}
{"kind":"comparison","operator":"eq|neq|lt|lte|gt|gte","left":numeric_expression,"right":numeric_expression}
{"kind":"forbid","filter":condition}
{"kind":"exists","source":"assignments","filter":condition}
{"kind":"no_adjacent","filter":condition}
{"kind":"for_each","dimension":"day|teacher|subject|class|room","expression":expression}

SEMANTIC RULES:
1. Preserve the user's meaning exactly. Never invent database IDs.
2. Subject names are registrations scoped by class and subject type. If the user says "OS lab", interpret it as subject="OS" AND subject_type="lab", not a subject literally named "OS lab".
3. If a user explicitly names a class, include class as an atomic condition.
4. If a user explicitly names a subject type such as lab, laboratory, practical, or theory, include subject_type as an atomic condition.
5. A rule such as "no classes on Tuesday" is GLOBAL. It has no subject, class, teacher, or room. Represent it as a hard forbid of day == Tuesday.
6. Similar global rules include "nothing on Friday", "no classes Monday", and "no teaching on Wednesday". Do not invent a subject for these.
7. "No OS lab on Tuesday" means subject=OS, subject_type=lab, day=Tuesday.
8. "OS cannot occur on Tuesday" means subject=OS, day=Tuesday. The backend will ask for class/type if OS has multiple registrations.
9. Do not resolve or guess which class a repeated subject belongs to. Preserve the human-readable subject name and let the backend resolve the database registration.
10. Do not turn phrases such as "no classes" into a subject or class named "classes".
11. If a requirement is ambiguous, preserve the ambiguity rather than silently choosing an entity.
"""


class GeminiProvider(LLMProvider):
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

    def generate_constraint(self, user_text: str) -> GeneratedConstraint:
        prompt = f"""
{SYSTEM_PROMPT}

User requirement:
{user_text}

Generate the corresponding GeneratedConstraint.
"""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        return GeneratedConstraint.model_validate_json(response.text)
