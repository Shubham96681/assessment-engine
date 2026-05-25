"""Pydantic schemas for all API request/response models"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ── Enums ──────────────────────────────────────────────────────────────────────

class QuestionType(str, Enum):
    MCQ = "MCQ"
    SHORT_ANSWER = "ShortAnswer"
    LONG_ANSWER = "LongAnswer"
    FIGURE_BASED = "FigureBased"
    TRUE_FALSE = "TrueFalse"
    FILL_BLANK = "FillBlank"
    ASSERTION_REASON = "AssertionReason"
    MATCH_COLUMN = "MatchColumn"
    CASE_STUDY = "CaseStudy"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class BloomLevel(str, Enum):
    REMEMBER = "Remember"
    UNDERSTAND = "Understand"
    APPLY = "Apply"
    ANALYZE = "Analyze"
    EVALUATE = "Evaluate"
    CREATE = "Create"


class FigureType(str, Enum):
    FLOWCHART = "flowchart"
    LABELED_DIAGRAM = "labeled_diagram"
    BAR_GRAPH = "bar_graph"
    LINE_GRAPH = "line_graph"
    TABLE = "table"
    MIND_MAP = "mind_map"
    VENN_DIAGRAM = "venn_diagram"
    PROCESS_DIAGRAM = "process_diagram"
    CHEMICAL_STRUCTURE = "chemical_structure"


# ── Auth ───────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str
    institution: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    full_name: str
    role: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    institution: Optional[str]
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Document ───────────────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: str
    filename: str
    original_filename: Optional[str]
    subject: Optional[str]
    class_level: Optional[str]
    total_chunks: int
    total_pages: int
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TheoremCoverageOut(BaseModel):
    id: str
    label: str = ""
    archetype_id: str = ""
    difficulty: str = "medium"
    importance: str = "important"
    weight: float = 0.85
    cognitive_type: str = "computation"
    combines_with: List[str] = []


class TopicProfileOut(BaseModel):
    document_id: str = ""
    primary_topic: str
    locked_chapter: str
    locked_chapter_source: str = ""
    confidence: float = 0.0
    subject: str = "Mathematics"
    class_level: str = ""
    subtopics: List[str] = []
    secondary_chapters: List[str] = []
    required_theorems: List[TheoremCoverageOut] = []
    retrieval_confidence: Optional[float] = None
    generation_mode: str = "pdf_rich"
    sample_pages: List[int] = []
    chunk_count_used: int = 0
    total_chunks_db: int = 0
    index_status: str = ""
    agents: List[str] = ["topic_agent", "retriever_agent"]


# ── Question Config ────────────────────────────────────────────────────────────

class DifficultyDistribution(BaseModel):
    easy: int = Field(default=30, ge=0, le=100)
    medium: int = Field(default=50, ge=0, le=100)
    hard: int = Field(default=20, ge=0, le=100)


class MarksPerType(BaseModel):
    MCQ: float = 1.0
    ShortAnswer: float = 3.0
    LongAnswer: float = 5.0
    FigureBased: float = 4.0
    TrueFalse: float = 1.0
    FillBlank: float = 1.0
    AssertionReason: float = 2.0
    MatchColumn: float = 3.0
    CaseStudy: float = 6.0


class GenerationConfig(BaseModel):
    document_id: Optional[str] = None
    use_chapter_pdf: bool = Field(
        default=False,
        description="When true and document_id is set, RAG uses the uploaded chapter PDF. When false, CBSE topic-only mode.",
    )
    source_document_id: Optional[str] = Field(
        default=None,
        description="User-selected PDF id when use_chapter_pdf is false (stored for reference only).",
    )
    locked_chapter: Optional[str] = Field(
        default=None,
        description="Chapter key from /chapters (e.g. trigonometry, circles). Required for topic-only generation.",
    )
    title: Optional[str] = "Assessment"
    question_types: List[QuestionType] = [QuestionType.MCQ, QuestionType.SHORT_ANSWER]
    difficulty_distribution: DifficultyDistribution = DifficultyDistribution()
    bloom_levels: List[BloomLevel] = [BloomLevel.REMEMBER, BloomLevel.UNDERSTAND, BloomLevel.APPLY]
    total_questions: int = Field(default=20, ge=1, le=100)
    marks_per_type: Optional[MarksPerType] = None
    figure_types: Optional[List[FigureType]] = None
    subject: Optional[str] = None
    class_level: Optional[str] = None
    language: str = "English"
    negative_marking: bool = False
    topic_focus: Optional[str] = None
    exclude_topics: Optional[str] = None
    instructions: Optional[str] = None
    weak_in: Optional[List[str]] = None
    strong_in: Optional[List[str]] = None
    paper_template: Optional[str] = Field(
        default=None,
        description="Paper template id (chained_concentric, mixed_independent, auto). Overrides DEFAULT_PAPER_TEMPLATE when set.",
    )


# ── MCQ Option ─────────────────────────────────────────────────────────────────

class MCQOption(BaseModel):
    label: str      # A, B, C, D
    text: str
    is_correct: bool = False


# ── Question Out ───────────────────────────────────────────────────────────────

class QuestionOut(BaseModel):
    id: str
    content: str
    question_type: str
    difficulty: str
    bloom_level: Optional[str]
    options: Optional[List[MCQOption]]
    correct_answer: Optional[str]
    explanation: Optional[str]
    marks: float
    figure_url: Optional[str]
    figure_type: Optional[str]
    quality_score: float
    created_at: datetime

    class Config:
        from_attributes = True


# ── Assessment Out ─────────────────────────────────────────────────────────────

class GenerationLogStep(BaseModel):
    step: int
    question_type: str
    difficulty: str
    bloom_level: str
    count_requested: int
    rag_query: str
    rag_chunks: List[Dict[str, Any]] = []
    llm_prompt: str
    llm_response: str
    questions_parsed: int
    question_previews: List[str] = []


class AssessmentStatusOut(BaseModel):
    """Lightweight poll endpoint — no questions or generation_log."""
    id: str
    title: Optional[str] = None
    status: str
    question_count: int = 0
    total_marks: float = 0.0


class AssessmentListItemOut(BaseModel):
    """My Assessments page — no generation_log (can be multi‑MB per row)."""
    id: str
    title: Optional[str] = None
    total_marks: float = 0.0
    status: str
    pdf_url: Optional[str] = None
    answer_key_url: Optional[str] = None
    generation_num: int = 1
    created_at: datetime

    class Config:
        from_attributes = True


class AssessmentOut(BaseModel):
    id: str
    title: Optional[str]
    config: Dict[str, Any]
    total_marks: float
    status: str
    pdf_url: Optional[str]
    answer_key_url: Optional[str]
    generation_num: int
    created_at: datetime
    generation_log: Optional[List[Dict[str, Any]]] = None
    questions: Optional[List[QuestionOut]] = None

    class Config:
        from_attributes = True


# ── Feedback ───────────────────────────────────────────────────────────────────

class FeedbackCreate(BaseModel):
    question_id: str
    assessment_id: str
    rating: int = Field(ge=1, le=5)
    tags: Optional[List[str]] = []
    comment: Optional[str] = None


class FeedbackOut(BaseModel):
    id: str
    rating: int
    tags: Optional[List[str]]
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Analytics ──────────────────────────────────────────────────────────────────

class AnalyticsOut(BaseModel):
    total_documents: int
    total_assessments: int
    total_questions_generated: int
    avg_quality_score: float
    bloom_distribution: Dict[str, int]
    difficulty_distribution: Dict[str, int]
    question_type_distribution: Dict[str, int]
    recent_assessments: List[Dict[str, Any]]
