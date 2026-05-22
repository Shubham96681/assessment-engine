"""
Application Configuration — Pydantic Settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "Assessment Engine"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    # LLM
    OPENAI_API_KEY: str = ""
    GOOGLE_GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_ENABLED: bool = True
  # RAG file bridge (rag_query.txt → rag_response.txt, e.g. Cursor agent)
    RAG_FILE_AGENT_ENABLED: bool = True
    # When true with RAG file agent: never call Groq/Gemini/OpenAI (avoids instant fail on bad API keys)
    RAG_FILE_AGENT_ONLY: bool = True
    RAG_FILE_TIMEOUT_SECONDS: int = 180
    # Second full-paper attempt: shorter wait when rag_response is still stale
    RAG_FILE_RETRY_TIMEOUT_SECONDS: int = 45
    RAG_FILE_SLOT_REGEN_TIMEOUT_SECONDS: int = 180
    RAG_FILE_POLL_INTERVAL_SECONDS: float = 2.0
    PRIMARY_LLM: str = "gemini"
    FAST_LLM: str = "gemini-flash"

    # Vector Store
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_QUESTIONS: str = "questions"
    QDRANT_COLLECTION_HISTORY: str = "generation_history"
    QDRANT_COLLECTION_DOCUMENTS: str = "documents"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://assessment_user:assessment_pass@localhost:5433/assessment_db"
    DATABASE_SYNC_URL: str = "postgresql://assessment_user:assessment_pass@localhost:5433/assessment_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Storage
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_PATH: str = "./uploads"
    AWS_S3_BUCKET: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"

    # Auth
    SECRET_KEY: str = "dev-secret-key-change-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Generation
    DEDUP_SIMILARITY_THRESHOLD: float = 0.92
    DEDUP_BATCH_SIMILARITY_THRESHOLD: float = 0.90
    DEDUP_MAX_REGEN_ATTEMPTS: int = 2
    QUALITY_REGEN_ENABLED: bool = True
    QUALITY_REGEN_USE_CURSOR: bool = True
    QUALITY_REGEN_MAX_PER_SLOT: int = 2
    MAX_CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    MAX_RETRIEVAL_CHUNKS: int = 6
    # 0 = index all pages on upload; set e.g. 25 to cap ingestion time
    MAX_INGEST_PAGES: int = 0
    ENABLE_INGEST_OCR: bool = False
    INGEST_EMBED_BATCH_SIZE: int = 32
    ENABLE_FIGURE_GENERATION: bool = True
    ENABLE_SELF_ENHANCEMENT: bool = True
    MAX_QUESTIONS_PER_GENERATION: int = 100
    MULTI_AGENT_ORCHESTRATION: bool = True
    TOPIC_GATE_LENIENT_FALLBACK: bool = True
    RETRIEVAL_CONFIDENCE_THRESHOLD: float = 0.45
    RETRIEVAL_MIN_CHUNKS: int = 2
    RETRIEVAL_MIN_MEAN_SCORE: float = 0.35
    TOPIC_ALIGNMENT_ACCEPT_THRESHOLD: float = 0.55
    TOPIC_ALIGNMENT_REJECT_THRESHOLD: float = 0.35
    MAX_SAME_THEOREM_RATIO: float = 0.4
    MINIMUM_THEOREM_COVERAGE_SCORE: float = 0.5
    MINIMUM_WEIGHTED_COVERAGE_SCORE: float = 0.55
    THEOREM_COVERAGE_ENFORCE: bool = True
    CONTROLLED_ORGANIC_NOISE: float = 0.15
    MINIMUM_COGNITIVE_DIVERSITY_SCORE: float = 0.4
    GENERATION_MEMORY_LIMIT: int = 80
    ENABLE_STUDENT_SKILL_TARGETING: bool = True
    ENABLE_GENERATION_MEMORY: bool = True
    ENABLE_STEM_DEPENDENCY_VALIDATION: bool = True
    ENABLE_THEOREM_TOPOLOGY_VALIDATION: bool = True
    ENABLE_COGNITIVE_GRAPH_VALIDATION: bool = True
    ENABLE_ARC_GEOMETRY_VALIDATION: bool = True
    ENABLE_FIGURE_NECESSITY_VALIDATION: bool = True
    ENABLE_REJECTION_CORPUS: bool = True
    REJECTION_CORPUS_LIMIT: int = 40
    REJECTION_CORPUS_PROMPT_MAX_EXAMPLES: int = 8
    SOLUTION_ELEGANCE_WEIGHT: float = 0.12
    ENABLE_SEMANTIC_PROMPT_PURITY: bool = True
    SEMANTIC_PURITY_MARGIN: float = 0.04
    SEMANTIC_PURITY_MIN_LOCKED_SIM: float = 0.22
    ENABLE_PROMPT_SECTION_DOMINANCE: bool = True
    PROMPT_SECTION_DOMINANCE_STRICT: bool = True
    PROMPT_FOREIGN_TOPIC_RATIO_MAX: float = 0.10


settings = Settings()
