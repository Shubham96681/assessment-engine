-- Assessment Engine — PostgreSQL Initialization
-- This runs automatically via Docker on first start

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Users
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    institution VARCHAR(255),
    role VARCHAR(50) DEFAULT 'teacher',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Documents
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500),
    file_path TEXT,
    subject VARCHAR(255),
    class_level VARCHAR(100),
    total_chunks INTEGER DEFAULT 0,
    total_pages INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Assessments
CREATE TABLE IF NOT EXISTS assessments (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    document_id VARCHAR(36) REFERENCES documents(id) ON DELETE CASCADE,
    title VARCHAR(500),
    config JSONB DEFAULT '{}',
    question_ids JSONB DEFAULT '[]',
    pdf_url TEXT,
    answer_key_url TEXT,
    generation_num INTEGER DEFAULT 1,
    total_marks FLOAT DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    generation_log JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Questions
CREATE TABLE IF NOT EXISTS questions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    document_id VARCHAR(36) REFERENCES documents(id) ON DELETE CASCADE,
    assessment_id VARCHAR(36) REFERENCES assessments(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    question_type VARCHAR(100),
    difficulty VARCHAR(50),
    bloom_level VARCHAR(100),
    options JSONB,
    correct_answer TEXT,
    explanation TEXT,
    marks FLOAT DEFAULT 1.0,
    figure_url TEXT,
    figure_type VARCHAR(100),
    figure_spec JSONB,
    source_chunks JSONB,
    content_hash VARCHAR(64),
    embedding_id VARCHAR(100),
    quality_score FLOAT DEFAULT 0.0,
    times_used INTEGER DEFAULT 0,
    is_approved BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Question Feedback
CREATE TABLE IF NOT EXISTS question_feedback (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    question_id VARCHAR(36) REFERENCES questions(id) ON DELETE CASCADE,
    assessment_id VARCHAR(36) REFERENCES assessments(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    tags JSONB DEFAULT '[]',
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Generation History (for dedup)
CREATE TABLE IF NOT EXISTS generation_history (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    question_hash VARCHAR(64) NOT NULL,
    question_embedding_id VARCHAR(100),
    subject VARCHAR(255),
    class_level VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Prompt Templates (for self-enhancement)
CREATE TABLE IF NOT EXISTS prompt_templates (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name VARCHAR(255) UNIQUE,
    question_type VARCHAR(100),
    bloom_level VARCHAR(100),
    template_text TEXT,
    version INTEGER DEFAULT 1,
    performance_score FLOAT DEFAULT 0.0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_questions_assessment ON questions(assessment_id);
CREATE INDEX IF NOT EXISTS idx_questions_document ON questions(document_id);
CREATE INDEX IF NOT EXISTS idx_questions_hash ON questions(content_hash);
CREATE INDEX IF NOT EXISTS idx_assessments_user ON assessments(user_id);
CREATE INDEX IF NOT EXISTS idx_assessments_status ON assessments(status);
CREATE INDEX IF NOT EXISTS idx_feedback_question ON question_feedback(question_id);
CREATE INDEX IF NOT EXISTS idx_history_user ON generation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_history_hash ON generation_history(question_hash);

-- Demo admin user (password: admin123)
INSERT INTO users (id, email, hashed_password, full_name, institution, role)
VALUES (
    'a0000000-0000-4000-8000-000000000001',
    'demo@assessment.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMUMYPLYBGJNFvVt9mAQh6Bq..',
    'Admin Teacher',
    'Assessment Engine Demo',
    'admin'
) ON CONFLICT (email) DO NOTHING;
