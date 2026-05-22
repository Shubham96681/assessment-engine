"""All SQLAlchemy models"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean,
    DateTime, ForeignKey, JSON, ARRAY
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    institution = Column(String(255))
    role = Column(String(50), default="teacher")   # teacher | admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    documents = relationship("Document", back_populates="owner")
    assessments = relationship("Assessment", back_populates="owner")


class Document(Base):
    __tablename__ = "documents"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500))
    file_path = Column(Text)
    subject = Column(String(255))
    class_level = Column(String(100))
    total_chunks = Column(Integer, default=0)
    total_pages = Column(Integer, default=0)
    status = Column(String(50), default="pending")  # pending | processing | ready | failed
    error_message = Column(Text)
    metadata_ = Column("metadata", JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="documents")
    questions = relationship("Question", back_populates="document")
    assessments = relationship("Assessment", back_populates="document")


class Question(Base):
    __tablename__ = "questions"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    assessment_id = Column(String(36), ForeignKey("assessments.id"), nullable=True)
    content = Column(Text, nullable=False)
    question_type = Column(String(100))   # MCQ|ShortAnswer|LongAnswer|FigureBased|TrueFalse|FillBlank|AssertionReason|MatchColumn|CaseStudy
    difficulty = Column(String(50))       # easy | medium | hard
    bloom_level = Column(String(100))     # Remember|Understand|Apply|Analyze|Evaluate|Create
    options = Column(JSON)                # for MCQ: [{label, text, is_correct}]
    correct_answer = Column(Text)
    explanation = Column(Text)
    marks = Column(Float, default=1.0)
    figure_url = Column(Text)
    figure_type = Column(String(100))     # flowchart|diagram|graph|table|chemical|mindmap
    figure_spec = Column(JSON)            # raw spec used to generate the figure
    source_chunks = Column(JSON)          # list of chunk IDs used
    content_hash = Column(String(64))     # SHA256 for exact dedup
    embedding_id = Column(String(100))    # Qdrant point ID
    quality_score = Column(Float, default=0.0)
    times_used = Column(Integer, default=0)
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    document = relationship("Document", back_populates="questions")
    feedback_items = relationship("QuestionFeedback", back_populates="question")


class Assessment(Base):
    __tablename__ = "assessments"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    title = Column(String(500))
    config = Column(JSON)           # full generation config
    question_ids = Column(JSON)     # list of question UUIDs
    pdf_url = Column(Text)
    answer_key_url = Column(Text)
    generation_num = Column(Integer, default=1)
    total_marks = Column(Float, default=0.0)
    status = Column(String(50), default="pending")
    generation_log = Column(JSON, default=list)  # RAG + LLM prompt/response trace per step
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="assessments")
    document = relationship("Document", back_populates="assessments")
    feedback_items = relationship("QuestionFeedback", back_populates="assessment")


class QuestionFeedback(Base):
    __tablename__ = "question_feedback"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    question_id = Column(String(36), ForeignKey("questions.id"), nullable=False)
    assessment_id = Column(String(36), ForeignKey("assessments.id"), nullable=False)
    rating = Column(Integer)   # 1–5
    tags = Column(JSON)        # ["too_easy","ambiguous","out_of_context"]
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    question = relationship("Question", back_populates="feedback_items")
    assessment = relationship("Assessment", back_populates="feedback_items")


class GenerationHistory(Base):
    __tablename__ = "generation_history"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    question_hash = Column(String(64), nullable=False)
    question_embedding_id = Column(String(100))
    subject = Column(String(255))
    class_level = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), unique=True)
    question_type = Column(String(100))
    bloom_level = Column(String(100))
    template_text = Column(Text)
    version = Column(Integer, default=1)
    performance_score = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
