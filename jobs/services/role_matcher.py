"""
jobs/services/role_matcher.py
Detects candidate target job roles and professional headlines from uploaded resumes.

Features:
- Extracts professional headlines from resume headers, title fields, or professional summaries.
- Normalizes and matches headlines to canonical JobRole records (e.g. 'Java Full Stack Developer').
- Handles role synonyms, variations (e.g. 'Fullstack', 'Full-Stack', 'Full Stack Java'),
  and qualifiers ('Aspiring', 'Junior', 'Senior', 'Associate', 'Lead', 'Developer', 'Engineer').
- Prioritizes specific matches (e.g. 'Java Full Stack Developer' over generic 'Full-Stack Developer').
- Works with both Resume model instances and raw extracted resume text strings.
"""
import re
from typing import Optional, Tuple, List
from jobs.models import JobRole
from jobs.services.role_profiles import sync_role_profiles_to_db


# Known role patterns sorted by specificity (more specific patterns match first)
ROLE_MATCHING_RULES = [
    # 1. Java Full Stack Developer (highest priority to avoid partial match with generic Full-Stack)
    {
        'canonical_title': 'Java Full Stack Developer',
        'patterns': [
            r'\bjava\s+full[\s-]?stack(?:\s+(?:developer|engineer|programmer|specialist))?\b',
            r'\bfull[\s-]?stack\s+java(?:\s+(?:developer|engineer|programmer|specialist))?\b',
            r'\bjava\s+fullstack(?:\s+(?:developer|engineer|programmer|specialist))?\b',
            r'\bjava\s+developer\b',
            r'\bcore\s+java\s+developer\b',
        ],
    },
    # 2. Django Developer (prioritize over generic Python Developer if Django is explicit)
    {
        'canonical_title': 'Django Developer',
        'patterns': [
            r'\bdjango\s+(?:web\s+)?(?:developer|engineer|programmer)\b',
            r'\bpython\s*(?:&|\/|and)\s*django(?:\s+(?:developer|engineer|programmer))?\b',
            r'\bdjango\b',
        ],
    },
    # 3. Python Developer
    {
        'canonical_title': 'Python Developer',
        'patterns': [
            r'\bpython\s+(?:software\s+|web\s+)?(?:developer|engineer|programmer)\b',
            r'\bpython\s*(?:&|\/|\s)\s*software\s+developer\b',
            r'\bpython\s+backend\b',
            r'\bpython\b',
        ],
    },
    # 4. Backend Developer
    {
        'canonical_title': 'Backend Developer',
        'patterns': [
            r'\bback[\s-]?end\s+(?:software\s+|web\s+)?(?:developer|engineer|programmer)\b',
            r'\bbackend\b',
        ],
    },
    # 5. Full-Stack Developer (generic, without Java)
    {
        'canonical_title': 'Full-Stack Developer',
        'patterns': [
            r'\bfull[\s-]?stack\s+(?:software\s+|web\s+)?(?:developer|engineer|programmer)\b',
            r'\bfullstack\s+(?:developer|engineer|programmer)\b',
            r'\bfull[\s-]?stack\b',
        ],
    },
    # 6. Data Analyst
    {
        'canonical_title': 'Data Analyst',
        'patterns': [
            r'\bdata\s+analyst\b',
            r'\bdata\s+analytics(?:\s+(?:specialist|engineer|consultant))?\b',
            r'\bbi\s+analyst\b',
            r'\bbusiness\s+intelligence\s+analyst\b',
        ],
    },
]


# Words indicating contact info or document metadata, NOT a job headline
IGNORE_LINE_PATTERNS = [
    r'@',                                     # email address
    r'https?://',                             # URL
    r'www\.',                                 # URL
    r'linkedin\.com',                         # LinkedIn
    r'github\.com',                           # GitHub
    r'^\s*(?:resume|cv|curriculum\s+vitae)\s*$',  # Resume title
    r'^\s*page\s+\d+\s*(?:of\s+\d+)?\s*$',   # Page numbers
    r'^\s*(?:phone|mobile|tel|contact)[:\s]', # Contact label
    r'^\s*\+?\d[\d\s\-\(\)\.]{7,}\d\s*$',    # Standalone phone number
]

# Section headers where headline search stops
SECTION_HEADERS = [
    'technical skills', 'skills', 'experience', 'work experience',
    'education', 'projects', 'technical projects', 'certifications',
    'coursework', 'achievements', 'declaration'
]

# Prefixes to strip when normalizing a candidate headline string for display
HEADLINE_PREFIX_STRIP = r'(?i)^\s*(?:aspiring|junior|jr\.?|senior|sr\.?|entry[\s-]level|lead|associate|freelance|professional)\s+'


def clean_headline_text(raw_text: str) -> str:
    """
    Cleans raw headline line by stripping contact details, URLs, and excessive punctuation.
    """
    if not raw_text:
        return ''

    # Remove email addresses
    cleaned = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', raw_text)
    # Remove URLs
    cleaned = re.sub(r'https?://\S+|www\.\S+|linkedin\.com/\S+|github\.com/\S+', '', cleaned)
    # Remove phone numbers
    cleaned = re.sub(r'\(?\+?\d[\d\s\-\.]{7,}\d\)?', '', cleaned)
    # Remove leading labels like "Headline:", "Title:", "Target Role:"
    cleaned = re.sub(r'(?i)^\s*(?:headline|target\s+role|desired\s+role|professional\s+title|job\s+title|title|role)\s*[:|-]\s*', '', cleaned)
    # Clean up trailing/leading separators
    cleaned = re.sub(r'^[|\-•–—\s]+|[|\-•–—\s]+$', '', cleaned)
    # Collapse whitespace
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()

    return cleaned


def extract_headline(resume_text: str) -> Optional[str]:
    """
    Extracts the candidate's professional headline or target title from resume text.
    Inspects early header lines and the Professional Summary/Objective opening.
    """
    if not resume_text or not resume_text.strip():
        return None

    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    if not lines:
        return None

    # 1. First pass: look for an explicit label like "Headline:", "Target Role:", "Title:"
    for line in lines[:20]:
        m = re.match(r'(?i)^\s*(?:headline|target\s+role|desired\s+role|professional\s+title|job\s+title|position)\s*[:|-]\s*(.+)$', line)
        if m:
            cand = clean_headline_text(m.group(1))
            if cand and len(cand) <= 100:
                return cand

    # 2. Second pass: scan the header lines (first 10 lines)
    # Look for a line containing role-defining terms (developer, analyst, engineer, full stack, etc.)
    role_keyword_pattern = re.compile(
        r'(?i)\b(?:developer|engineer|analyst|programmer|architect|full[\s-]?stack|fullstack|backend|frontend|data\s+analyst|web\s+developer)\b'
    )

    for i, line in enumerate(lines[:10]):
        # Stop if we hit a standard major section header
        lower_line = line.lower().strip()
        if any(lower_line == header or lower_line.startswith(header + ':') for header in SECTION_HEADERS):
            break

        # Skip lines that are clearly contact info, URLs, phone numbers
        if any(re.search(pat, line, re.IGNORECASE) for pat in IGNORE_LINE_PATTERNS):
            # Check if this line has a headline followed by email/phone (e.g. "JAVA FULLSTACK DEVELOPER madhavan@...")
            cleaned = clean_headline_text(line)
            if role_keyword_pattern.search(cleaned) and len(cleaned) <= 80:
                return cleaned
            continue

        # Skip line 0 if it looks like just a candidate name (1-4 words of letters only, no role keywords)
        if i == 0 and not role_keyword_pattern.search(line):
            words = line.split()
            if 1 <= len(words) <= 5 and all(w.replace('.', '').replace('-', '').isalpha() for w in words):
                continue

        # Check if line matches role keywords
        cleaned = clean_headline_text(line)
        if role_keyword_pattern.search(cleaned) and 3 <= len(cleaned) <= 100:
            return cleaned

    # 3. Third pass: inspect opening of PROFESSIONAL SUMMARY or OBJECTIVE section
    in_summary = False
    for line in lines[:25]:
        lower_line = line.lower().strip()
        if re.search(r'(?i)\b(?:professional\s+summary|summary|career\s+objective|objective|profile)\b', lower_line):
            in_summary = True
            continue

        if in_summary:
            # Stop if another major section begins
            if any(lower_line == header or lower_line.startswith(header + ':') for header in SECTION_HEADERS):
                break

            # Look for phrases like "Seeking an entry-level Java Full Stack Developer opportunity"
            # or "Java Full Stack Developer skilled in building..."
            # or "Aspiring Python / Django Developer..."
            role_phrases = [
                r'(?i)\b(?:aspiring\s+)?(Java\s+Full[\s-]?Stack\s+Developer|Java\s+Fullstack\s+Developer)\b',
                r'(?i)\b(?:aspiring\s+)?(Python\s*(?:&|\/|and)\s*Django\s+Developer|Django\s+Developer)\b',
                r'(?i)\b(?:aspiring\s+)?(Python\s+Developer)\b',
                r'(?i)\b(?:aspiring\s+)?(Backend\s+Developer|Back-End\s+Developer)\b',
                r'(?i)\b(?:aspiring\s+)?(Full[\s-]?Stack\s+Developer)\b',
                r'(?i)\b(?:aspiring\s+)?(Data\s+Analyst)\b',
            ]
            for pat in role_phrases:
                m = re.search(pat, line)
                if m:
                    return m.group(0).strip()

    return None


def match_role_from_text(text: str) -> Optional[JobRole]:
    """
    Matches headline text (or resume snippet) against existing JobRole models.
    Returns the best matching JobRole or None.
    """
    if not text or not text.strip():
        return None

    # Ensure canonical roles are loaded
    if not JobRole.objects.exists():
        sync_role_profiles_to_db()

    roles_by_title = {r.title.lower(): r for r in JobRole.objects.all()}

    # 1. First test structured matching rules (sorted by specificity)
    for rule in ROLE_MATCHING_RULES:
        canonical_title = rule['canonical_title']
        role_obj = roles_by_title.get(canonical_title.lower())
        if not role_obj:
            continue

        for pattern in rule['patterns']:
            if re.search(pattern, text, re.IGNORECASE):
                return role_obj

    # 2. Direct exact title or substring match against any database JobRole
    cleaned_lower = text.lower().strip()
    # Strip common prefixes like 'aspiring'
    cleaned_stripped = re.sub(HEADLINE_PREFIX_STRIP, '', cleaned_lower).strip()

    for title_lower, role_obj in roles_by_title.items():
        if title_lower == cleaned_lower or title_lower == cleaned_stripped:
            return role_obj
        # Word boundary match of role title inside headline
        escaped = re.escape(title_lower)
        if re.search(rf'\b{escaped}\b', cleaned_lower):
            return role_obj

    return None


def detect_target_role_from_resume(resume_or_text) -> Tuple[Optional[JobRole], Optional[str]]:
    """
    Main detection pipeline:
    Given a Resume model instance or raw resume text:
    1. Extracts candidate headline.
    2. Matches headline against JobRole records.
    3. If no headline was matched directly, falls back to analyzing the full text for target role signals.

    Returns: (matched_job_role, extracted_headline)
    """
    if not resume_or_text:
        return None, None

    # Support Resume model instances or raw string
    if hasattr(resume_or_text, 'extracted_text'):
        resume_text = resume_or_text.extracted_text or ''
    else:
        resume_text = str(resume_or_text)

    if not resume_text.strip():
        return None, None

    headline = extract_headline(resume_text)
    matched_role = None

    if headline:
        matched_role = match_role_from_text(headline)

    # Fallback: if headline didn't match a role directly, search the first 1500 chars of resume
    if not matched_role:
        header_sample = resume_text[:1500]
        matched_role = match_role_from_text(header_sample)
        if matched_role and not headline:
            headline = matched_role.title

    return matched_role, headline
