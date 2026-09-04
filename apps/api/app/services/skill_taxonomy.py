"""
Skill Taxonomy & Normalization Engine — Phase 13.

Normalizes varied skill references into canonical concepts (e.g. "Postgres", "PostgreSQL DB", "pg" -> "PostgreSQL").
Provides hierarchical categorization across technical domains.
"""

from typing import Dict, List, Optional, Set, Tuple


# Canonical Skill Taxonomy mapping: Canonical Name -> Dict of properties
SKILL_TAXONOMY: Dict[str, Dict[str, any]] = {
    # Programming Languages
    "Python": {
        "category": "programming_languages",
        "aliases": ["python", "python3", "py", "cpython"],
        "related": ["FastAPI", "Django", "Flask", "PyTorch"],
    },
    "JavaScript": {
        "category": "programming_languages",
        "aliases": ["javascript", "js", "ecmascript", "es6", "es2020", "esnext"],
        "related": ["TypeScript", "Node.js", "React", "Next.js"],
    },
    "TypeScript": {
        "category": "programming_languages",
        "aliases": ["typescript", "ts"],
        "related": ["JavaScript", "Node.js", "React", "Next.js", "NestJS"],
    },
    "Go": {
        "category": "programming_languages",
        "aliases": ["go", "golang"],
        "related": ["gRPC", "Docker", "Kubernetes", "Microservices"],
    },
    "Rust": {
        "category": "programming_languages",
        "aliases": ["rust", "rustlang", "cargo"],
        "related": ["WebAssembly", "Systems Programming", "Concurrency"],
    },
    "Java": {
        "category": "programming_languages",
        "aliases": ["java", "java 17", "java 21", "jvm"],
        "related": ["Spring Boot", "Kotlin", "Hibernate", "Kafka"],
    },
    "C++": {
        "category": "programming_languages",
        "aliases": ["c++", "cpp", "cplusplus"],
        "related": ["C", "Low-Level Systems", "Concurrency"],
    },

    # Frameworks & Runtimes
    "FastAPI": {
        "category": "frameworks",
        "aliases": ["fastapi", "fast api", "fast-api"],
        "related": ["Python", "Pydantic", "Starlette", "Uvicorn", "REST APIs"],
    },
    "React": {
        "category": "frameworks",
        "aliases": ["react", "react.js", "reactjs"],
        "related": ["JavaScript", "TypeScript", "Next.js", "Zustand", "Redux", "Tailwind CSS"],
    },
    "Next.js": {
        "category": "frameworks",
        "aliases": ["next.js", "nextjs", "next 14", "next 15"],
        "related": ["React", "TypeScript", "SSR", "Server Components"],
    },
    "Node.js": {
        "category": "frameworks",
        "aliases": ["node.js", "nodejs", "node"],
        "related": ["JavaScript", "TypeScript", "Express", "Socket.IO"],
    },
    "Django": {
        "category": "frameworks",
        "aliases": ["django", "django rest framework", "drf"],
        "related": ["Python", "PostgreSQL", "ORM"],
    },
    "Spring Boot": {
        "category": "frameworks",
        "aliases": ["spring boot", "springboot", "spring framework", "spring"],
        "related": ["Java", "Microservices", "Hibernate"],
    },

    # Databases
    "PostgreSQL": {
        "category": "databases",
        "aliases": ["postgres", "postgresql", "postgresql db", "postgres sql", "pg", "psql"],
        "related": ["SQL", "Relational Databases", "pgvector", "Database Indexing", "Transactions"],
    },
    "MySQL": {
        "category": "databases",
        "aliases": ["mysql", "mariadb"],
        "related": ["SQL", "Relational Databases", "InnoDB"],
    },
    "Redis": {
        "category": "databases",
        "aliases": ["redis", "redis cache", "redis cluster"],
        "related": ["Caching", "Pub/Sub", "In-Memory Databases", "Distributed Systems"],
    },
    "MongoDB": {
        "category": "databases",
        "aliases": ["mongodb", "mongo", "documentdb"],
        "related": ["NoSQL", "Document Databases"],
    },
    "Elasticsearch": {
        "category": "databases",
        "aliases": ["elasticsearch", "elastic search", "opensearch"],
        "related": ["Search Engines", "Distributed Indexing"],
    },

    # Distributed Systems & Messaging
    "Kafka": {
        "category": "system_design",
        "aliases": ["kafka", "apache kafka", "confluent kafka"],
        "related": ["Event-Driven Architecture", "Pub/Sub", "Message Queues", "Streaming"],
    },
    "RabbitMQ": {
        "category": "system_design",
        "aliases": ["rabbitmq", "rabbit mq", "amqp"],
        "related": ["Message Queues", "Celery", "Distributed Systems"],
    },
    "Distributed Systems": {
        "category": "system_design",
        "aliases": ["distributed systems", "distributed architecture", "microservices", "service oriented architecture", "soa"],
        "related": ["Kafka", "Consensus", "Raft", "Fault Tolerance", "Scalability", "CAP Theorem"],
    },
    "REST APIs": {
        "category": "system_design",
        "aliases": ["rest", "rest api", "rest apis", "restful", "restful apis"],
        "related": ["FastAPI", "HTTP", "OpenAPI", "API Design"],
    },
    "gRPC": {
        "category": "system_design",
        "aliases": ["grpc", "protocol buffers", "protobuf"],
        "related": ["Microservices", "HTTP/2", "Go", "Distributed Systems"],
    },
    "WebSockets": {
        "category": "system_design",
        "aliases": ["websocket", "websockets", "ws", "socket.io", "realtime"],
        "related": ["Realtime Systems", "Node.js", "Redis Pub/Sub"],
    },
    "WebRTC": {
        "category": "system_design",
        "aliases": ["webrtc", "rtc", "coturn", "stun", "turn"],
        "related": ["Realtime Audio/Video", "Signaling", "P2P"],
    },

    # Cloud & DevOps
    "Docker": {
        "category": "infrastructure",
        "aliases": ["docker", "containerization", "containers", "docker-compose", "docker compose"],
        "related": ["Kubernetes", "DevOps", "CI/CD"],
    },
    "Kubernetes": {
        "category": "infrastructure",
        "aliases": ["kubernetes", "k8s", "k8s cluster", "helm"],
        "related": ["Docker", "Cloud Native", "Container Orchestration", "DevOps"],
    },
    "AWS": {
        "category": "cloud",
        "aliases": ["aws", "amazon web services", "ec2", "s3", "ecs", "eks", "lambda"],
        "related": ["Cloud Computing", "Infrastructure", "MinIO"],
    },
    "GCP": {
        "category": "cloud",
        "aliases": ["gcp", "google cloud", "google cloud platform", "gke"],
        "related": ["Cloud Computing", "Infrastructure"],
    },
    "CI/CD": {
        "category": "devops",
        "aliases": ["ci/cd", "ci cd", "continuous integration", "github actions", "gitlab ci", "jenkins"],
        "related": ["DevOps", "Docker", "Testing"],
    },

    # AI / ML
    "LangGraph": {
        "category": "ai_ml",
        "aliases": ["langgraph", "lang graph"],
        "related": ["LangChain", "Multi-Agent Systems", "LLMs"],
    },
    "LLMs": {
        "category": "ai_ml",
        "aliases": ["llm", "llms", "large language models", "groq", "ollama", "openai", "claude", "gpt-4"],
        "related": ["AI/ML", "Prompt Engineering", "RAG", "Embeddings", "pgvector"],
    },
    "PyTorch": {
        "category": "ai_ml",
        "aliases": ["pytorch", "torch"],
        "related": ["Deep Learning", "Python", "Machine Learning"],
    },

    # Testing & Code Quality
    "Unit Testing": {
        "category": "testing",
        "aliases": ["unit testing", "pytest", "jest", "tdd", "integration testing", "automated testing"],
        "related": ["Code Quality", "CI/CD"],
    },
    "System Design": {
        "category": "system_design",
        "aliases": ["system design", "systems design", "high level design", "hld", "lld", "low level design", "scalability"],
        "related": ["Distributed Systems", "Databases", "Caching", "Load Balancing"],
    },
}

# Reverse index: alias (lowercase stripped) -> canonical name
_ALIAS_INDEX: Dict[str, str] = {}
for canonical_name, data in SKILL_TAXONOMY.items():
    _ALIAS_INDEX[canonical_name.lower().strip()] = canonical_name
    for alias in data.get("aliases", []):
        _ALIAS_INDEX[alias.lower().strip()] = canonical_name


def normalize_skill(skill_name: str) -> Tuple[str, str]:
    """
    Normalizes a skill name to its canonical representation and category.
    Returns: (canonical_name, category)
    """
    if not skill_name:
        return ("Unknown", "general")

    clean = skill_name.strip()
    lower = clean.lower()

    if lower in _ALIAS_INDEX:
        canonical = _ALIAS_INDEX[lower]
        category = SKILL_TAXONOMY.get(canonical, {}).get("category", "general")
        return (canonical, category)

    # Partial / substring match check
    for alias, canonical in _ALIAS_INDEX.items():
        if len(alias) >= 3 and (alias == lower or f" {alias} " in f" {lower} "):
            category = SKILL_TAXONOMY.get(canonical, {}).get("category", "general")
            return (canonical, category)

    # Title-case clean fallback
    title_fallback = clean.title() if len(clean) > 3 else clean.upper()
    return (title_fallback, "general")


def get_skill_category(skill_name: str) -> str:
    """Returns the taxonomy category for a skill."""
    canonical, category = normalize_skill(skill_name)
    return category


def get_related_skills(canonical_skill: str) -> List[str]:
    """Returns related technologies or prerequisites for a canonical skill."""
    data = SKILL_TAXONOMY.get(canonical_skill)
    if data:
        return data.get("related", [])
    return []
