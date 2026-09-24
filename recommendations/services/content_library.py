# Deterministic learning-step library, keyed by normalized skill name.
# MVP scope: covers Section 8's example job roles. Extend as more JobSkills are added.

SKILL_STEPS = {
    'rest apis': [
        "Learn HTTP fundamentals (methods, status codes, headers)",
        "Understand REST architectural principles",
        "Practice sending requests with a tool like Postman",
        "Learn Django REST Framework basics",
        "Build a simple CRUD API",
        "Learn API authentication (tokens, sessions)",
        "Build a real-world REST API project",
    ],
    'testing': [
        "Learn why automated testing matters",
        "Write your first unit test with Django's TestCase",
        "Learn about test fixtures and setUp/tearDown",
        "Practice testing views and models",
        "Learn about test coverage tools",
    ],
    'docker': [
        "Understand what containers solve vs virtual machines",
        "Install Docker and run your first container",
        "Write a Dockerfile for a Django project",
        "Learn docker-compose for multi-container setups",
        "Containerize one of your existing projects",
    ],
    'sql': [
        "Learn basic SELECT, WHERE, JOIN queries",
        "Practice writing queries against a real database",
        "Learn about indexes and query performance",
        "Learn Django ORM's relationship to raw SQL",
    ],
    'git': [
        "Learn basic commands: add, commit, push, pull",
        "Practice branching and merging",
        "Learn to resolve merge conflicts",
        "Practice collaborative workflows (pull requests)",
    ],
}

DEFAULT_STEPS = [
    "Research foundational concepts for this skill",
    "Find a structured course or official documentation",
    "Practice with small exercises",
    "Apply it in a real project",
]


def get_steps_for_skill(skill_name):
    key = skill_name.strip().lower()
    return SKILL_STEPS.get(key, DEFAULT_STEPS)