"""
skills/services/normalization.py
Centralized Skill Normalization, Aliasing, and Matching System for DUALYN.

Features:
- Centralized canonical skill registry with alias mappings.
- Clean text normalization (case, punctuation, whitespace, separators).
- Regex word-boundary matching to prevent false substring matches (e.g. 'c' in 'basic', 'git' in 'digital').
- Compound competency support (e.g. 'HTML & CSS' maps to individual 'HTML' and 'CSS', and vice-versa).
- Section-aware evidence extraction from resumes and project descriptions.
"""
import re
from typing import Dict, List, Optional, Tuple, Set, Any


# ---------------------------------------------------------------------------
# CANONICAL SKILL REGISTRY
# ---------------------------------------------------------------------------
SKILL_CATALOG: Dict[str, Dict[str, Any]] = {
    'Python': {
        'canonical': 'Python',
        'category': 'Programming',
        'aliases': [
            'python', 'python3', 'python 3', 'python programming', 'python developer',
            'python scripting', 'py', 'cpython'
        ],
        'pattern': r'\bpython(?:3|\s+programming|\s+scripting)?\b',
    },
    'Django': {
        'canonical': 'Django',
        'category': 'Backend Development',
        'aliases': ['django', 'django framework', 'django mvc', 'django mtv', 'django orm'],
        'pattern': r'\bdjango(?:\s+framework|\s+mvc|\s+mtv|\s+orm)?\b',
    },
    'HTML': {
        'canonical': 'HTML',
        'category': 'Frontend Development',
        'aliases': ['html', 'html5', 'hypertext markup language'],
        'pattern': r'\bhtml5?\b',
    },
    'CSS': {
        'canonical': 'CSS',
        'category': 'Frontend Development',
        'aliases': [
            'css', 'css3', 'cascading style sheets', 'responsive design',
            'responsive design basics', 'flexbox', 'css grid'
        ],
        'pattern': r'\bcss3?\b|\bresponsive\s+design(?:\s+basics)?\b|\bcascading\s+style\s+sheets\b',
    },
    'HTML & CSS': {
        'canonical': 'HTML & CSS',
        'category': 'Frontend Development',
        'is_compound': True,
        'components': ['HTML', 'CSS'],
        'aliases': [
            'html & css', 'html and css', 'html/css', 'html / css', 'html+css',
            'html5/css3', 'html5 & css3', 'html5 and css3', 'html5 + css3',
            'html, css', 'html5, css3'
        ],
        'pattern': r'\bhtml5?\s*(?:&|and|\/|\+|\,)\s*css3?\b',
    },
    'JavaScript': {
        'canonical': 'JavaScript',
        'category': 'Frontend Development',
        'aliases': ['javascript', 'js', 'es6', 'ecmascript', 'vanilla js', 'modern javascript'],
        'pattern': r'\b(?:javascript|js|es6|ecmascript|vanilla\s+js)\b',
    },
    'Object-Oriented Programming': {
        'canonical': 'Object-Oriented Programming',
        'category': 'Core Concepts',
        'aliases': [
            'object-oriented programming', 'object oriented programming',
            'oop', 'oops', 'oop basics', 'oops basics', 'object-oriented design',
            'ood', 'object-oriented concepts'
        ],
        'pattern': r'\b(?:object[\s-]oriented\s+programming|object[\s-]oriented\s+design|oop[s]?(?:\s+basics)?|ood)\b',
    },
    'Data Structures & Algorithms': {
        'canonical': 'Data Structures & Algorithms',
        'category': 'Core Concepts',
        'aliases': [
            'data structures & algorithms', 'data structures and algorithms',
            'dsa', 'data structures', 'algorithms', 'ds & algo', 'ds and algo'
        ],
        'pattern': r'\b(?:data\s+structures\s*(?:&|and)\s*algorithms|dsa|data\s+structures|algorithms)\b',
    },
    'SQL': {
        'canonical': 'SQL',
        'category': 'Databases',
        'aliases': [
            'sql', 'mysql', 'sqlite', 'sqlite3', 'relational database', 'rdbms',
            'sql queries', 'mysql / sqlite', 'mysql/sqlite'
        ],
        'pattern': r'\b(?:sql|mysql|sqlite3?|rdbms|relational\s+database)\b',
    },
    'PostgreSQL': {
        'canonical': 'PostgreSQL',
        'category': 'Databases',
        'aliases': ['postgresql', 'postgres', 'pgsql', 'psql'],
        'pattern': r'\b(?:postgresql|postgres|pgsql|psql)\b',
    },
    'Git': {
        'canonical': 'Git',
        'category': 'Tools & Version Control',
        'aliases': [
            'git', 'git version control', 'github', 'gitlab', 'version control',
            'git cli', 'git/github', 'git & github'
        ],
        'pattern': r'\b(?:git(?:\s+version\s+control)?|github|gitlab)\b',
    },
    'REST API': {
        'canonical': 'REST API',
        'category': 'Backend Development',
        'aliases': [
            'rest api', 'rest apis', 'restful api', 'restful apis',
            'rest api development', 'restful api development', 'restful services',
            'rest endpoints', 'django rest framework', 'drf', 'api development',
            'rest api design', 'web api'
        ],
        'pattern': r'\b(?:rest(?:ful)?\s+apis?|rest(?:ful)?\s+api\s+development|restful\s+services|django\s+rest\s+framework|drf|rest\s+endpoints)\b',
    },
    'Testing & Debugging': {
        'canonical': 'Testing & Debugging',
        'category': 'Testing & Quality',
        'aliases': [
            'testing & debugging', 'testing and debugging', 'testing', 'debugging',
            'unit testing', 'test cases', 'pytest', 'unittest', 'automated testing',
            'test-driven development', 'tdd'
        ],
        'pattern': r'\b(?:testing\s*(?:&|and)\s*debugging|unit\s+testing|automated\s+testing|debugging|pytest|unittest|test\s+cases|tdd)\b',
    },
    'NumPy': {
        'canonical': 'NumPy',
        'category': 'Data Analysis',
        'aliases': ['numpy'],
        'pattern': r'\bnumpy\b',
    },
    'Pandas': {
        'canonical': 'Pandas',
        'category': 'Data Analysis',
        'aliases': ['pandas'],
        'pattern': r'\bpandas\b',
    },
    'Docker': {
        'canonical': 'Docker',
        'category': 'DevOps & Deployment',
        'aliases': ['docker', 'containerization', 'dockerfile', 'docker-compose', 'containers'],
        'pattern': r'\b(?:docker(?:file|-compose)?|containerization)\b',
    },
    'Excel': {
        'canonical': 'Excel',
        'category': 'Data Analysis',
        'aliases': ['excel', 'microsoft excel', 'ms excel', 'spreadsheets'],
        'pattern': r'\b(?:ms\s+)?excel\b|\bspreadsheets\b',
    },
    'Power BI': {
        'canonical': 'Power BI',
        'category': 'Data Analysis',
        'aliases': ['power bi', 'powerbi', 'ms power bi'],
        'pattern': r'\bpower\s*bi\b',
    },
    'Statistics': {
        'canonical': 'Statistics',
        'category': 'Data Analysis',
        'aliases': [
            'statistics', 'statistical analysis', 'probability & statistics',
            'probability and statistics', 'stats'
        ],
        'pattern': r'\b(?:statistics|statistical\s+analysis|probability\s*(?:&|and)\s*statistics)\b',
    },
}

# Synonyms for canonical names used in different catalog entries
CANONICAL_SYNONYMS: Dict[str, str] = {
    'rest api development': 'REST API',
    'restful api': 'REST API',
    'django rest framework': 'REST API',
    'drf': 'REST API',
    'oop': 'Object-Oriented Programming',
    'object oriented programming': 'Object-Oriented Programming',
    'dsa': 'Data Structures & Algorithms',
    'data structures and algorithms': 'Data Structures & Algorithms',
    'html5': 'HTML',
    'css3': 'CSS',
    'html and css': 'HTML & CSS',
    'html/css': 'HTML & CSS',
    'postgres': 'PostgreSQL',
    'testing and debugging': 'Testing & Debugging',
    'debugging': 'Testing & Debugging',
    'unit testing': 'Testing & Debugging',
}


def normalize_text(text: str) -> str:
    """Standardizes string casing, whitespace, and uniform separators."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def canonicalize_skill_name(raw_name: str) -> str:
    """
    Given any raw skill string (e.g. 'OOP basics', 'Postgres', 'DRF', 'HTML5'),
    resolves and returns the canonical Skill name in SKILL_CATALOG, or cleaned title case.
    """
    if not raw_name:
        return ""

    cleaned = normalize_text(raw_name)

    # 1. Exact match in catalog keys (case-insensitive)
    for canonical in SKILL_CATALOG:
        if cleaned == canonical.lower():
            return canonical

    # 2. Check canonical synonyms
    if cleaned in CANONICAL_SYNONYMS:
        return CANONICAL_SYNONYMS[cleaned]

    # 3. Check aliases in SKILL_CATALOG
    for canonical, data in SKILL_CATALOG.items():
        if cleaned in [a.lower() for a in data.get('aliases', [])]:
            return canonical

    # 4. Regex pattern matching
    for canonical, data in SKILL_CATALOG.items():
        pattern = data.get('pattern')
        if pattern and re.search(f"^(?:{pattern})$", cleaned, re.IGNORECASE):
            return canonical

    # Fallback to normalized title-case
    return raw_name.strip()


def extract_skills_with_evidence(
    text: str,
    target_catalog_skills: Optional[List[str]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Scans free text (resume, project description, bio) and returns all detected
    canonical skills alongside matched excerpts, evidence strength, and sections.

    Returns dict mapping canonical skill name -> {
        'canonical': str,
        'category': str,
        'matched_alias': str,
        'excerpt': str,
        'strength': 'strong' | 'moderate' | 'basic',
        'is_project_evidence': bool,
        'occurrences': int,
    }
    """
    if not text or not text.strip():
        return {}

    norm_text = text  # preserve case for excerpt extraction, lower for matching
    low_text = text.lower()
    results: Dict[str, Dict[str, Any]] = {}

    # Identify project vs skills sections
    sections = _split_into_sections(norm_text)

    # Check each catalog item
    for canonical, data in SKILL_CATALOG.items():
        # If target catalog is specified, we can still match components to build compounds
        pattern_str = data.get('pattern')
        if not pattern_str:
            continue

        pattern = re.compile(pattern_str, re.IGNORECASE)
        matches = list(pattern.finditer(norm_text))

        if matches:
            # Check all matches to find if any appears in a project/experience section
            is_proj = False
            best_strength = 'basic'
            best_excerpt = None
            first_alias = matches[0].group(0)

            for m in matches:
                m_alias = m.group(0)
                # Determine excerpt around the match
                start = max(0, m.start() - 60)
                end = min(len(norm_text), m.end() + 60)
                raw_excerpt = norm_text[start:end].replace('\n', ' ').strip()
                curr_excerpt = f"...{raw_excerpt}..."

                m_proj, m_strength = _determine_evidence_context(m.start(), norm_text, sections, m_alias)
                if m_proj:
                    is_proj = True
                
                # Priority: strong > moderate > basic
                strength_ranks = {'basic': 1, 'moderate': 2, 'strong': 3}
                if strength_ranks.get(m_strength, 1) >= strength_ranks.get(best_strength, 1):
                    best_strength = m_strength
                    best_excerpt = curr_excerpt

            if not best_excerpt:
                start = max(0, matches[0].start() - 60)
                end = min(len(norm_text), matches[0].end() + 60)
                best_excerpt = f"...{norm_text[start:end].replace(chr(10), ' ').strip()}..."

            results[canonical] = {
                'canonical': canonical,
                'category': data.get('category', 'Technical Skills'),
                'matched_alias': first_alias,
                'excerpt': best_excerpt,
                'strength': best_strength,
                'is_project_evidence': is_proj,
                'occurrences': len(matches),
            }

    # Handle compound skills (like HTML & CSS):
    # 1. If HTML and CSS both detected, also register 'HTML & CSS'
    if 'HTML' in results and 'CSS' in results and 'HTML & CSS' not in results:
        html_res = results['HTML']
        css_res = results['CSS']
        is_proj = html_res['is_project_evidence'] or css_res['is_project_evidence']
        strength = 'strong' if (html_res['strength'] == 'strong' or css_res['strength'] == 'strong') else 'moderate'
        combined_excerpt = f"HTML ({html_res['matched_alias']}) and CSS ({css_res['matched_alias']}) demonstrated."
        results['HTML & CSS'] = {
            'canonical': 'HTML & CSS',
            'category': 'Frontend Development',
            'matched_alias': f"{html_res['matched_alias']} + {css_res['matched_alias']}",
            'excerpt': combined_excerpt,
            'strength': strength,
            'is_project_evidence': is_proj,
            'occurrences': html_res['occurrences'] + css_res['occurrences'],
        }

    # 2. If 'HTML & CSS' was detected directly, ensure individual HTML and CSS are also credited
    if 'HTML & CSS' in results:
        compound = results['HTML & CSS']
        for comp in ['HTML', 'CSS']:
            if comp not in results:
                results[comp] = {
                    'canonical': comp,
                    'category': 'Frontend Development',
                    'matched_alias': compound['matched_alias'],
                    'excerpt': compound['excerpt'],
                    'strength': compound['strength'],
                    'is_project_evidence': compound['is_project_evidence'],
                    'occurrences': compound['occurrences'],
                }

    return results


def _split_into_sections(text: str) -> List[Tuple[str, int, int]]:
    """
    Identifies common resume section boundaries and returns:
    [(section_type, start_idx, end_idx), ...]
    section_type can be 'projects', 'skills', 'experience', 'education', 'general'
    """
    headings = [
        (r'(?i)\b(?:projects?|academic\s+projects?|key\s+projects?|personal\s+projects?)\b', 'projects'),
        (r'(?i)\b(?:work\s+experience|experience|employment|professional\s+experience|internships?)\b', 'experience'),
        (r'(?i)\b(?:technical\s+skills|skills\s*(?:&|and)\s*tools|skills|core\s+concepts|core\s+competencies|programming)\b', 'skills'),
        (r'(?i)\b(?:education|academic\s+background|qualifications)\b', 'education'),
    ]

    boundaries = []
    for pattern, sec_type in headings:
        for m in re.finditer(pattern, text):
            boundaries.append((m.start(), sec_type))

    boundaries.sort(key=lambda x: x[0])

    sections = []
    prev_idx = 0
    prev_type = 'general'

    for idx, sec_type in boundaries:
        if idx > prev_idx:
            sections.append((prev_type, prev_idx, idx))
        prev_idx = idx
        prev_type = sec_type

    sections.append((prev_type, prev_idx, len(text)))
    return sections


def _determine_evidence_context(
    match_pos: int,
    full_text: str,
    sections: List[Tuple[str, int, int]],
    matched_alias: str
) -> Tuple[bool, str]:
    """
    Determines whether evidence is project-based and its strength
    ('strong', 'moderate', 'basic').
    """
    # Find which section the match falls in
    active_section = 'general'
    for sec_type, start, end in sections:
        if start <= match_pos < end:
            active_section = sec_type
            break

    # Look at surrounding 100 characters for context clues
    ctx_start = max(0, match_pos - 80)
    ctx_end = min(len(full_text), match_pos + 80)
    surrounding = full_text[ctx_start:ctx_end].lower()

    # Check for practical indicators
    has_action_verbs = bool(re.search(
        r'\b(?:built|developed|implemented|created|designed|integrated|engineered|deployed|applied|used|using|scripting)\b',
        surrounding
    ))
    has_basic_cues = bool(re.search(
        r'\b(?:basic|basics|introductory|beginner|learning|familiar|knowledge\s+of)\b',
        surrounding
    ))
    is_in_project = (active_section == 'projects')
    is_in_experience = (active_section == 'experience')

    if (is_in_project or is_in_experience) and (has_action_verbs or 'technology:' in surrounding or 'tech stack:' in surrounding or 'technologies:' in surrounding):
        strength = 'strong'
    elif has_basic_cues:
        strength = 'basic'
    elif is_in_project or is_in_experience:
        strength = 'strong' if has_action_verbs else 'moderate'
    elif active_section == 'skills':
        strength = 'basic'
    else:
        strength = 'basic' if not has_action_verbs else 'moderate'

    return (is_in_project or is_in_experience), strength
