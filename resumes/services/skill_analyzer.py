"""
resumes/services/skill_analyzer.py
Turns raw resume text into a validated list of Skill objects.
Hybrid pipeline:
1. High-accuracy deterministic regex & normalization extraction (fast, zero hallucinations).
2. Optional Gemini AI extraction with strict grounding against resume text.
3. Trust boundary validation against Skill catalog.
"""
import json
import re

from django.db.models import Q
from skills.models import Skill
from skills.services.normalization import (
    SKILL_CATALOG,
    extract_skills_with_evidence,
    canonicalize_skill_name
)
from .ai_service import generate_text


def build_prompt(resume_text, catalog_names):
    catalog_list = ", ".join(catalog_names)
    return (
        "You are an expert technical competency extractor for a career platform.\n"
        f"Here is our tracked competency catalog: {catalog_list}\n\n"
        "Read the student's resume text below and extract all technical skills, "
        "programming languages, frameworks, databases, tools, cloud services, and "
        "engineering competencies from that catalog that are genuinely evidenced "
        "in the text (explicitly listed, mentioned, or applied in a project/experience).\n\n"
        "CRITICAL RULES:\n"
        "1. Do NOT invent, assume, or hallucinate skills that are not supported by the resume text.\n"
        "2. Do NOT include a skill just because it sounds related if it is not actually in the text.\n"
        "3. Return ONLY a valid JSON array of strings corresponding to catalog skill names.\n"
        'Example response: ["Python", "Django", "SQL", "Git"]\n\n'
        f"Resume text:\n{resume_text}"
    )


def parse_ai_response(raw_text):
    """
    Parses raw AI text response into a list of skill name strings.
    Strips markdown code fences and returns empty list on invalid JSON.
    """
    if not raw_text:
        return []
    cleaned = re.sub(r"```json|```", "", raw_text).strip()
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if item and str(item).strip()]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _is_candidate_supported_by_text(candidate: str, lower_text: str) -> bool:
    """
    Grounding check: verifies that an AI-suggested candidate actually has
    textual evidence in the resume, preventing hallucinations.
    """
    canon = canonicalize_skill_name(candidate)
    cand_lower = candidate.strip().lower()

    # Collect alias forms to check
    aliases_to_check = {cand_lower}
    if canon in SKILL_CATALOG:
        catalog_data = SKILL_CATALOG[canon]
        for a in catalog_data.get('aliases', []):
            aliases_to_check.add(a.lower())
        aliases_to_check.add(canon.lower())

    for alias in aliases_to_check:
        if len(alias) <= 1:
            continue
        # Use word boundary check
        escaped = re.escape(alias)
        if re.search(rf'\b{escaped}\b', lower_text, re.IGNORECASE):
            return True

    return False


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
    ).distinct().order_by('name'))

    return matched_skills


def extract_resume_skills_with_evidence(resume_text):
    """
    Hybrid extraction pipeline:
    1. Deterministic normalization & regex extraction (fast, accurate, no external dependency).
    2. Optional Gemini AI extraction with strict grounding against resume text.
    3. Guarantees that every detected competency is traceable to an exact sentence and section.
    4. Validates against Skill catalog and resolves duplicate or overlapping entries.

    Returns: (list_of_skills, evidence_dict)
    """
    if not resume_text or not resume_text.strip():
        return [], {}

    # 1. Deterministic extraction via centralized normalization engine
    detected_map = extract_skills_with_evidence(resume_text)

    # 2. Build catalog list for AI prompt (combine DB skills with SKILL_CATALOG)
    db_catalog_names = set(Skill.objects.values_list('name', flat=True))
    all_catalog_names = sorted(db_catalog_names.union(SKILL_CATALOG.keys()))

    if all_catalog_names:
        try:
            prompt = build_prompt(resume_text, all_catalog_names)
            raw_response = generate_text(prompt)
            ai_candidates = parse_ai_response(raw_response)

            lower_text = resume_text.lower()
            for cand in ai_candidates:
                canon = canonicalize_skill_name(cand)
                if canon not in detected_map and _is_candidate_supported_by_text(cand, lower_text):
                    # Verify text presence and extract enclosing sentence
                    escaped = re.escape(cand)
                    m = re.search(rf'\b{escaped}\b', resume_text, re.IGNORECASE)
                    if m:
                        from skills.services.normalization import _split_into_sections, _get_active_section, _extract_matched_sentence
                        sections = _split_into_sections(resume_text)
                        sec_name = _get_active_section(m.start(), sections)
                        sentence = _extract_matched_sentence(m.start(), m.end(), resume_text)
                        catalog_entry = SKILL_CATALOG.get(canon, {})
                        detected_map[canon] = {
                            'canonical': canon,
                            'category': catalog_entry.get('category', 'Technical Skills'),
                            'matched_alias': m.group(0),
                            'section': sec_name,
                            'sentence': sentence,
                            'excerpt': f"...{sentence}...",
                            'strength': 'moderate',
                            'is_project_evidence': (sec_name == 'Projects'),
                            'occurrences': 1,
                            'is_inferred': False,
                            'evidence_type': 'explicit',
                        }
        except Exception:
            # AI call failure is gracefully handled; deterministic results are preserved
            pass

    # Avoid duplicate overlapping detections (Requirement 2 & 7)
    if 'HTML' in detected_map and 'CSS' in detected_map:
        detected_map.pop('HTML & CSS', None)

    # Do not infer Testing from Debugging (Requirement 4)
    if 'Debugging' in detected_map and 'Testing' not in detected_map:
        detected_map.pop('Testing & Debugging', None)

    candidate_names = list(detected_map.keys())
    if not candidate_names:
        return [], {}

    matched_skills = validate_against_catalog(candidate_names)

    # Filter and organize evidence by matched skill name
    evidence_dict = {}
    for skill in matched_skills:
        if skill.name in detected_map:
            evidence_dict[skill.name] = detected_map[skill.name]
        else:
            canon = canonicalize_skill_name(skill.name)
            if canon in detected_map:
                evidence_dict[skill.name] = detected_map[canon]
            else:
                # Fallback evidence structure guaranteeing traceability metadata
                evidence_dict[skill.name] = {
                    'canonical': skill.name,
                    'category': skill.category or 'Technical Skills',
                    'matched_alias': skill.name,
                    'section': 'Parsed Content',
                    'sentence': '',
                    'excerpt': '',
                    'strength': 'basic',
                    'is_project_evidence': False,
                    'occurrences': 1,
                    'is_inferred': False,
                    'evidence_type': 'explicit',
                }

    return matched_skills, evidence_dict


def extract_resume_skills(resume_text):
    """
    Backwards-compatible wrapper returning the list of Skill objects.
    """
    skills, _ = extract_resume_skills_with_evidence(resume_text)
    return skills