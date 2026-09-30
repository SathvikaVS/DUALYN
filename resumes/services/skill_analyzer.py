"""
Turns raw resume text into a validated list of Skill objects.
Gemini only ever proposes skill names; every name is checked against the
real Skill catalog before being trusted (Section 9: "do not blindly trust
extracted information"). A skill Gemini invents that doesn't exist in the
catalog is silently dropped, never auto-created.
"""
import json
import re

from skills.models import Skill
from .ai_service import generate_text


def build_prompt(resume_text, catalog_names):
    catalog_list = ", ".join(catalog_names)
    return (
        "You are extracting technical skills from a student's resume.\n"
        f"Here is the list of skills we track: {catalog_list}\n\n"
        "Read the resume text below and return ONLY the skills from that "
        "exact list that are genuinely evidenced in the text (mentioned, "
        "used in a project, or listed as a technology). Do not invent "
        "skills that are not in the list. Do not include a skill just "
        "because it sounds related.\n\n"
        "Respond with ONLY a JSON array of strings, nothing else. "
        'Example: ["Python", "Django", "SQL"]\n\n'
        f"Resume text:\n{resume_text}"
    )


def parse_ai_response(raw_text):
    """
    Gemini sometimes wraps JSON in ```json fences despite instructions.
    Strip those before parsing, and never let a malformed response crash
    the caller - return an empty list instead (Section 27).
    """
    cleaned = re.sub(r"```json|```", "", raw_text).strip()
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def validate_against_catalog(candidate_names):
    """
    The trust boundary: only names that match a real Skill row
    (case-insensitively) survive. Everything else is discarded here,
    not downstream.
    """
    normalized_candidates = {name.strip().lower() for name in candidate_names}
    return list(Skill.objects.filter(normalized_name__in=normalized_candidates))


def extract_resume_skills(resume_text):
    """
    Full pipeline: catalog -> prompt -> Gemini -> parse -> validate.
    Returns a list of real Skill objects. Returns an empty list (never
    raises) if Gemini fails, so resume upload always succeeds even when
    the AI call doesn't (Section 27: "AI/API failure").
    """
    catalog_names = list(Skill.objects.values_list('name', flat=True))
    if not catalog_names or not resume_text.strip():
        return []

    prompt = build_prompt(resume_text, catalog_names)
    try:
        raw_response = generate_text(prompt)
    except Exception:
        return []

    candidate_names = parse_ai_response(raw_response)
    if not candidate_names:
        return []

    return validate_against_catalog(candidate_names)