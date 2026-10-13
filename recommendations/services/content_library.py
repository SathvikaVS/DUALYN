"""
recommendations/services/content_library.py
Deterministic learning-step and pedagogical metadata library for DUALYN.
Provides phased progression mapping, learning outcomes, practical task ideas,
and actionable step-by-step guides for technical competencies.
"""
from typing import Dict, List, Any
from skills.services.normalization import canonicalize_skill_name


SKILL_METADATA: Dict[str, Dict[str, Any]] = {
    'Python': {
        'default_phase': 1,
        'why_it_matters': "Python is the core language powering your backend logic, automation scripts, and data processing.",
        'learning_outcome': "Master Python data types, functions, exception handling, list comprehensions, and generators.",
        'task_idea': "Build a command-line expense tracker that parses JSON/CSV data and computes spending statistics.",
        'steps': [
            "Review Python control flow, functions, and standard library modules.",
            "Practice writing modular functions with comprehensive type hints and docstrings.",
            "Master Python error handling, custom exceptions, and context managers (with statements).",
            "Learn Python generators, list/dict comprehensions, and itertools.",
            "Write small automation scripts to manipulate files and parse API payloads.",
        ],
    },
    'Object-Oriented Programming': {
        'default_phase': 1,
        'why_it_matters': "Object-Oriented Programming (OOP) is required to build maintainable classes, Django models, and scalable architectures.",
        'learning_outcome': "Understand classes, objects, encapsulation, inheritance, polymorphism, and magic dunder methods.",
        'task_idea': "Design an object-oriented Bank Account management system with Account, Customer, and Transaction classes.",
        'steps': [
            "Learn class definitions, instance variables, and the __init__ constructor.",
            "Practice inheritance and super() calls across class hierarchies.",
            "Understand encapsulation using private attributes and @property getters/setters.",
            "Learn polymorphism and abstract base classes (abc module).",
            "Implement common design patterns (Singleton, Factory) in Python.",
        ],
    },
    'Data Structures & Algorithms': {
        'default_phase': 1,
        'why_it_matters': "DSA develops analytical problem-solving and ensures your code runs efficiently under heavy traffic.",
        'learning_outcome': "Master array manipulation, hash maps, binary search, trees, graphs, and Big-O runtime analysis.",
        'task_idea': "Solve 20 curated LeetCode/HackerRank problems covering two-pointers, hash tables, and depth-first search.",
        'steps': [
            "Understand Big-O time and space complexity notation.",
            "Master arrays, strings, and hash maps (dictionaries) for constant-time lookups.",
            "Learn two-pointer and sliding-window techniques.",
            "Practice recursion, binary search, and sorting algorithms.",
            "Study linked lists, stacks, queues, and tree traversal (BFS / DFS).",
        ],
    },
    'SQL': {
        'default_phase': 1,
        'why_it_matters': "SQL is the universal language for querying, updating, and indexing data across relational databases.",
        'learning_outcome': "Write performant SELECT, JOIN, GROUP BY, subquery, and transaction statements against real databases.",
        'task_idea': "Create an e-commerce schema in SQLite or PostgreSQL and write analytical queries for customer revenue.",
        'steps': [
            "Master basic SELECT, WHERE, ORDER BY, and LIMIT clauses.",
            "Learn INNER JOIN, LEFT JOIN, and table aliases to combine multi-table datasets.",
            "Practice aggregation with GROUP BY, HAVING, and aggregate functions (COUNT, SUM, AVG).",
            "Understand database normalization (1NF, 2NF, 3NF) and primary/foreign keys.",
            "Learn indexes, EXPLAIN ANALYZE, and how query performance is optimized.",
        ],
    },
    'Git': {
        'default_phase': 1,
        'why_it_matters': "Git is the industry-standard version control system essential for team collaboration and continuous deployment.",
        'learning_outcome': "Confidently branch, commit, merge, resolve conflicts, and collaborate using GitHub pull requests.",
        'task_idea': "Create a GitHub repository with protected main branch, feature branches, and submit clean pull requests.",
        'steps': [
            "Master git init, status, add, commit, and git log.",
            "Practice branch workflows: git checkout -b, branch, and merge.",
            "Learn how to handle and resolve merge conflicts cleanly.",
            "Understand git reset, stash, and git rebase for clean commit histories.",
            "Practice collaborative open-source workflows with GitHub forks, PRs, and reviews.",
        ],
    },
    'Django': {
        'default_phase': 2,
        'why_it_matters': "Django is Python's leading batteries-included web framework for creating secure, full-featured web applications.",
        'learning_outcome': "Build complete web applications with models, class-based views, URL routing, forms, and admin interface.",
        'task_idea': "Develop a multi-user Blog or Task Management app with user authentication, CRUD operations, and search.",
        'steps': [
            "Understand Django project structure, settings, apps, and the MTV architecture.",
            "Create database models, manage migrations, and utilize the Django ORM query API.",
            "Build dynamic views (function-based and Class-Based Views) and configure URL patterns.",
            "Design responsive HTML templates with template tags, filters, and template inheritance.",
            "Implement user registration, login, session authentication, and CSRF protection.",
            "Configure static files, media uploads, and the Django admin interface.",
        ],
    },
    'REST API': {
        'default_phase': 2,
        'why_it_matters': "REST APIs provide standard JSON endpoints enabling frontend apps, mobile devices, and microservices to communicate.",
        'learning_outcome': "Architect, document, and secure RESTful endpoints using Django REST Framework (DRF).",
        'task_idea': "Build a REST API for a bookstore with serializers, ViewSets, JWT authentication, and Swagger/OpenAPI docs.",
        'steps': [
            "Learn HTTP methods (GET, POST, PUT, PATCH, DELETE) and status codes (200, 201, 400, 401, 404, 500).",
            "Understand REST principles: statelessness, resource-oriented URLs, and JSON representations.",
            "Install and configure Django REST Framework (DRF).",
            "Create ModelSerializers to validate and serialize model data.",
            "Build API views using APIView, GenericAPIView, and ModelViewSet with DefaultRouter.",
            "Implement token or JWT authentication and custom permissions (IsAuthenticated, IsOwner).",
            "Test API endpoints with Postman, curl, or automated APITestCase tests.",
        ],
    },
    'Testing & Debugging': {
        'default_phase': 2,
        'why_it_matters': "Automated testing guarantees that new changes do not break existing features in production systems.",
        'learning_outcome': "Write unit and integration tests using Django TestCase, pytest-django, and isolate bugs systematically.",
        'task_idea': "Add 90%+ test coverage to your Django project models, views, and forms using automated tests.",
        'steps': [
            "Learn the unit testing lifecycle: Arrange, Act, Assert (AAA).",
            "Write model tests checking field constraints, validation, and custom methods.",
            "Write view tests checking response status codes, template rendering, and context data.",
            "Test forms and API endpoints with valid and invalid payloads.",
            "Use coverage.py to generate test coverage reports.",
            "Practice debugging with Python's pdb, breakpoints, and logging.",
        ],
    },
    'PostgreSQL': {
        'default_phase': 3,
        'why_it_matters': "PostgreSQL is the industry-standard production database known for stability, ACID compliance, and rich features.",
        'learning_outcome': "Deploy, configure, and optimize PostgreSQL databases for production Django applications.",
        'task_idea': "Migrate a local Django project from SQLite to PostgreSQL with Docker and measure query speeds.",
        'steps': [
            "Install PostgreSQL and understand databases, users, and permissions.",
            "Configure psycopg (psycopg2 or psycopg3) in Django settings.py.",
            "Understand PostgreSQL data types, JSONB fields, and full-text search.",
            "Learn connection pooling and database transaction isolation levels.",
            "Practice backup and restore operations using pg_dump and psql.",
        ],
    },
    'HTML & CSS': {
        'default_phase': 3,
        'why_it_matters': "HTML and CSS form the foundation of web interfaces, enabling accessible layouts and attractive styling.",
        'learning_outcome': "Build semantic, responsive web pages utilizing Flexbox, CSS Grid, and modern design principles.",
        'task_idea': "Create a responsive portfolio landing page with mobile hamburger navigation and CSS Grid project showcase.",
        'steps': [
            "Master semantic HTML5 elements: header, nav, main, section, article, footer.",
            "Understand the CSS Box Model (margin, border, padding, content).",
            "Build fluid layouts using CSS Flexbox and CSS Grid.",
            "Implement responsive breakpoints with CSS media queries.",
            "Apply modern CSS variables, transitions, and hover states.",
        ],
    },
    'JavaScript': {
        'default_phase': 3,
        'why_it_matters': "JavaScript adds dynamic behavior, asynchronous data fetching, and user interactivity to web applications.",
        'learning_outcome': "Manipulate the DOM, handle asynchronous API requests via fetch(), and write modern ES6+ JavaScript.",
        'task_idea': "Add dynamic live search and asynchronous comment submission to your Django application using Fetch API.",
        'steps': [
            "Review modern ES6 syntax: let/const, arrow functions, template literals, destructuring.",
            "Practice DOM selection, manipulation, and event listeners.",
            "Understand asynchronous JavaScript: Promises and async/await.",
            "Send GET and POST requests to backend REST endpoints using the Fetch API.",
            "Handle JSON responses and render UI components dynamically without full page reloads.",
        ],
    },
    'Docker': {
        'default_phase': 3,
        'why_it_matters': "Docker packages applications and dependencies into standardized containers for consistent deployment across environments.",
        'learning_outcome': "Write Dockerfiles and docker-compose configurations to orchestrate multi-container Django applications.",
        'task_idea': "Dockerize a Django application with PostgreSQL, Redis, and Gunicorn using docker-compose.",
        'steps': [
            "Understand containerization vs virtualization concepts.",
            "Write a multi-stage Dockerfile for a production Python/Django application.",
            "Configure docker-compose.yml for web app, PostgreSQL, and cache containers.",
            "Manage persistent volumes for media files and database storage.",
            "Learn essential Docker CLI commands: build, run, exec, logs, ps, down.",
        ],
    },
    'NumPy': {
        'default_phase': 3,
        'why_it_matters': "NumPy enables fast, vectorized mathematical and multi-dimensional array operations in Python.",
        'learning_outcome': "Create, slice, reshape, and perform mathematical operations on multi-dimensional NumPy arrays.",
        'task_idea': "Implement matrix operations and statistical calculations on real numerical data using NumPy.",
        'steps': [
            "Understand ndarray structures vs standard Python lists.",
            "Practice array indexing, slicing, broadcasting, and reshaping.",
            "Learn mathematical, trigonometric, and statistical array methods.",
            "Understand vectorization for accelerating computational loops.",
        ],
    },
    'Pandas': {
        'default_phase': 3,
        'why_it_matters': "Pandas is the premier library for importing, cleaning, analyzing, and transforming structured datasets.",
        'learning_outcome': "Manipulate DataFrames, clean missing data, execute GroupBy summaries, and merge disparate tables.",
        'task_idea': "Analyze a real-world CSV dataset, handle null values, calculate summary metrics, and export findings.",
        'steps': [
            "Master Pandas Series and DataFrame creation and indexing (.loc, .iloc).",
            "Learn data cleaning: handling missing values (dropna, fillna) and data type conversions.",
            "Practice filtering, sorting, and conditional selections.",
            "Perform aggregations using groupby(), pivot_table(), and apply().",
            "Merge and concatenate multiple DataFrames using merge() and concat().",
        ],
    },
    'Excel': {
        'default_phase': 2,
        'why_it_matters': "Excel remains the universal business tool for data auditing, ad-hoc modeling, and stakeholder communication.",
        'learning_outcome': "Build advanced formulas, dynamic pivot tables, and financial/operational summary models.",
        'task_idea': "Build an automated sales analysis model with XLOOKUP, dynamic charts, and conditional formatting.",
        'steps': [
            "Master essential formulas: XLOOKUP, INDEX/MATCH, SUMIFS, COUNTIFS, IF/AND.",
            "Build interactive Pivot Tables with calculated fields and slicers.",
            "Practice data validation, duplicate removal, and conditional formatting rules.",
            "Create executive charts that clearly present business metrics.",
        ],
    },
    'Power BI': {
        'default_phase': 3,
        'why_it_matters': "Power BI enables organizations to transform raw data into interactive, real-time visual dashboards.",
        'learning_outcome': "Design star-schema data models, write DAX measures, and publish interactive executive reports.",
        'task_idea': "Build an interactive 3-page Business Intelligence dashboard connecting SQL and Excel data sources.",
        'steps': [
            "Import and transform data using Power Query.",
            "Design star-schema relational data models with active relationships.",
            "Write DAX measures for YoY growth, running totals, and key ratios.",
            "Design clean, accessible visual layouts with cross-filtering and drill-throughs.",
        ],
    },
    'Statistics': {
        'default_phase': 2,
        'why_it_matters': "Statistical reasoning ensures business decisions and data conclusions are backed by rigorous probability.",
        'learning_outcome': "Apply descriptive statistics, normal distributions, confidence intervals, and hypothesis testing.",
        'task_idea': "Perform an A/B test analysis calculating p-values and confidence intervals to evaluate conversion lift.",
        'steps': [
            "Understand mean, median, mode, standard deviation, and interquartile range.",
            "Learn probability distributions (Normal, Binomial, Poisson).",
            "Master hypothesis testing: null hypothesis, p-values, t-tests, and chi-squared tests.",
            "Understand correlation vs causation and linear regression fundamentals.",
        ],
    },
}

DEFAULT_METADATA: Dict[str, Any] = {
    'default_phase': 2,
    'why_it_matters': "A key competency required for your target job role.",
    'learning_outcome': "Attain practical, verifiable proficiency in this competency.",
    'task_idea': "Build a focused mini-project demonstrating practical application of this skill.",
    'steps': [
        "Research foundational concepts and official documentation.",
        "Complete structured exercises and tutorials.",
        "Implement practical features in an application.",
        "Write tests and document your implementation in a GitHub repository.",
    ],
}


def get_skill_metadata(skill_name: str) -> Dict[str, Any]:
    """Retrieves full pedagogical metadata for any skill name (with alias resolution)."""
    canonical = canonicalize_skill_name(skill_name)
    if canonical in SKILL_METADATA:
        return SKILL_METADATA[canonical]
    for key, data in SKILL_METADATA.items():
        if key.lower() == skill_name.strip().lower():
            return data
    return DEFAULT_METADATA


def get_steps_for_skill(skill_name: str) -> List[str]:
    """Backward-compatible helper returning ordered learning steps."""
    meta = get_skill_metadata(skill_name)
    return meta.get('steps', DEFAULT_METADATA['steps'])