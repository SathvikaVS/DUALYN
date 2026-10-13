"""
Turns raw resume text into a validated list of Skill objects.
Gemini only ever proposes skill names; every name is checked against the
real Skill catalog before being trusted (Section 9: "do not blindly trust
extracted information"). A skill Gemini invents that doesn't exist in the
catalog is silently dropped, never auto-created.
"""
import json
import re

from django.db.models import Q
from skills.models import Skill
from skills.services.normalization import extract_skills_with_evidence, canonicalize_skill_name
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
    the caller - return an empty list instead.
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
    (case-insensitively or via canonical alias) survive. Everything
    else is discarded here, never auto-created.
    """
    normalized_candidates = set()
    canonical_candidates = set()

    for name in candidate_names:
        cleaned = str(name).strip().lower()
        if cleaned:
            normalized_candidates.add(cleaned)
            canon = canonicalize_skill_name(str(name))
            if canon:
                canonical_candidates.add(canon.lower())
                canonical_candidates.add(canon)

    matched_skills = list(Skill.objects.filter(
        Q(normalized_name__in=normalized_candidates) |
        Q(normalized_name__in=canonical_candidates) |
        Q(name__in=canonical_candidates)
    ).distinct())

    matched_names = {s.name for s in matched_skills}
    if 'HTML & CSS' in matched_names:
        matched_skills = [s for s in matched_skills if s.name not in ('HTML', 'CSS')]

    return matched_skills


def extract_resume_skills(resume_text):
    """
    Hybrid extraction pipeline:
    1. Deterministic normalization & regex extraction (fast, accurate, no external dependency).
    2. Optional Gemini AI extraction if configured.
    3. Merges and validates against real Skill catalog.
    Always returns a list of real Skill objects; never crashes.
    """
    if not resume_text or not resume_text.strip():
        return []

    # 1. Deterministic extraction via centralized normalization engine
    detected_map = extract_skills_with_evidence(resume_text)
    candidate_names = list(detected_map.keys())

    # 2. Optional AI enhancement if Gemini is available
    catalog_names = list(Skill.objects.values_list('name', flat=True))
    if catalog_names:
        try:
            prompt = build_prompt(resume_text, catalog_names)
            raw_response = generate_text(prompt)
            ai_candidates = parse_ai_response(raw_response)
            candidate_names.extend(ai_candidates)
        except Exception:
            # AI call failure is gracefully handled; deterministic results are preserved
            pass

    if not candidate_names:
        return []

    return validate_against_catalog(candidate_names)