"""
Application Configuration — Pydantic Settings
"""
import re

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

# Substrings that mean the value is still a template from .env.example
_PLACEHOLDER_KEY_MARKERS = (
    "your_openai_api_key",
    "your_gemini_api_key",
    "your_groq_api_key",
    "your-super-secret",
    "changeme",
    "replace_me",
    "insert_key",
    "api_key_here",
)


def sanitize_api_key(value: str | None) -> str:
    """Treat .env.example placeholders as unset so RAG file agent / local embeds run."""
    v = (value or "").strip().strip('"').strip("'")
    if not v or len(v) < 8:
        return ""
    low = v.lower()
    if low in ("false", "true", "none", "null", "undefined"):
        return ""
    if any(marker in low for marker in _PLACEHOLDER_KEY_MARKERS):
        return ""
    if re.fullmatch(r"x{6,}", low):
        return ""
    return v


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "Assessment Engine"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002"

    # LLM
    OPENAI_API_KEY: str = ""
    GOOGLE_GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_ENABLED: bool = False
    # RAG file bridge (rag_query.txt → rag_response.txt — Cursor agent)
    RAG_FILE_AGENT_ENABLED: bool = True
    # Cursor agent only — never Groq/Gemini/OpenAI/Ollama/local templates
    RAG_FILE_AGENT_ONLY: bool = True
    RAG_FILE_TIMEOUT_SECONDS: int = 300
    RAG_FILE_RETRY_TIMEOUT_SECONDS: int = 90
    RAG_FILE_SLOT_REGEN_TIMEOUT_SECONDS: int = 120
    RAG_FILE_POLL_INTERVAL_SECONDS: float = 0.2
    RAG_FILE_MAX_RETRIES: int = 6
    # False = never use local_llm template stubs; use Cursor rag_response.txt and/or cloud APIs only
    ENABLE_LOCAL_LLM_FALLBACK: bool = False
    PRIMARY_LLM: str = "gemini"
    FAST_LLM: str = "gemini-flash"

    # Vector store: faiss (local, no Docker) | qdrant (needs Docker)
    VECTOR_STORE_BACKEND: str = "faiss"
    FAISS_DATA_PATH: str = "./data/faiss"
    EMBEDDING_DIMENSION: int = 384  # all-MiniLM-L6-v2; use 1536 with OpenAI + Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_QUESTIONS: str = "questions"
    QDRANT_COLLECTION_HISTORY: str = "generation_history"
    QDRANT_COLLECTION_DOCUMENTS: str = "documents"
    QDRANT_COLLECTION_CBSE_REFERENCE: str = "cbse_reference"

    # Database — SQLite by default (no Docker); set postgresql+asyncpg://... for Postgres
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/assessment.db"
    DATABASE_SYNC_URL: str = "sqlite:///./data/assessment.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Storage
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_PATH: str = "./uploads"

    # PDF / figure export quality
    FIGURE_EXPORT_DPI: int = 300
    # Geometry diagram typography (matplotlib points — readable after PDF downscale)
    FIGURE_POINT_LABEL_FONT_PT: int = 17
    FIGURE_SEGMENT_LABEL_FONT_PT: int = 12
    FIGURE_TITLE_FONT_PT: int = 14
    FIGURE_POINT_MARKER_SIZE: float = 10.0
    PDF_FIGURE_WIDTH_MM: float = 72
    PDF_FIGURE_HEIGHT_MM: float = 56
    PDF_FIGURE_COL_MM: float = 72
    PDF_FIGURE_PANEL_MAX_MM: float = 52
    PDF_FONT_QUESTION_PT: float = 11
    PDF_FONT_BODY_PT: float = 10.5
    # Blank ruled lines under each question in the question paper PDF
    PDF_MATH_LATEX: bool = True
    PDF_MATH_DPI: int = 150
    PDF_SHOW_ANSWER_LINES: bool = False
    # CBSE-style instructions box below the header (off by default)
    PDF_SHOW_INSTRUCTIONS: bool = False
    PDF_RE_ENRICH_FIGURES: bool = True
    ENABLE_PDF_POST_VALIDATE: bool = True
    PDF_POST_VALIDATE_STRICT: bool = False
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
    # Generate pool = delivery * multiplier, validate all, keep best delivery count
    GENERATION_OVERSAMPLE_ENABLED: bool = True
    GENERATION_OVERSAMPLE_MULTIPLIER: float = 2.0
    QUALITY_REGEN_ENABLED: bool = True
    QUALITY_REGEN_USE_CURSOR: bool = True
    QUALITY_REGEN_MAX_PER_SLOT: int = 2
    MAX_CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    MAX_RETRIEVAL_CHUNKS: int = 6
    # phyEngine-style indexing & retrieval
    ENABLE_STRUCTURED_CHUNKING: bool = True
    RETRIEVAL_SEARCH_MULTIPLIER: float = 2.0
    ENABLE_RETRIEVAL_RERANK: bool = True
    ENABLE_CROSS_ENCODER_RERANK: bool = False
    # RL feedback loop (human ratings → reward scorer → combined_score)
    ENABLE_RL_REWARD: bool = True
    RL_REWARD_WEIGHT: float = 0.14
    RL_FEEDBACK_PATH: str = "./data/rl/feedback.jsonl"
    RL_TAG_WEIGHT_PATH: str = "./data/rl/tag_weights.json"
    RL_TRANSFORMER_MODEL_PATH: str = "./data/rl/reward_model"
    ENABLE_RL_TRANSFORMER: bool = False
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
    # Reject hallucinated formulas, calculus in trig, Unicode/LaTeX corruption (Groq/LLM)
    ENABLE_MATH_STEM_VALIDATION: bool = True
    ENABLE_PAPER_DEPENDENCY_GRAPH: bool = True
    ENABLE_CROSS_QUESTION_CONSISTENCY: bool = True
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
    ENABLE_HARDNESS_SCORER: bool = True
    ENABLE_EXAMINER_SIMULATION: bool = True
    # Paper layout: auto | chained_concentric | mixed_independent | chained_triangle
    DEFAULT_PAPER_TEMPLATE: str = "auto"
    # CBSE board-paper benchmark — dynamic floors from CBSE_QuestionPapers/*.pdf
    ENABLE_CHAPTER_PAPER_QUALITY: bool = True
    # When False, integrity issues are logged but the paper still exports (UI shows questions only).
    PAPER_INTEGRITY_BLOCK_EXPORT: bool = False
    ENABLE_CBSE_BENCHMARK: bool = True
    CBSE_BENCHMARK_ROOT: str = "CBSE_QuestionPapers"
    CBSE_BENCHMARK_CACHE_PATH: str = "./data/cbse_benchmark/benchmark.json"
    CBSE_BENCHMARK_MAX_AGE_HOURS: int = 168
    CBSE_BENCHMARK_AUTO_BUILD: bool = True
    # CBSE reference index — question stems by chapter/topic from CBSE_QuestionPapers/
    ENABLE_CBSE_REFERENCE: bool = True
    CBSE_REFERENCE_CACHE_PATH: str = "./data/cbse_reference/manifest.json"
    CBSE_REFERENCE_TOP_K: int = 8
    CBSE_REFERENCE_AUTO_BUILD: bool = True
    CBSE_REFERENCE_MIN_CHAPTER_CONF: float = 0.28

    @staticmethod
    def _normalize_vector_store_backend(value: object) -> str:
        """Default to FAISS (local). Only explicit 'qdrant' enables Docker Qdrant."""
        raw = str(value or "faiss").strip().lower()
        if raw == "qdrant":
            return "qdrant"
        return "faiss"

    @field_validator("VECTOR_STORE_BACKEND", mode="before")
    @classmethod
    def _coerce_vector_backend(cls, v: object) -> str:
        return cls._normalize_vector_store_backend(v)

    @model_validator(mode="after")
    def _sanitize_secrets_and_llm_flags(self) -> "Settings":
        object.__setattr__(
            self, "OPENAI_API_KEY", sanitize_api_key(self.OPENAI_API_KEY)
        )
        object.__setattr__(
            self,
            "GOOGLE_GEMINI_API_KEY",
            sanitize_api_key(self.GOOGLE_GEMINI_API_KEY),
        )
        object.__setattr__(self, "GROQ_API_KEY", sanitize_api_key(self.GROQ_API_KEY))
        if self.RAG_FILE_AGENT_ONLY and not (
            self.OPENAI_API_KEY or self.GOOGLE_GEMINI_API_KEY
        ):
            object.__setattr__(self, "ENABLE_SELF_ENHANCEMENT", False)
        backend = self._normalize_vector_store_backend(self.VECTOR_STORE_BACKEND)
        if backend != self.VECTOR_STORE_BACKEND:
            object.__setattr__(self, "VECTOR_STORE_BACKEND", backend)
        return self

    def has_cloud_llm(self) -> bool:
        return bool(self.OPENAI_API_KEY or self.GOOGLE_GEMINI_API_KEY or self.GROQ_API_KEY)


settings = Settings()
