"""
jobs/services/role_profiles.py
Defines canonical competency profiles and weights for supported job roles:
- Python Developer
- Django Developer
- Backend Developer
- Full-Stack Developer
- Data Analyst
- Java Full Stack Developer

Provides synchronization utilities to populate and maintain JobRole and JobSkill records.
"""
from typing import Dict, List, Any
from django.db import transaction
from skills.models import Skill
from jobs.models import JobRole, JobSkill
from skills.services.normalization import SKILL_CATALOG, canonicalize_skill_name


ROLE_PROFILES: Dict[str, Dict[str, Any]] = {
    'Python Developer': {
        'description': 'Designs, implements, and maintains backend services, automation scripts, and application logic using Python.',
        'competencies': [
            {
                'skill': 'Python',
                'weight': 5,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Programming',
                'why_it_matters': 'Core language for writing efficient algorithms, scripting, and backend workflows.',
            },
            {
                'skill': 'Object-Oriented Programming',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Core Concepts',
                'why_it_matters': 'Essential for structuring modular classes, inheritance, encapsulation, and clean domain models.',
            },
            {
                'skill': 'Data Structures & Algorithms',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Core Concepts',
                'why_it_matters': 'Fundamental for computational problem-solving, time/space complexity optimization, and scalable code.',
            },
            {
                'skill': 'SQL',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Databases',
                'why_it_matters': 'Critical for relational data persistence, writing queries, and interacting with ORMs.',
            },
            {
                'skill': 'Git',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Tools & Version Control',
                'why_it_matters': 'Standard version control system for collaborative branches, pull requests, and history tracking.',
            },
            {
                'skill': 'Testing & Debugging',
                'weight': 3,
                'is_fundamental': False,
                'required_level': 'Intermediate',
                'priority': 'medium',
                'category': 'Testing & Quality',
                'why_it_matters': 'Ensures production reliability through unit tests, test fixtures, and systematic bug isolation.',
            },
            {
                'skill': 'Django',
                'weight': 4,
                'is_fundamental': False,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Backend Frameworks',
                'why_it_matters': 'High-productivity web framework for routing, MTV architecture, authentication, and database ORM.',
            },
            {
                'skill': 'REST API',
                'weight': 4,
                'is_fundamental': False,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Backend Development',
                'why_it_matters': 'Standard HTTP interface for client-server communication and JSON serialization.',
            },
            {
                'skill': 'PostgreSQL',
                'weight': 3,
                'is_fundamental': False,
                'required_level': 'Intermediate',
                'priority': 'medium',
                'category': 'Databases',
                'why_it_matters': 'Production-grade relational database commonly paired with Python backends.',
            },
            {
                'skill': 'HTML & CSS',
                'weight': 2,
                'is_fundamental': False,
                'required_level': 'Beginner',
                'priority': 'low',
                'category': 'Frontend Development',
                'why_it_matters': 'Useful for template rendering, responsive design basics, and full-stack collaboration.',
            },
            {
                'skill': 'JavaScript',
                'weight': 2,
                'is_fundamental': False,
                'required_level': 'Beginner',
                'priority': 'low',
                'category': 'Frontend Development',
                'why_it_matters': 'Client-side scripting language for frontend interactivity and API consumption.',
            },
            {
                'skill': 'NumPy',
                'weight': 1,
                'is_fundamental': False,
                'required_level': 'Beginner',
                'priority': 'low',
                'category': 'Data Analysis',
                'why_it_matters': 'Specialization skill for numerical calculations; optional for general web backend roles.',
            },
            {
                'skill': 'Pandas',
                'weight': 1,
                'is_fundamental': False,
                'required_level': 'Beginner',
                'priority': 'low',
                'category': 'Data Analysis',
                'why_it_matters': 'Specialization library for tabular datasets; optional for general web backend roles.',
            },
        ],
    },
    'Django Developer': {
        'description': 'Specializes in creating robust, scalable web applications, REST APIs, and database models using the Django framework.',
        'competencies': [
            {
                'skill': 'Django',
                'weight': 5,
                'is_fundamental': True,
                'required_level': 'Advanced',
                'priority': 'high',
                'category': 'Backend Frameworks',
                'why_it_matters': 'Core web framework for models, views, templates, signals, forms, and middleware.',
            },
            {
                'skill': 'Python',
                'weight': 5,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Programming',
                'why_it_matters': 'Foundational language for writing Django views, models, and custom management commands.',
            },
            {
                'skill': 'REST API',
                'weight': 5,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Backend Development',
                'why_it_matters': 'Crucial for building API endpoints using Django REST Framework (DRF) and JSON serialization.',
            },
            {
                'skill': 'SQL',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Databases',
                'why_it_matters': 'Understanding database operations behind Django ORM querysets, joins, and migrations.',
            },
            {
                'skill': 'Git',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Tools & Version Control',
                'why_it_matters': 'Standard version control for team codebases and deployment workflows.',
            },
            {
                'skill': 'Object-Oriented Programming',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Core Concepts',
                'why_it_matters': 'Underpins Django class-based views (CBVs), model inheritance, and custom managers.',
            },
            {
                'skill': 'PostgreSQL',
                'weight': 4,
                'is_fundamental': False,
                'required_level': 'Intermediate',
                'priority': 'medium',
                'category': 'Databases',
                'why_it_matters': 'Standard production database for Django applications with native JSONField support.',
            },
            {
                'skill': 'Testing & Debugging',
                'weight': 4,
                'is_fundamental': False,
                'required_level': 'Intermediate',
                'priority': 'medium',
                'category': 'Testing & Quality',
                'why_it_matters': 'Writing automated TestCase suites for models, forms, and API endpoints.',
            },
            {
                'skill': 'HTML & CSS',
                'weight': 3,
                'is_fundamental': False,
                'required_level': 'Intermediate',
                'priority': 'medium',
                'category': 'Frontend Development',
                'why_it_matters': 'Required for Django template rendering, forms styling, and responsive UI design.',
            },
            {
                'skill': 'JavaScript',
                'weight': 3,
                'is_fundamental': False,
                'required_level': 'Beginner',
                'priority': 'medium',
                'category': 'Frontend Development',
                'why_it_matters': 'Handles asynchronous UI updates, Fetch/Axios requests, and DOM manipulation.',
            },
            {
                'skill': 'Data Structures & Algorithms',
                'weight': 3,
                'is_fundamental': False,
                'required_level': 'Intermediate',
                'priority': 'low',
                'category': 'Core Concepts',
                'why_it_matters': 'Helps write algorithmic code, caching strategies, and efficient data processing.',
            },
            {
                'skill': 'Docker',
                'weight': 2,
                'is_fundamental': False,
                'required_level': 'Beginner',
                'priority': 'low',
                'category': 'DevOps & Deployment',
                'why_it_matters': 'Containerizing Django applications, database services, and dependencies.',
            },
        ],
    },
    'Backend Developer': {
        'description': 'Architects and builds server-side applications, database pipelines, and APIs focused on security, speed, and scalability.',
        'competencies': [
            {
                'skill': 'Python',
                'weight': 5,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Programming',
                'why_it_matters': 'Core backend programming language for business logic, services, and asynchronous tasks.',
            },
            {
                'skill': 'REST API',
                'weight': 5,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Backend Development',
                'why_it_matters': 'Building secure, performant RESTful endpoints, token authentication, and API specs.',
            },
            {
                'skill': 'SQL',
                'weight': 5,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Databases',
                'why_it_matters': 'Complex queries, schema design, database transactions, indexing, and connection pools.',
            },
            {
                'skill': 'PostgreSQL',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Databases',
                'why_it_matters': 'Enterprise relational database for ACID compliance and performance optimization.',
            },
            {
                'skill': 'Object-Oriented Programming',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Core Concepts',
                'why_it_matters': 'Essential design patterns (repository, service layer, factory) in backend systems.',
            },
            {
                'skill': 'Data Structures & Algorithms',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Core Concepts',
                'why_it_matters': 'Designing high-throughput data processing algorithms and memory-efficient data structures.',
            },
            {
                'skill': 'Git',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Tools & Version Control',
                'why_it_matters': 'Version control, git rebase/merge, feature branches, and CI/CD triggers.',
            },
            {
                'skill': 'Django',
                'weight': 4,
                'is_fundamental': False,
                'required_level': 'Intermediate',
                'priority': 'medium',
                'category': 'Backend Frameworks',
                'why_it_matters': 'Robust framework for rapid backend development and admin dashboards.',
            },
            {
                'skill': 'Testing & Debugging',
                'weight': 4,
                'is_fundamental': False,
                'required_level': 'Intermediate',
                'priority': 'medium',
                'category': 'Testing & Quality',
                'why_it_matters': 'Integration tests, mock services, and logging for server health.',
            },
            {
                'skill': 'Docker',
                'weight': 3,
                'is_fundamental': False,
                'required_level': 'Beginner',
                'priority': 'low',
                'category': 'DevOps & Deployment',
                'why_it_matters': 'Deploying microservices and uniform local development environments.',
            },
        ],
    },
    'Full-Stack Developer': {
        'description': 'Delivers end-to-end features spanning dynamic client user interfaces, responsive designs, and robust server-side APIs.',
        'competencies': [
            {
                'skill': 'JavaScript',
                'weight': 5,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Frontend Development',
                'why_it_matters': 'Primary language of the modern web for browser interfaces, DOM events, and async fetch.',
            },
            {
                'skill': 'Python',
                'weight': 5,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Programming',
                'why_it_matters': 'Server-side language for data processing, validation, and backend routes.',
            },
            {
                'skill': 'HTML & CSS',
                'weight': 5,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Frontend Development',
                'why_it_matters': 'Structuring web pages, responsive layouts, flexbox, grid, and CSS styling.',
            },
            {
                'skill': 'Django',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Backend Frameworks',
                'why_it_matters': 'Connects frontend templates with backend database models and routing.',
            },
            {
                'skill': 'REST API',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Backend Development',
                'why_it_matters': 'Bridges the gap between frontend client apps and server databases.',
            },
            {
                'skill': 'SQL',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Databases',
                'why_it_matters': 'Database queries, schema definitions, and ORM operations.',
            },
            {
                'skill': 'Git',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Tools & Version Control',
                'why_it_matters': 'Managing combined frontend and backend code repositories.',
            },
            {
                'skill': 'PostgreSQL',
                'weight': 3,
                'is_fundamental': False,
                'required_level': 'Intermediate',
                'priority': 'medium',
                'category': 'Databases',
                'why_it_matters': 'Reliable persistence layer for full-stack deployments.',
            },
            {
                'skill': 'Testing & Debugging',
                'weight': 3,
                'is_fundamental': False,
                'required_level': 'Intermediate',
                'priority': 'medium',
                'category': 'Testing & Quality',
                'why_it_matters': 'Full-stack debugging across browser developer tools and server logs.',
            },
            {
                'skill': 'Object-Oriented Programming',
                'weight': 3,
                'is_fundamental': False,
                'required_level': 'Intermediate',
                'priority': 'low',
                'category': 'Core Concepts',
                'why_it_matters': 'Clean code architecture and component structuring.',
            },
        ],
    },
    'Data Analyst': {
        'description': 'Extracts actionable business insights through SQL queries, spreadsheet modeling, statistical analysis, and interactive dashboards.',
        'competencies': [
            {
                'skill': 'SQL',
                'weight': 5,
                'is_fundamental': True,
                'required_level': 'Advanced',
                'priority': 'high',
                'category': 'Databases',
                'why_it_matters': 'Primary language for extracting, aggregating, joining, and filtering dataset records.',
            },
            {
                'skill': 'Excel',
                'weight': 5,
                'is_fundamental': True,
                'required_level': 'Advanced',
                'priority': 'high',
                'category': 'Data Analysis',
                'why_it_matters': 'Universal tool for pivot tables, VLOOKUP/XLOOKUP, summary modeling, and quick audits.',
            },
            {
                'skill': 'Python',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Programming',
                'why_it_matters': 'Automating repetitive data tasks, writing cleaning scripts, and statistical calculations.',
            },
            {
                'skill': 'Statistics',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Data Analysis',
                'why_it_matters': 'Descriptive and inferential statistics, hypothesis testing, distributions, and variance.',
            },
            {
                'skill': 'Power BI',
                'weight': 4,
                'is_fundamental': False,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Data Analysis',
                'why_it_matters': 'Designing interactive stakeholder reports, data models, and DAX calculations.',
            },
            {
                'skill': 'Pandas',
                'weight': 4,
                'is_fundamental': False,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Data Analysis',
                'why_it_matters': 'High-performance dataframe manipulation, missing value imputation, and aggregations.',
            },
            {
                'skill': 'NumPy',
                'weight': 3,
                'is_fundamental': False,
                'required_level': 'Intermediate',
                'priority': 'medium',
                'category': 'Data Analysis',
                'why_it_matters': 'Multi-dimensional arrays, mathematical functions, and vectorized operations.',
            },
            {
                'skill': 'Git',
                'weight': 2,
                'is_fundamental': False,
                'required_level': 'Beginner',
                'priority': 'low',
                'category': 'Tools & Version Control',
                'why_it_matters': 'Versioning analysis notebooks and automated data extraction scripts.',
            },
        ],
    },
    'Java Full Stack Developer': {
        'description': (
            'Develop and maintain full-stack web applications using Java, Spring Boot, '
            'HTML, CSS, JavaScript, and SQL. Build secure backend services, design responsive '
            'user interfaces, manage relational databases, and integrate frontend and backend '
            'components. Apply object-oriented programming, REST API development, debugging, '
            'testing, and Git version control. Follow software development best practices to '
            'build scalable, maintainable, and reliable applications.'
        ),
        'competencies': [
            {
                'skill': 'Java',
                'weight': 5,
                'is_fundamental': True,
                'required_level': 'Advanced',
                'priority': 'high',
                'category': 'Programming',
                'why_it_matters': 'Core language for building secure, scalable backend services and enterprise web applications.',
            },
            {
                'skill': 'OOP',
                'weight': 5,
                'is_fundamental': True,
                'required_level': 'Advanced',
                'priority': 'high',
                'category': 'Core Concepts',
                'why_it_matters': 'Object-oriented principles (encapsulation, inheritance, polymorphism, abstraction) for modular code design.',
            },
            {
                'skill': 'SQL',
                'weight': 5,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Databases',
                'why_it_matters': 'Relational data persistence, schema queries, joins, and data integrity operations.',
            },
            {
                'skill': 'Spring Boot',
                'weight': 5,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Backend Frameworks',
                'why_it_matters': 'Primary enterprise Java framework for building microservices, REST APIs, and production backends.',
            },
            {
                'skill': 'HTML',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Frontend Development',
                'why_it_matters': 'Standard markup language for structuring web pages and user interface components.',
            },
            {
                'skill': 'CSS',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Frontend Development',
                'why_it_matters': 'Styling and layout language for responsive user interface presentation and cross-device aesthetics.',
            },
            {
                'skill': 'JavaScript',
                'weight': 5,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Frontend Development',
                'why_it_matters': 'Client-side programming language for dynamic web UI, DOM manipulation, and asynchronous API calls.',
            },
            {
                'skill': 'REST APIs',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Backend Development',
                'why_it_matters': 'Architectural style for designing standardized HTTP client-server interfaces and endpoints.',
            },
            {
                'skill': 'Git',
                'weight': 3,
                'is_fundamental': False,
                'required_level': 'Intermediate',
                'priority': 'medium',
                'category': 'Tools & Version Control',
                'why_it_matters': 'Distributed version control system for team collaboration, branching workflows, and tracking changes.',
            },
            {
                'skill': 'Database Design',
                'weight': 4,
                'is_fundamental': True,
                'required_level': 'Intermediate',
                'priority': 'high',
                'category': 'Databases',
                'why_it_matters': 'Designing normalized relational schemas, entity relationships, primary/foreign keys, and indexes.',
            },
        ],
    },
}


def sync_role_profiles_to_db() -> None:
    """
    Synchronizes the canonical competency profiles into JobRole and JobSkill records.
    Ensures all 5 target roles and required skills exist with consistent importance weights.
    Idempotent and safe to call anytime.
    """
    with transaction.atomic():
        # Ensure all catalog skills exist in the Skill model
        for name, data in SKILL_CATALOG.items():
            skill, _ = Skill.objects.get_or_create(
                name=name,
                defaults={'category': data.get('category', 'Technical Skills')}
            )
            # Ensure normalized name is updated
            if skill.category != data.get('category', ''):
                skill.category = data.get('category', '')
                skill.save()

        # Synchronize roles
        for role_title, role_data in ROLE_PROFILES.items():
            job_role, _ = JobRole.objects.get_or_create(
                title=role_title,
                defaults={'description': role_data['description']}
            )
            if not job_role.description:
                job_role.description = role_data['description']
                job_role.save()

            for comp in role_data['competencies']:
                skill_obj = Skill.objects.filter(name=comp['skill']).first()
                if not skill_obj:
                    skill_obj = Skill.objects.create(
                        name=comp['skill'],
                        category=comp.get('category', '')
                    )

                job_skill, _ = JobSkill.objects.get_or_create(
                    job_role=job_role,
                    skill=skill_obj,
                    defaults={
                        'importance_weight': comp['weight'],
                        'is_fundamental': comp['is_fundamental'],
                        'required_level': comp.get('required_level', 'Intermediate'),
                        'role_priority': comp.get('priority', 'medium'),
                        'why_it_matters': comp.get('why_it_matters', ''),
                        'category': comp.get('category', ''),
                    }
                )
                # Update attributes if they were defaults
                updated = False
                if job_skill.importance_weight != comp['weight']:
                    job_skill.importance_weight = comp['weight']
                    updated = True
                if job_skill.is_fundamental != comp['is_fundamental']:
                    job_skill.is_fundamental = comp['is_fundamental']
                    updated = True
                if comp.get('why_it_matters') and job_skill.why_it_matters != comp['why_it_matters']:
                    job_skill.why_it_matters = comp['why_it_matters']
                    updated = True
                if comp.get('required_level') and job_skill.required_level != comp['required_level']:
                    job_skill.required_level = comp['required_level']
                    updated = True
                if comp.get('priority') and job_skill.role_priority != comp['priority']:
                    job_skill.role_priority = comp['priority']
                    updated = True
                if comp.get('category') and job_skill.category != comp['category']:
                    job_skill.category = comp['category']
                    updated = True
                if updated:
                    job_skill.save()
