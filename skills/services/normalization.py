"""
skills/services/normalization.py
Centralized Skill Normalization, Aliasing, and Matching System for DUALYN.

Features:
- Centralized canonical skill registry with alias mappings covering technical skills,
  tools, databases, frameworks, libraries, cloud platforms, and project competencies.
- Clean text normalization (case, punctuation, whitespace, separators).
- Regex word-boundary matching with strict disambiguation to prevent false matches
  (e.g. 'c' in 'basic', 'git' in 'digital', 'java' in 'javascript', 'go' in common text).
- Compound competency support (e.g. 'HTML & CSS' maps bidirectionally to 'HTML' and 'CSS').
- Section-aware evidence extraction from resumes, coursework, and project descriptions.
- Synchronizer to populate canonical catalog skills into the database.
"""
import re
from typing import Dict, List, Optional, Tuple, Set, Any


# ---------------------------------------------------------------------------
# CANONICAL SKILL REGISTRY
# ---------------------------------------------------------------------------
SKILL_CATALOG: Dict[str, Dict[str, Any]] = {
    # --- Programming Languages ---
    'Python': {
        'canonical': 'Python',
        'category': 'Programming',
        'aliases': [
            'python', 'python3', 'python 3', 'python programming', 'python developer',
            'python scripting', 'py', 'cpython'
        ],
        'pattern': r'\bpython(?:3|\s+programming|\s+scripting|\s+developer)?\b',
    },
    'Java': {
        'canonical': 'Java',
        'category': 'Programming',
        'aliases': [
            'java', 'core java', 'java 8', 'java 11', 'java 17', 'java 21',
            'j2ee', 'java programming', 'jakarta ee'
        ],
        'pattern': r'\bjava(?:\s*(?:8|11|17|21))?\b(?![\w-]*script)|\bcore\s+java\b|\bj2ee\b|\bjakarta\s+ee\b',
    },
    'JavaScript': {
        'canonical': 'JavaScript',
        'category': 'Frontend Development',
        'aliases': ['javascript', 'js', 'es6', 'ecmascript', 'vanilla js', 'modern javascript'],
        'pattern': r'\b(?:javascript|js|es6|ecmascript|vanilla\s+js|modern\s+javascript)\b',
    },
    'TypeScript': {
        'canonical': 'TypeScript',
        'category': 'Frontend Development',
        'aliases': ['typescript', 'ts'],
        'pattern': r'\b(?:typescript|ts)\b',
    },
    'C': {
        'canonical': 'C',
        'category': 'Programming',
        'aliases': ['c', 'c programming', 'c language', 'ansi c'],
        'pattern': r'\b(?:c\s+programming|c\s+language|ansi\s+c)\b|(?:languages?|programming|skills?|coursework)[:\s][^\n.]*?\bC\b(?!\+\+|#)',
    },
    'C++': {
        'canonical': 'C++',
        'category': 'Programming',
        'aliases': ['c++', 'cpp', 'c plus plus', 'c/c++'],
        'pattern': r'\b(?:c\+\+|cpp|c\s*plus\s*plus)\b|c\s*\/\s*c\+\+',
    },
    'C#': {
        'canonical': 'C#',
        'category': 'Programming',
        'aliases': ['c#', 'csharp', 'c sharp'],
        'pattern': r'\b(?:c#|csharp|c\s*sharp|\.net\s+c#)\b',
    },
    'PHP': {
        'canonical': 'PHP',
        'category': 'Programming',
        'aliases': ['php', 'php7', 'php8'],
        'pattern': r'\bphp(?:[578])?\b',
    },
    'Ruby': {
        'canonical': 'Ruby',
        'category': 'Programming',
        'aliases': ['ruby', 'ruby on rails'],
        'pattern': r'\bruby(?:\s+on\s+rails)?\b',
    },
    'Go': {
        'canonical': 'Go',
        'category': 'Programming',
        'aliases': ['go', 'golang', 'go language', 'go programming'],
        'pattern': r'\b(?:golang|go\s+language|go\s+programming)\b',
    },
    'Rust': {
        'canonical': 'Rust',
        'category': 'Programming',
        'aliases': ['rust', 'rustlang', 'rust programming'],
        'pattern': r'\brust(?:\s+programming|\s+language|lang)?\b',
    },
    'Kotlin': {
        'canonical': 'Kotlin',
        'category': 'Programming',
        'aliases': ['kotlin'],
        'pattern': r'\bkotlin\b',
    },
    'Swift': {
        'canonical': 'Swift',
        'category': 'Programming',
        'aliases': ['swift'],
        'pattern': r'\bswift(?:\s+programming|\s+language|\s+ios)?\b|(?:languages?|programming|skills?)[:\s][^\n.]*?\bSwift\b',
    },
    'Dart': {
        'canonical': 'Dart',
        'category': 'Programming',
        'aliases': ['dart'],
        'pattern': r'\bdart(?:\s+programming|\s+language|\s+flutter)?\b|(?:languages?|programming|skills?)[:\s][^\n.]*?\bDart\b',
    },
    'R': {
        'canonical': 'R',
        'category': 'Data Analysis',
        'aliases': ['r', 'r programming', 'r language'],
        'pattern': r'\b(?:r\s+programming|r\s+language)\b|(?:languages?|programming|skills?)[:\s][^\n.]*?\bR\b',
    },
    'Bash / Shell': {
        'canonical': 'Bash / Shell',
        'category': 'Tools & Version Control',
        'aliases': ['bash', 'shell', 'shell scripting', 'shell script', 'zsh', 'powershell', 'command line', 'bash scripting'],
        'pattern': r'\b(?:bash|shell\s+script(?:ing)?|zsh|powershell|command\s+line|linux\s+shell)\b',
    },

    # --- Web & Backend Frameworks ---
    'Django': {
        'canonical': 'Django',
        'category': 'Backend Frameworks',
        'aliases': ['django', 'django framework', 'django mvc', 'django mtv', 'django orm'],
        'pattern': r'\bdjango(?:\s+framework|\s+mvc|\s+mtv|\s+orm)?\b',
    },
    'Django REST Framework': {
        'canonical': 'Django REST Framework',
        'category': 'Backend Frameworks',
        'aliases': ['django rest framework', 'drf'],
        'pattern': r'\b(?:django\s+rest\s+framework|drf)\b',
    },
    'FastAPI': {
        'canonical': 'FastAPI',
        'category': 'Backend Frameworks',
        'aliases': ['fastapi', 'fast api'],
        'pattern': r'\bfast\s*api\b',
    },
    'Flask': {
        'canonical': 'Flask',
        'category': 'Backend Frameworks',
        'aliases': ['flask', 'flask framework'],
        'pattern': r'\bflask(?:\s+framework)?\b',
    },
    'Spring Boot': {
        'canonical': 'Spring Boot',
        'category': 'Backend Frameworks',
        'aliases': ['spring boot', 'spring', 'spring framework', 'spring mvc'],
        'pattern': r'\bspring(?:\s+boot|\s+framework|\s+mvc)?\b',
    },
    'Node.js': {
        'canonical': 'Node.js',
        'category': 'Backend Development',
        'aliases': ['node.js', 'nodejs', 'node', 'node js'],
        'pattern': r'\bnode(?:\.js|js)\b|\bnode\s+js\b',
    },
    'Express.js': {
        'canonical': 'Express.js',
        'category': 'Backend Development',
        'aliases': ['express.js', 'expressjs', 'express', 'express js'],
        'pattern': r'\bexpress(?:\.js|js)\b|\bexpress\s+js\b|\bexpress\s+framework\b',
    },
    'React': {
        'canonical': 'React',
        'category': 'Frontend Development',
        'aliases': ['react', 'react.js', 'reactjs', 'react js'],
        'pattern': r'\breact(?:\.js|js)?\b(?![\w-]*native)',
    },
    'Angular': {
        'canonical': 'Angular',
        'category': 'Frontend Development',
        'aliases': ['angular', 'angularjs', 'angular.js', 'angular js'],
        'pattern': r'\bangular(?:\.js|js)?\b',
    },
    'Vue.js': {
        'canonical': 'Vue.js',
        'category': 'Frontend Development',
        'aliases': ['vue.js', 'vuejs', 'vue', 'vue js'],
        'pattern': r'\bvue(?:\.js|js)?\b',
    },
    'Next.js': {
        'canonical': 'Next.js',
        'category': 'Frontend Development',
        'aliases': ['next.js', 'nextjs', 'next js', 'next'],
        'pattern': r'\bnext(?:\.js|js)\b|\bnext\s+js\b',
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
        'pattern': r'\bcss3?\b|\bresponsive\s+design(?:\s+basics)?\b|\bcascading\s+style\s+sheets\b|\bflexbox\b|\bcss\s+grid\b',
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
    'Bootstrap': {
        'canonical': 'Bootstrap',
        'category': 'Frontend Development',
        'aliases': ['bootstrap', 'bootstrap css', 'bootstrap 5', 'bootstrap 4'],
        'pattern': r'\bbootstrap[45]?\b',
    },
    'Tailwind CSS': {
        'canonical': 'Tailwind CSS',
        'category': 'Frontend Development',
        'aliases': ['tailwind css', 'tailwind', 'tailwindcss'],
        'pattern': r'\btailwind(?:\s*css)?\b',
    },
    'Bulma CSS': {
        'canonical': 'Bulma CSS',
        'category': 'Frontend Development',
        'aliases': ['bulma css', 'bulma'],
        'pattern': r'\bbulma(?:\s+css)?\b',
    },
    'jQuery': {
        'canonical': 'jQuery',
        'category': 'Frontend Development',
        'aliases': ['jquery'],
        'pattern': r'\bjquery\b',
    },
    'Celery': {
        'canonical': 'Celery',
        'category': 'Backend Development',
        'aliases': ['celery'],
        'pattern': r'\bcelery\b',
    },

    # --- Databases ---
    'SQL': {
        'canonical': 'SQL',
        'category': 'Databases',
        'aliases': [
            'sql', 'mysql', 'sqlite', 'sqlite3', 'mariadb', 'postgresql',
            'postgres', 'pgsql', 'psql', 'relational database', 'rdbms',
            'sql queries', 'mysql / sqlite', 'mysql/sqlite'
        ],
        'pattern': r'\b(?:sql|mysql|sqlite3?|mariadb|postgresql|postgres|pgsql|psql|rdbms|relational\s+databases?)\b',
    },
    'MySQL': {
        'canonical': 'MySQL',
        'category': 'Databases',
        'aliases': ['mysql'],
        'pattern': r'\bmysql\b',
    },
    'PostgreSQL': {
        'canonical': 'PostgreSQL',
        'category': 'Databases',
        'aliases': ['postgresql', 'postgres', 'pgsql', 'psql'],
        'pattern': r'\b(?:postgresql|postgres|pgsql|psql)\b',
    },
    'SQLite': {
        'canonical': 'SQLite',
        'category': 'Databases',
        'aliases': ['sqlite', 'sqlite3'],
        'pattern': r'\bsqlite3?\b',
    },
    'MariaDB': {
        'canonical': 'MariaDB',
        'category': 'Databases',
        'aliases': ['mariadb'],
        'pattern': r'\bmariadb\b',
    },
    'MongoDB': {
        'canonical': 'MongoDB',
        'category': 'Databases',
        'aliases': ['mongodb', 'mongo'],
        'pattern': r'\bmongo(?:db)?\b',
    },
    'Redis': {
        'canonical': 'Redis',
        'category': 'Databases',
        'aliases': ['redis'],
        'pattern': r'\bredis\b',
    },
    'Oracle': {
        'canonical': 'Oracle',
        'category': 'Databases',
        'aliases': ['oracle', 'oracle db', 'oracle database'],
        'pattern': r'\boracle(?:\s+database|\s+db)?\b',
    },
    'Microsoft SQL Server': {
        'canonical': 'Microsoft SQL Server',
        'category': 'Databases',
        'aliases': ['sql server', 'mssql', 'ms sql server', 'microsoft sql server'],
        'pattern': r'\b(?:sql\s+server|mssql|ms\s+sql\s+server)\b',
    },
    'Firebase': {
        'canonical': 'Firebase',
        'category': 'Databases',
        'aliases': ['firebase', 'firestore'],
        'pattern': r'\b(?:firebase|firestore)\b',
    },
    'Cassandra': {
        'canonical': 'Cassandra',
        'category': 'Databases',
        'aliases': ['cassandra'],
        'pattern': r'\bcassandra\b',
    },
    'ChromaDB': {
        'canonical': 'ChromaDB',
        'category': 'Databases',
        'aliases': ['chromadb', 'chroma db', 'chroma'],
        'pattern': r'\bchroma(?:\s*db)?\b',
    },
    'Qdrant': {
        'canonical': 'Qdrant',
        'category': 'Databases',
        'aliases': ['qdrant'],
        'pattern': r'\bqdrant\b',
    },
    'Vector Databases': {
        'canonical': 'Vector Databases',
        'category': 'Databases',
        'aliases': ['vector database', 'vector databases', 'vector db', 'vector search'],
        'pattern': r'\bvector\s+(?:databases?|db|search|embeddings?)\b',
    },

    # --- Tools, Platforms & DevOps ---
    'Git': {
        'canonical': 'Git',
        'category': 'Tools & Version Control',
        'aliases': [
            'git', 'git version control', 'github', 'gitlab', 'version control',
            'git cli', 'git/github', 'git & github'
        ],
        'pattern': r'\b(?:git(?:\s+cli|\s+version\s+control)?|github|gitlab|version\s+control)\b',
    },
    'GitHub': {
        'canonical': 'GitHub',
        'category': 'Tools & Version Control',
        'aliases': ['github'],
        'pattern': r'\bgithub\b',
    },
    'GitLab': {
        'canonical': 'GitLab',
        'category': 'Tools & Version Control',
        'aliases': ['gitlab'],
        'pattern': r'\bgitlab\b',
    },
    'Docker': {
        'canonical': 'Docker',
        'category': 'DevOps & Deployment',
        'aliases': ['docker', 'containerization', 'dockerfile', 'docker-compose', 'containers'],
        'pattern': r'\b(?:docker(?:file|-compose)?|containerization|containers)\b',
    },
    'Kubernetes': {
        'canonical': 'Kubernetes',
        'category': 'DevOps & Deployment',
        'aliases': ['kubernetes', 'k8s'],
        'pattern': r'\b(?:kubernetes|k8s)\b',
    },
    'AWS': {
        'canonical': 'AWS',
        'category': 'DevOps & Deployment',
        'aliases': ['aws', 'amazon web services', 'aws ec2', 'ec2', 's3', 'aws lambda', 'aws linux'],
        'pattern': r'\b(?:aws(?:\s+ec2|\s+linux)?|amazon\s+web\s+services|ec2|aws\s+s3|aws\s+lambda)\b',
    },
    'Microsoft Azure': {
        'canonical': 'Microsoft Azure',
        'category': 'DevOps & Deployment',
        'aliases': ['azure', 'microsoft azure'],
        'pattern': r'\b(?:microsoft\s+)?azure\b',
    },
    'Google Cloud Platform': {
        'canonical': 'Google Cloud Platform',
        'category': 'DevOps & Deployment',
        'aliases': ['google cloud', 'gcp', 'google cloud platform'],
        'pattern': r'\b(?:google\s+cloud(?:\s+platform)?|gcp)\b',
    },
    'Linux': {
        'canonical': 'Linux',
        'category': 'DevOps & Deployment',
        'aliases': ['linux', 'ubuntu', 'debian', 'centos', 'redhat'],
        'pattern': r'\b(?:linux|ubuntu|debian|centos|redhat)\b',
    },
    'Gunicorn': {
        'canonical': 'Gunicorn',
        'category': 'DevOps & Deployment',
        'aliases': ['gunicorn'],
        'pattern': r'\bgunicorn\b',
    },
    'Nginx': {
        'canonical': 'Nginx',
        'category': 'DevOps & Deployment',
        'aliases': ['nginx'],
        'pattern': r'\bnginx\b',
    },
    'Apache': {
        'canonical': 'Apache',
        'category': 'DevOps & Deployment',
        'aliases': ['apache', 'apache web server', 'httpd'],
        'pattern': r'\bapache(?:\s+web\s+server|\s+httpd)?\b',
    },
    'Postman': {
        'canonical': 'Postman',
        'category': 'Tools & Version Control',
        'aliases': ['postman'],
        'pattern': r'\bpostman\b',
    },
    'VS Code': {
        'canonical': 'VS Code',
        'category': 'Tools & Version Control',
        'aliases': ['vs code', 'vscode', 'visual studio code'],
        'pattern': r'\b(?:vs\s*code|vscode|visual\s+studio\s+code)\b',
    },
    'Jira': {
        'canonical': 'Jira',
        'category': 'Tools & Version Control',
        'aliases': ['jira'],
        'pattern': r'\bjira\b',
    },
    'Jenkins': {
        'canonical': 'Jenkins',
        'category': 'DevOps & Deployment',
        'aliases': ['jenkins'],
        'pattern': r'\bjenkins\b',
    },
    'CI/CD': {
        'canonical': 'CI/CD',
        'category': 'DevOps & Deployment',
        'aliases': ['ci/cd', 'ci-cd', 'continuous integration', 'continuous deployment', 'github actions'],
        'pattern': r'\b(?:ci\s*\/\s*cd|ci-cd|continuous\s+integration|github\s+actions)\b',
    },

    # --- Backend & Architecture Concepts ---
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
    'Debugging': {
        'canonical': 'Debugging',
        'category': 'Testing & Quality',
        'aliases': ['debugging', 'bug fixing', 'troubleshooting', 'code debugging'],
        'pattern': r'\b(?:debugging|bug\s+fixing|troubleshooting|code\s+debugging)\b',
    },
    'Testing': {
        'canonical': 'Testing',
        'category': 'Testing & Quality',
        'aliases': [
            'testing', 'unit testing', 'automated testing', 'pytest', 'unittest',
            'test cases', 'tdd', 'test-driven development', 'integration testing'
        ],
        'pattern': r'\b(?:unit\s+testing|automated\s+testing|integration\s+testing|pytest|unittest|test\s+cases|tdd|test[\s-]driven\s+development)\b|\btesting\b',
    },
    'Testing & Debugging': {
        'canonical': 'Testing & Debugging',
        'category': 'Testing & Quality',
        'is_compound': True,
        'components': ['Testing', 'Debugging'],
        'aliases': ['testing & debugging', 'testing and debugging', 'testing/debugging'],
        'pattern': r'\btesting\s*(?:&|and|\/)\s*debugging\b|\bdebugging\s*(?:&|and|\/)\s*testing\b',
    },
    'CRUD Operations': {
        'canonical': 'CRUD Operations',
        'category': 'Core Concepts',
        'aliases': [
            'crud', 'crud operations', 'crud functionality', 'crud api',
            'crud operations (create, read, update, delete)'
        ],
        'pattern': r'\bcrud(?:\s+operations?|\s+functionality|\s+apis?)?\b',
    },
    'Software Engineering': {
        'canonical': 'Software Engineering',
        'category': 'Core Concepts',
        'aliases': [
            'software engineering', 'software engineering principles', 'software engineering practices'
        ],
        'pattern': r'\bsoftware\s+engineering(?:\s+principles|\s+practices)?\b',
    },
    'Object-Oriented Programming': {
        'canonical': 'Object-Oriented Programming',
        'category': 'Core Concepts',
        'aliases': [
            'object-oriented programming', 'object oriented programming',
            'oop', 'oops', 'oop basics', 'oops basics', 'object-oriented design',
            'ood', 'object-oriented concepts'
        ],
        'pattern': r'\b(?:object[\s-]oriented\s+programming|object[\s-]oriented\s+design|oop[s]?(?:\s+basics)?|ood|object[\s-]oriented\s+concepts?)\b',
    },
    'Data Structures & Algorithms': {
        'canonical': 'Data Structures & Algorithms',
        'category': 'Core Concepts',
        'aliases': [
            'data structures & algorithms', 'data structures and algorithms',
            'dsa', 'data structures', 'algorithms', 'ds & algo', 'ds and algo'
        ],
        'pattern': r'\b(?:data\s+structures\s*(?:&|and)\s*algorithms|dsa|data\s+structures|algorithms|ds\s*(?:&|and)\s*algo)\b',
    },
    'Database Management Systems (DBMS)': {
        'canonical': 'Database Management Systems (DBMS)',
        'category': 'Core Concepts',
        'aliases': ['dbms', 'database management systems', 'database management'],
        'pattern': r'\b(?:dbms|database\s+management\s+systems?|database\s+management)\b',
    },
    'Web Development': {
        'canonical': 'Web Development',
        'category': 'Core Concepts',
        'aliases': ['web development', 'web technologies'],
        'pattern': r'\bweb\s+(?:development|technologies)\b',
    },
    'Microservices': {
        'canonical': 'Microservices',
        'category': 'Core Concepts',
        'aliases': ['microservices', 'microservice architecture'],
        'pattern': r'\bmicroservices?(?:\s+architecture)?\b',
    },
    'Cloud Computing': {
        'canonical': 'Cloud Computing',
        'category': 'Core Concepts',
        'aliases': ['cloud computing', 'cloud deployment'],
        'pattern': r'\bcloud\s+(?:computing|deployment)\b',
    },
    'Agile / Scrum': {
        'canonical': 'Agile / Scrum',
        'category': 'Core Concepts',
        'aliases': ['agile', 'scrum', 'agile / scrum', 'agile project management'],
        'pattern': r'\b(?:agile(?:\s+methodology|\s+project\s+management)?|scrum)\b',
    },

    # --- AI, Data Science & Machine Learning ---
    'Artificial Intelligence': {
        'canonical': 'Artificial Intelligence',
        'category': 'Core Concepts',
        'aliases': ['artificial intelligence', 'ai', 'ai application development', 'ai chatbot development'],
        'pattern': r'\b(?:artificial\s+intelligence|ai\s+powered|ai\s+applications?|ai\s+apis?|ai\s+solutions?|ai\s+systems?|ai\s+agents?|ai\s+chatbot(?:\s+development)?)\b|(?:coursework|interests?)[:\s][^\n.]*?\bAI\b',
    },
    'Machine Learning': {
        'canonical': 'Machine Learning',
        'category': 'Data Analysis',
        'aliases': ['machine learning', 'ml'],
        'pattern': r'\b(?:machine\s+learning|ml\s+models?)\b|(?:coursework|interests?)[:\s][^\n.]*?\bML\b',
    },
    'Deep Learning': {
        'canonical': 'Deep Learning',
        'category': 'Data Analysis',
        'aliases': ['deep learning'],
        'pattern': r'\bdeep\s+learning\b',
    },
    'Generative AI': {
        'canonical': 'Generative AI',
        'category': 'Core Concepts',
        'aliases': ['generative ai', 'gen ai', 'genai'],
        'pattern': r'\b(?:generative\s+ai|gen\s*ai|genai)\b',
    },
    'Large Language Models (LLMs)': {
        'canonical': 'Large Language Models (LLMs)',
        'category': 'Core Concepts',
        'aliases': ['large language models', 'llm', 'llms', 'large language models (llms)'],
        'pattern': r'\b(?:large\s+language\s+models?|llms?)\b',
    },
    'Retrieval-Augmented Generation (RAG)': {
        'canonical': 'Retrieval-Augmented Generation (RAG)',
        'category': 'Core Concepts',
        'aliases': ['retrieval-augmented generation', 'retrieval augmented generation', 'rag', 'retrieval-augmented generation (rag)'],
        'pattern': r'\b(?:retrieval[\s-]augmented\s+generation|rag)\b',
    },
    'Prompt Engineering': {
        'canonical': 'Prompt Engineering',
        'category': 'Core Concepts',
        'aliases': ['prompt engineering'],
        'pattern': r'\bprompt\s+engineering\b',
    },
    'TensorFlow': {
        'canonical': 'TensorFlow',
        'category': 'Data Analysis',
        'aliases': ['tensorflow'],
        'pattern': r'\btensorflow\b',
    },
    'PyTorch': {
        'canonical': 'PyTorch',
        'category': 'Data Analysis',
        'aliases': ['pytorch'],
        'pattern': r'\bpytorch\b',
    },
    'Scikit-learn': {
        'canonical': 'Scikit-learn',
        'category': 'Data Analysis',
        'aliases': ['scikit-learn', 'sklearn'],
        'pattern': r'\b(?:scikit[\s-]learn|sklearn)\b',
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

# Precompile regex patterns for high-throughput scanning
_COMPILED_PATTERNS: Dict[str, re.Pattern] = {
    canonical: re.compile(data['pattern'], re.IGNORECASE)
    for canonical, data in SKILL_CATALOG.items()
    if 'pattern' in data
}

# Synonyms for canonical names used in different catalog entries
CANONICAL_SYNONYMS: Dict[str, str] = {
    'rest api development': 'REST API',
    'restful api': 'REST API',
    'restful apis': 'REST API',
    'django rest framework': 'REST API',
    'drf': 'REST API',
    'oop': 'Object-Oriented Programming',
    'oops': 'Object-Oriented Programming',
    'dsa': 'Data Structures & Algorithms',
    'data structures and algorithms': 'Data Structures & Algorithms',
    'html5': 'HTML',
    'css3': 'CSS',
    'html and css': 'HTML & CSS',
    'html/css': 'HTML & CSS',
    'postgres': 'PostgreSQL',
    'postgresql': 'PostgreSQL',
    'testing and debugging': 'Testing & Debugging',
    'testing & debugging': 'Testing & Debugging',
    'debugging': 'Debugging',
    'bug fixing': 'Debugging',
    'troubleshooting': 'Debugging',
    'code debugging': 'Debugging',
    'testing': 'Testing',
    'unit testing': 'Testing',
    'automated testing': 'Testing',
    'pytest': 'Testing',
    'unittest': 'Testing',
    'crud': 'CRUD Operations',
    'crud operations': 'CRUD Operations',
    'software engineering': 'Software Engineering',
    'fastapi': 'FastAPI',
    'fast api': 'FastAPI',
    'mariadb': 'MariaDB',
    'mysql': 'MySQL',
    'sqlite': 'SQLite',
    'sqlite3': 'SQLite',
    'mongodb': 'MongoDB',
    'mongo': 'MongoDB',
    'redis': 'Redis',
    'aws': 'AWS',
    'amazon web services': 'AWS',
    'gcp': 'Google Cloud Platform',
    'google cloud': 'Google Cloud Platform',
    'azure': 'Microsoft Azure',
    'github': 'GitHub',
    'gitlab': 'GitLab',
    'vs code': 'VS Code',
    'vscode': 'VS Code',
    'visual studio code': 'VS Code',
    'postman': 'Postman',
    'bootstrap': 'Bootstrap',
    'tailwind': 'Tailwind CSS',
    'tailwindcss': 'Tailwind CSS',
    'bulma': 'Bulma CSS',
    'bulma css': 'Bulma CSS',
    'llm': 'Large Language Models (LLMs)',
    'llms': 'Large Language Models (LLMs)',
    'large language models': 'Large Language Models (LLMs)',
    'rag': 'Retrieval-Augmented Generation (RAG)',
    'retrieval augmented generation': 'Retrieval-Augmented Generation (RAG)',
    'retrieval-augmented generation': 'Retrieval-Augmented Generation (RAG)',
    'prompt engineering': 'Prompt Engineering',
    'genai': 'Generative AI',
    'gen ai': 'Generative AI',
    'generative ai': 'Generative AI',
    'dbms': 'Database Management Systems (DBMS)',
    'database management systems': 'Database Management Systems (DBMS)',
    'web development': 'Web Development',
    'machine learning': 'Machine Learning',
    'ml': 'Machine Learning',
    'artificial intelligence': 'Artificial Intelligence',
    'ai': 'Artificial Intelligence',
    'gunicorn': 'Gunicorn',
    'nginx': 'Nginx',
    'linux': 'Linux',
    'docker': 'Docker',
    'kubernetes': 'Kubernetes',
    'k8s': 'Kubernetes',
    'agile': 'Agile / Scrum',
    'scrum': 'Agile / Scrum',
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
    for canonical, compiled_pattern in _COMPILED_PATTERNS.items():
        if compiled_pattern.search(cleaned):
            return canonical

    # Fallback to normalized title-case
    return raw_name.strip()


def _extract_matched_sentence(start_pos: int, end_pos: int, full_text: str) -> str:
    """
    Extracts the clean, human-readable sentence or line enclosing the match
    for verifiable traceability.
    """
    # Find start of line / sentence
    line_start = full_text.rfind('\n', 0, start_pos)
    line_start = 0 if line_start == -1 else line_start + 1

    line_end = full_text.find('\n', end_pos)
    line_end = len(full_text) if line_end == -1 else line_end

    raw_line = full_text[line_start:line_end].strip()

    # Clean bullet markers or extra symbols at start
    cleaned_line = re.sub(r'^[•\-\*–—\u25cf\u25cb\u25a0\u25aa\t\s]+', '', raw_line).strip()

    # If the line is excessively long (multi-sentence paragraph), isolate the sentence
    if len(cleaned_line) > 160:
        rel_pos = start_pos - line_start
        s_start = 0
        for m in re.finditer(r'[\.\;\!\?]\s+', raw_line[:rel_pos]):
            s_start = m.end()
        s_end = len(raw_line)
        m_after = re.search(r'[\.\;\!\?](?:\s+|$)', raw_line[rel_pos:])
        if m_after:
            s_end = rel_pos + m_after.end()
        sentence_candidate = raw_line[s_start:s_end].strip()
        if sentence_candidate:
            cleaned_line = re.sub(r'^[•\-\*–—\u25cf\u25cb\u25a0\u25aa\t\s]+', '', sentence_candidate).strip()

    if not cleaned_line:
        w_start = max(0, start_pos - 40)
        w_end = min(len(full_text), end_pos + 40)
        cleaned_line = full_text[w_start:w_end].replace('\n', ' ').strip()

    return cleaned_line


def _get_active_section(match_pos: int, sections: List[Tuple[str, int, int]]) -> str:
    for sec_name, start, end in sections:
        if start <= match_pos < end:
            return sec_name
    return 'General'


def extract_skills_with_evidence(
    text: str,
    target_catalog_skills: Optional[List[str]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Scans free text (resume, project description, coursework, bio) and returns all detected
    canonical skills alongside exact sentence traceability, section name, and evidence strength.

    Returns dict mapping canonical skill name -> {
        'canonical': str,
        'category': str,
        'matched_alias': str,
        'section': str,
        'sentence': str,
        'excerpt': str,
        'strength': 'strong' | 'moderate' | 'basic',
        'is_project_evidence': bool,
        'occurrences': int,
        'is_inferred': bool,
        'evidence_type': 'explicit' | 'inferred',
    }
    """
    if not text or not text.strip():
        return {}

    norm_text = text  # preserve case for excerpt & sentence extraction
    results: Dict[str, Dict[str, Any]] = {}

    # Identify resume sections with clear human-readable titles
    sections = _split_into_sections(norm_text)

    # Section priority for selecting the most representative evidence
    SECTION_PRIORITY = {
        'Projects': 5,
        'Technical Skills': 4,
        'Education': 3,
        'Certifications': 3,
        'Work Experience': 3,
        'Summary': 2,
        'General': 1,
    }

    # Check each catalog item
    for canonical, pattern in _COMPILED_PATTERNS.items():
        data = SKILL_CATALOG[canonical]
        matches = list(pattern.finditer(norm_text))

        if matches:
            is_proj = False
            best_strength = 'basic'
            best_excerpt = None
            best_sentence = None
            best_section = 'General'
            best_alias = matches[0].group(0)
            best_priority = 0

            for m in matches:
                m_alias = m.group(0)
                m_section = _get_active_section(m.start(), sections)
                m_sentence = _extract_matched_sentence(m.start(), m.end(), norm_text)

                start = max(0, m.start() - 60)
                end = min(len(norm_text), m.end() + 60)
                raw_excerpt = norm_text[start:end].replace('\n', ' ').strip()
                curr_excerpt = f"...{raw_excerpt}..."

                m_proj, m_strength = _determine_evidence_context(m.start(), norm_text, sections, m_alias)
                if m_proj:
                    is_proj = True

                curr_priority = SECTION_PRIORITY.get(m_section, 1)
                strength_ranks = {'basic': 1, 'moderate': 2, 'strong': 3}

                # Choose best occurrence based on section priority and strength
                if (curr_priority > best_priority) or (
                    curr_priority == best_priority and strength_ranks.get(m_strength, 1) >= strength_ranks.get(best_strength, 1)
                ):
                    best_priority = curr_priority
                    best_section = m_section
                    best_sentence = m_sentence
                    best_strength = m_strength
                    best_excerpt = curr_excerpt
                    best_alias = m_alias

            if not best_sentence:
                best_sentence = _extract_matched_sentence(matches[0].start(), matches[0].end(), norm_text)
            if not best_excerpt:
                start = max(0, matches[0].start() - 60)
                end = min(len(norm_text), matches[0].end() + 60)
                best_excerpt = f"...{norm_text[start:end].replace(chr(10), ' ').strip()}..."

            results[canonical] = {
                'canonical': canonical,
                'category': data.get('category', 'Technical Skills'),
                'matched_alias': best_alias,
                'section': best_section,
                'sentence': best_sentence,
                'excerpt': best_excerpt,
                'strength': best_strength,
                'is_project_evidence': is_proj,
                'occurrences': len(matches),
                'is_inferred': False,
                'evidence_type': 'explicit',
            }

    # Deduplication and compound resolution:
    # 1. HTML and CSS (Requirement 2 & 7):
    # Avoid duplicate overlapping entries such as CSS, HTML, and HTML & CSS.
    # Individual technologies (HTML, CSS) are canonical.
    if 'HTML' in results and 'CSS' in results:
        # Both individual technologies are detected; suppress compound HTML & CSS chip
        results.pop('HTML & CSS', None)
    elif 'HTML & CSS' in results:
        # If literal "HTML & CSS" was found without separate detections, decompose into HTML & CSS
        compound = results.pop('HTML & CSS')
        for comp in ['HTML', 'CSS']:
            if comp not in results:
                results[comp] = {
                    'canonical': comp,
                    'category': 'Frontend Development',
                    'matched_alias': comp,
                    'section': compound['section'],
                    'sentence': compound['sentence'],
                    'excerpt': compound['excerpt'],
                    'strength': compound['strength'],
                    'is_project_evidence': compound['is_project_evidence'],
                    'occurrences': compound['occurrences'],
                    'is_inferred': False,
                    'evidence_type': 'explicit',
                }

    # 2. Testing vs Debugging (Requirement 4):
    # Do not infer Testing just because Debugging is mentioned.
    # If candidate only mentioned Debugging, discard any combined Testing & Debugging entry.
    if 'Debugging' in results and 'Testing' not in results:
        results.pop('Testing & Debugging', None)
    elif 'Testing & Debugging' in results:
        # If combined phrase was matched, ensure both Testing and Debugging are credited
        combined = results.pop('Testing & Debugging')
        for comp in ['Testing', 'Debugging']:
            if comp not in results:
                results[comp] = {
                    'canonical': comp,
                    'category': 'Testing & Quality',
                    'matched_alias': comp,
                    'section': combined['section'],
                    'sentence': combined['sentence'],
                    'excerpt': combined['excerpt'],
                    'strength': combined['strength'],
                    'is_project_evidence': combined['is_project_evidence'],
                    'occurrences': combined['occurrences'],
                    'is_inferred': False,
                    'evidence_type': 'explicit',
                }

    return results


def _split_into_sections(text: str) -> List[Tuple[str, int, int]]:
    """
    Identifies common resume section boundaries and returns:
    [(section_title, start_idx, end_idx), ...]
    section_title is human-readable: 'Technical Skills', 'Projects', 'Work Experience',
    'Education', 'Certifications', 'Summary', 'General'
    """
    headings = [
        (r'(?i)(?:^|[\r\n])\s*(?:technical\s+skills|skills\s*(?:&|and)\s*tools|skills|core\s+concepts|core\s+competencies|programming(?:\s+languages)?|web\s+technologies|frameworks?|databases?|developer\s+tools|tools|technical\s+expertise)\b', 'Technical Skills'),
        (r'(?i)(?:^|[\r\n])\s*(?:projects?|academic\s+projects?|key\s+projects?|personal\s+projects?|project\s+experience)\b', 'Projects'),
        (r'(?i)(?:^|[\r\n])\s*(?:work\s+experience|experience|employment|professional\s+experience|internships?|key\s+responsibilities)\b', 'Work Experience'),
        (r'(?i)(?:^|[\r\n])\s*(?:education|academic\s+background|qualifications|academic\s+details|coursework|relevant\s+coursework)\b', 'Education'),
        (r'(?i)(?:^|[\r\n])\s*(?:certifications?(?:\s*(?:&|and)\s*learning)?|certificates?|credentials|licenses?)\b', 'Certifications'),
        (r'(?i)(?:^|[\r\n])\s*(?:professional\s+summary|summary|profile|about\s+me|career\s+objective|objective)\b', 'Summary'),
    ]

    boundaries = []
    for pattern, sec_name in headings:
        for m in re.finditer(pattern, text):
            start_pos = m.start()
            if text[start_pos] in '\r\n':
                start_pos += 1
            boundaries.append((start_pos, sec_name))

    boundaries.sort(key=lambda x: x[0])

    sections = []
    prev_idx = 0
    prev_type = 'General'

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
    active_section = 'General'
    for sec_type, start, end in sections:
        if start <= match_pos < end:
            active_section = sec_type
            break

    ctx_start = max(0, match_pos - 90)
    ctx_end = min(len(full_text), match_pos + 90)
    surrounding = full_text[ctx_start:ctx_end].lower()

    has_action_verbs = bool(re.search(
        r'\b(?:built|developed|implemented|created|designed|integrated|engineered|deployed|applied|used|using|scripting|configured|architected|automated|optimized|managed|maintained|trained|queried)\b',
        surrounding
    ))
    has_basic_cues = bool(re.search(
        r'\b(?:basic|basics|introductory|beginner|learning|familiar|knowledge\s+of)\b',
        surrounding
    ))
    is_in_project = (active_section == 'Projects')
    is_in_experience = (active_section == 'Work Experience')

    if (is_in_project or is_in_experience) and (has_action_verbs or 'technology:' in surrounding or 'tech stack:' in surrounding or 'technologies:' in surrounding):
        strength = 'strong'
    elif has_basic_cues:
        strength = 'basic'
    elif is_in_project or is_in_experience:
        strength = 'strong' if has_action_verbs else 'moderate'
    elif active_section == 'Technical Skills':
        strength = 'basic'
    else:
        strength = 'basic' if not has_action_verbs else 'moderate'

    return (is_in_project or is_in_experience), strength


def sync_catalog_skills_to_db() -> int:
    """
    Populates/updates the Skill model with all canonical skills defined in SKILL_CATALOG.
    Returns the count of newly created skills.
    """
    from skills.models import Skill
    created_count = 0
    for name, data in SKILL_CATALOG.items():
        _, created = Skill.objects.get_or_create(
            name=name,
            defaults={'category': data.get('category', 'Technical Skills')}
        )
        if created:
            created_count += 1
    return created_count
