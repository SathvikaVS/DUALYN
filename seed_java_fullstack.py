"""
seed_java_fullstack.py

Standalone seeding script for the 'Java Full Stack Developer' Job Role and its
associated competencies in DUALYN.

Usage:
    python seed_java_fullstack.py
    or
    venv/Scripts/python seed_java_fullstack.py
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from jobs.models import JobRole, JobSkill
from skills.models import Skill

ROLE_DATA = {
    'title': 'Java Full Stack Developer',
    'description': (
        'Develop and maintain full-stack web applications using Java, Spring Boot, '
        'HTML, CSS, JavaScript, and SQL. Build secure backend services, design responsive '
        'user interfaces, manage relational databases, and integrate frontend and backend '
        'components. Apply object-oriented programming, REST API development, debugging, '
        'testing, and Git version control. Follow software development best practices to '
        'build scalable, maintainable, and reliable applications.'
    ),
    'skills': [
        {
            'name': 'Java',
            'importance_weight': 5,
            'is_fundamental': True,
            'required_level': 'Advanced',
            'role_priority': 'high',
            'category': 'Programming',
            'why_it_matters': 'Core language for building secure, scalable backend services and enterprise web applications.',
        },
        {
            'name': 'OOP',
            'importance_weight': 5,
            'is_fundamental': True,
            'required_level': 'Advanced',
            'role_priority': 'high',
            'category': 'Core Concepts',
            'why_it_matters': 'Object-oriented principles (encapsulation, inheritance, polymorphism, abstraction) for modular code design.',
        },
        {
            'name': 'SQL',
            'importance_weight': 5,
            'is_fundamental': True,
            'required_level': 'Intermediate',
            'role_priority': 'high',
            'category': 'Databases',
            'why_it_matters': 'Relational data persistence, schema queries, joins, and data integrity operations.',
        },
        {
            'name': 'Spring Boot',
            'importance_weight': 5,
            'is_fundamental': True,
            'required_level': 'Intermediate',
            'role_priority': 'high',
            'category': 'Backend Frameworks',
            'why_it_matters': 'Primary enterprise Java framework for building microservices, REST APIs, and production backends.',
        },
        {
            'name': 'HTML',
            'importance_weight': 4,
            'is_fundamental': True,
            'required_level': 'Intermediate',
            'role_priority': 'high',
            'category': 'Frontend Development',
            'why_it_matters': 'Standard markup language for structuring web pages and user interface components.',
        },
        {
            'name': 'CSS',
            'importance_weight': 4,
            'is_fundamental': True,
            'required_level': 'Intermediate',
            'role_priority': 'high',
            'category': 'Frontend Development',
            'why_it_matters': 'Styling and layout language for responsive user interface presentation and cross-device aesthetics.',
        },
        {
            'name': 'JavaScript',
            'importance_weight': 5,
            'is_fundamental': True,
            'required_level': 'Intermediate',
            'role_priority': 'high',
            'category': 'Frontend Development',
            'why_it_matters': 'Client-side programming language for dynamic web UI, DOM manipulation, and asynchronous API calls.',
        },
        {
            'name': 'REST APIs',
            'importance_weight': 4,
            'is_fundamental': True,
            'required_level': 'Intermediate',
            'role_priority': 'high',
            'category': 'Backend Development',
            'why_it_matters': 'Architectural style for designing standardized HTTP client-server interfaces and endpoints.',
        },
        {
            'name': 'Git',
            'importance_weight': 3,
            'is_fundamental': False,
            'required_level': 'Intermediate',
            'role_priority': 'medium',
            'category': 'Tools & Version Control',
            'why_it_matters': 'Distributed version control system for team collaboration, branching workflows, and tracking changes.',
        },
        {
            'name': 'Database Design',
            'importance_weight': 4,
            'is_fundamental': True,
            'required_level': 'Intermediate',
            'role_priority': 'high',
            'category': 'Databases',
            'why_it_matters': 'Designing normalized relational schemas, entity relationships, primary/foreign keys, and indexes.',
        },
    ]
}


def seed_java_full_stack():
    """
    Seeds the Java Full Stack Developer job role and its associated skills idempotently.
    """
    print("=" * 60)
    print("Seeding 'Java Full Stack Developer' Job Role & Skills")
    print("=" * 60)

    with transaction.atomic():
        # 1. Create or update JobRole
        role, created = JobRole.objects.get_or_create(
            title=ROLE_DATA['title'],
            defaults={'description': ROLE_DATA['description']}
        )
        if not created and role.description != ROLE_DATA['description']:
            role.description = ROLE_DATA['description']
            role.save()
            print(f"[UPDATED] JobRole: {role.title}")
        elif created:
            print(f"[CREATED] JobRole: {role.title}")
        else:
            print(f"[EXISTS]  JobRole: {role.title}")

        # 2. Seed Skills & JobSkill mappings
        for sdata in ROLE_DATA['skills']:
            skill_name = sdata['name']
            category = sdata.get('category', 'Technical Skills')

            skill, skill_created = Skill.objects.get_or_create(
                name=skill_name,
                defaults={'category': category}
            )
            if skill_created:
                print(f"  + [NEW SKILL] {skill.name} (category: {skill.category})")
            elif skill.category != category and category:
                skill.category = category
                skill.save()

            # Create or update JobSkill
            job_skill, js_created = JobSkill.objects.get_or_create(
                job_role=role,
                skill=skill,
                defaults={
                    'importance_weight': sdata['importance_weight'],
                    'is_fundamental': sdata['is_fundamental'],
                    'required_level': sdata['required_level'],
                    'role_priority': sdata['role_priority'],
                    'why_it_matters': sdata['why_it_matters'],
                    'category': category,
                }
            )

            if not js_created:
                # Update attributes to match definition
                updated = False
                if job_skill.importance_weight != sdata['importance_weight']:
                    job_skill.importance_weight = sdata['importance_weight']
                    updated = True
                if job_skill.is_fundamental != sdata['is_fundamental']:
                    job_skill.is_fundamental = sdata['is_fundamental']
                    updated = True
                if job_skill.required_level != sdata['required_level']:
                    job_skill.required_level = sdata['required_level']
                    updated = True
                if job_skill.role_priority != sdata['role_priority']:
                    job_skill.role_priority = sdata['role_priority']
                    updated = True
                if job_skill.why_it_matters != sdata['why_it_matters']:
                    job_skill.why_it_matters = sdata['why_it_matters']
                    updated = True
                if job_skill.category != category:
                    job_skill.category = category
                    updated = True
                if updated:
                    job_skill.save()
                    print(f"  ~ [UPDATED SKILL MAP] {skill.name} -> Weight {job_skill.importance_weight}, Priority {job_skill.role_priority}")
                else:
                    print(f"  = [UNCHANGED SKILL MAP] {skill.name} -> Weight {job_skill.importance_weight}, Priority {job_skill.role_priority}")
            else:
                print(f"  + [ADDED SKILL MAP] {skill.name} -> Weight {job_skill.importance_weight}, Fundamental: {job_skill.is_fundamental}, Level: {job_skill.required_level}, Priority: {job_skill.role_priority}")

    total_skills = role.job_skills.count()
    print("=" * 60)
    print(f"SUCCESS: 'Java Full Stack Developer' configured with {total_skills} skills.")
    print("=" * 60)


if __name__ == '__main__':
    seed_java_full_stack()
