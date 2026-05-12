# Assessment Engine - Implementation Plan

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Scalable System Architecture](#scalable-system-architecture)
4. [Database Design](#database-design)
5. [Resource Management & Question Extraction](#resource-management--question-extraction)
6. [Application Architecture](#application-architecture)
7. [API Design](#api-design)
8. [Edge Cases & Error Handling](#edge-cases--error-handling)
9. [Security Considerations](#security-considerations)
10. [Performance Optimization](#performance-optimization)
11. [Deployment Strategy](#deployment-strategy)
12. [Monitoring & Observability](#monitoring--observability)
13. [Implementation Phases](#implementation-phases)

---

## Executive Summary

### Objective
Build a scalable, robust assessment engine for schools and teachers to generate, manage, and administer tests for students.

### Key Requirements
- Multi-tenant architecture supporting multiple schools
- Role-based access control (Admin, Teacher, Student)
- Scalable to handle 10,000+ concurrent users
- Support for multiple question types (MCQ, descriptive, coding, etc.)
- Real-time test taking and auto-grading
- Comprehensive analytics and reporting
- 99.9% uptime availability

### Technology Stack Recommendations
- **Backend**: Node.js/Express or Python/FastAPI
- **Database**: PostgreSQL (relational) + Redis (caching) + MongoDB (question bank)
- **Message Queue**: RabbitMQ or AWS SQS
- **File Storage**: AWS S3 or MinIO
- **Frontend**: React.js with TypeScript
- **State Management**: Redux Toolkit
- **Real-time**: Socket.io
- **Containerization**: Docker + Kubernetes
- **AI/ML**: Python + TensorFlow/PyTorch or OpenAI API
- **OCR**: Tesseract, AWS Textract, or Google Vision API
- **Document Processing**: pdfplumber, PyPDF2, pdf.js
- **Vector Database**: Pinecone or Weaviate (for semantic search)

---

## System Overview

### User Roles & Permissions

#### 1. School Admin
- Manage school settings
- Create/manage teacher accounts
- View school-wide analytics
- Configure assessment policies
- Manage subscriptions/billing

#### 2. Teacher
- Create and manage tests
- Create question bank
- Schedule tests
- Monitor student attempts
- Grade subjective answers
- View class performance
- Generate reports

#### 3. Student
- Take scheduled tests
- View test results
- Track progress
- Access learning resources

### Core Features
1. **Test Management**
   - Create tests with multiple question types
   - Configure time limits, attempts, shuffle options
   - Preview tests before publishing
   - Schedule tests with date/time windows
   - Duplicate tests for reuse

2. **Question Bank**
   - Support for MCQs, true/false, fill-in-blank, descriptive, coding
   - Tag questions by subject, topic, difficulty
   - Import/export questions (JSON, CSV)
   - Share questions across teachers
   - Question versioning
   - AI-powered question extraction from resources

3. **Resource Management**
   - Upload books class-wise and subject-wise
   - Upload previous year question papers
   - Organize resources by class, subject, year
   - Extract questions automatically from PDFs, images
   - Search and filter resources
   - Resource sharing across teachers

4. **Test Taking**
   - Secure browser-based test interface
   - Timer with auto-submit
   - Question navigation
   - Save progress periodically
   - Anti-cheating measures
   - Offline support (PWA)

5. **Grading & Analytics**
   - Auto-grading for objective questions
   - Manual grading interface for subjective
   - Detailed performance reports
   - Class-wise analytics
   - Question-wise analysis
   - Comparative reports

6. **Communication**
   - Notifications for test schedules
   - Result announcements
   - Feedback system

---

## Scalable System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Load Balancer                        │
│                    (AWS ALB / NGINX)                        │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼──────┐    ┌────────▼────────┐    ┌──────▼──────┐
│   Web App    │    │   API Gateway   │    │  WebSocket  │
│  (React SPA) │    │  (Kong/AWS API) │    │   Server    │
└──────────────┘    └─────────────────┘    └─────────────┘
        │                     │                     │
        │            ┌────────▼────────┐            │
        │            │  Auth Service   │            │
        │            │  (JWT/OAuth2)   │            │
        │            └─────────────────┘            │
        │                     │                     │
        │    ┌────────────────┼────────────────┐    │
        │    │                │                │    │
┌───────▼────▼────┐  ┌───────▼──────┐  ┌──────▼───────┐
│  Test Service   │  │  Question    │  │  Grading     │
│  (Test Mgmt)    │  │  Service     │  │  Service     │
└─────────────────┘  └──────────────┘  └──────────────┘
        │                │                │
        │    ┌───────────┼───────────┐    │
        │    │           │           │    │
┌───────▼────▼────┐ ┌───▼────┐ ┌─────▼────┐
│  Analytics      │ │ User   │ │ Notification│
│  Service        │ │ Service│ │ Service    │
└─────────────────┘ └────────┘ └────────────┘
        │                │           │
        └────────────────┼───────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼──────┐  ┌──────▼──────┐  ┌─────▼──────┐
│  PostgreSQL  │  │    Redis    │  │  MongoDB   │
│  (Primary)   │  │   (Cache)   │  │(Questions) │
└──────────────┘  └─────────────┘  └────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
              ┌──────────▼──────────┐
              │   Message Queue     │
              │  (RabbitMQ/SQS)     │
              └─────────────────────┘
                         │
              ┌──────────▼──────────┐
              │   Background Jobs    │
              │ (Grading, Reports)   │
              └─────────────────────┘
```

### Microservices Architecture

#### 1. Authentication Service
- User registration/login
- JWT token generation/validation
- Password management
- OAuth2 integration (Google, Microsoft)
- Session management

#### 2. User Management Service
- Profile management
- Role-based access control
- School/organization management
- Teacher-student assignments

#### 3. Question Bank Service
- CRUD operations for questions
- Question categorization and tagging
- Import/export functionality
- Question search and filtering
- Question versioning

#### 4. Test Management Service
- Test creation and configuration
- Test scheduling
- Question selection (random/manual)
- Test publishing/unpublishing
- Test duplication and templates

#### 5. Test Taking Service
- Test delivery
- Answer submission
- Progress tracking
- Time management
- Auto-save functionality
- Anti-cheating validation

#### 6. Grading Service
- Auto-grading for objective questions
- Manual grading interface
- Grade calculation
- Partial scoring support
- Grading rubrics

#### 7. Analytics Service
- Performance metrics calculation
- Report generation
- Data aggregation
- Export functionality
- Dashboard data

#### 8. Notification Service
- Email notifications
- SMS notifications
- In-app notifications
- Push notifications
- Notification preferences

#### 9. File Storage Service
- Question media upload/download
- Student submission handling
- Document storage
- CDN integration
- Book and question paper storage
- File processing and OCR

#### 10. Resource Management Service
- Book upload and management
- Question paper upload and management
- Resource categorization (class, subject, year)
- Resource metadata extraction
- Resource search and filtering
- Resource sharing

#### 11. AI/ML Service
- Question extraction from documents
- OCR for scanned documents
- NLP for question identification
- Question classification and tagging
- Answer extraction
- Quality scoring of extracted questions

#### 12. Document Processing Service
- PDF parsing and extraction
- Image preprocessing
- Text extraction
- Table detection and extraction
- Mathematical formula recognition

### Scalability Strategies

#### Horizontal Scaling
- Stateless service design
- Container orchestration with Kubernetes
- Auto-scaling based on CPU/memory metrics
- Database read replicas
- Connection pooling

#### Vertical Scaling
- Optimize database queries
- Index optimization
- Caching strategies
- Code optimization

#### Caching Strategy
- **Redis** for:
  - Session storage
  - Frequently accessed questions
  - Test configurations
  - User permissions
  - API response caching

#### Database Sharding Strategy
- Shard by school_id for multi-tenant isolation
- Shard by test_id for test-related data
- Shard by user_id for user-specific data

#### Load Balancing
- Application load balancer for web servers
- Database load balancer for read replicas
- CDN for static assets

---

## Database Design

### Database Technology Selection

#### PostgreSQL (Single Database Solution)
- **All Data Storage**: Unified database for complete application
- **ACID Compliance**: Full transactional integrity
- **Advanced Features**: JSONB, Full-text search, Partitioning, Row-level security
- **Scalability**: Read replicas, partitioning, connection pooling
- **Performance**: Optimized indexing, query optimization, materialized views

#### Redis (In-Memory Cache)
- Session management
- Real-time test data
- Rate limiting
- Query result caching
- Temporary data storage

### PostgreSQL Schema

```sql
-- Schools/Organizations
CREATE TABLE schools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    domain VARCHAR(255),
    logo_url VARCHAR(500),
    address TEXT,
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    subscription_plan VARCHAR(50) DEFAULT 'basic',
    subscription_status VARCHAR(50) DEFAULT 'active',
    subscription_expiry TIMESTAMP,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX idx_schools_code ON schools(code);
CREATE INDEX idx_schools_subscription_status ON schools(subscription_status);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID REFERENCES schools(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'teacher', 'student')),
    profile_picture_url VARCHAR(500),
    phone VARCHAR(50),
    date_of_birth DATE,
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    last_login_at TIMESTAMP,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX idx_users_school_id ON users(school_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- Classes/Groups
CREATE TABLE classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID REFERENCES schools(id) NOT NULL,
    name VARCHAR(255) NOT NULL,
    grade VARCHAR(50),
    section VARCHAR(50),
    teacher_id UUID REFERENCES users(id),
    academic_year VARCHAR(50),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX idx_classes_school_id ON classes(school_id);
CREATE INDEX idx_classes_teacher_id ON classes(teacher_id);

-- Student-Class Enrollments
CREATE TABLE student_enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES users(id) NOT NULL,
    class_id UUID REFERENCES classes(id) NOT NULL,
    roll_number VARCHAR(50),
    enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, class_id, academic_year)
);

CREATE INDEX idx_enrollments_student_id ON student_enrollments(student_id);
CREATE INDEX idx_enrollments_class_id ON student_enrollments(class_id);

-- Subjects
CREATE TABLE subjects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID REFERENCES schools(id) NOT NULL,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50),
    description TEXT,
    teacher_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX idx_subjects_school_id ON subjects(school_id);

-- Tests
CREATE TABLE tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID REFERENCES schools(id) NOT NULL,
    created_by UUID REFERENCES users(id) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    subject_id UUID REFERENCES subjects(id),
    class_ids UUID[] DEFAULT '{}',
    duration_minutes INTEGER NOT NULL,
    total_marks INTEGER NOT NULL,
    passing_marks INTEGER,
    instructions TEXT,
    question_selection_mode VARCHAR(50) DEFAULT 'manual' CHECK (question_selection_mode IN ('manual', 'random', 'mixed')),
    shuffle_questions BOOLEAN DEFAULT false,
    shuffle_options BOOLEAN DEFAULT false,
    show_results_immediately BOOLEAN DEFAULT false,
    allow_review BOOLEAN DEFAULT true,
    max_attempts INTEGER DEFAULT 1,
    show_answers_after_test BOOLEAN DEFAULT false,
    negative_marking BOOLEAN DEFAULT false,
    negative_marking_value DECIMAL(5,2) DEFAULT 0.25,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'scheduled', 'completed', 'archived')),
    is_template BOOLEAN DEFAULT false,
    template_id UUID REFERENCES tests(id),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX idx_tests_school_id ON tests(school_id);
CREATE INDEX idx_tests_created_by ON tests(created_by);
CREATE INDEX idx_tests_status ON tests(status);
CREATE INDEX idx_tests_start_time ON tests(start_time);
CREATE INDEX idx_tests_class_ids ON tests USING GIN(class_ids);

-- Test Questions Mapping
CREATE TABLE test_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id UUID REFERENCES tests(id) NOT NULL,
    question_id UUID NOT NULL,
    question_order INTEGER NOT NULL,
    marks DECIMAL(5,2) NOT NULL,
    is_mandatory BOOLEAN DEFAULT true,
    section_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_test_questions_test_id ON test_questions(test_id);
CREATE INDEX idx_test_questions_question_id ON test_questions(question_id);

-- Test Schedules
CREATE TABLE test_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id UUID REFERENCES tests(id) NOT NULL,
    class_id UUID REFERENCES classes(id) NOT NULL,
    scheduled_start_time TIMESTAMP NOT NULL,
    scheduled_end_time TIMESTAMP NOT NULL,
    status VARCHAR(50) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'in_progress', 'completed', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_test_schedules_test_id ON test_schedules(test_id);
CREATE INDEX idx_test_schedules_class_id ON test_schedules(class_id);

-- Test Attempts
CREATE TABLE test_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id UUID REFERENCES tests(id) NOT NULL,
    student_id UUID REFERENCES users(id) NOT NULL,
    schedule_id UUID REFERENCES test_schedules(id),
    attempt_number INTEGER DEFAULT 1,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    duration_used_seconds INTEGER,
    status VARCHAR(50) DEFAULT 'in_progress' CHECK (status IN ('not_started', 'in_progress', 'submitted', 'auto_submitted', 'abandoned', 'graded')),
    ip_address INET,
    browser_info TEXT,
    device_info TEXT,
    is_flagged BOOLEAN DEFAULT false,
    flag_reason TEXT,
    total_score DECIMAL(10,2),
    percentage DECIMAL(5,2),
    passed BOOLEAN,
    answers JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_test_attempts_test_id ON test_attempts(test_id);
CREATE INDEX idx_test_attempts_student_id ON test_attempts(student_id);
CREATE INDEX idx_test_attempts_status ON test_attempts(status);
CREATE INDEX idx_test_attempts_start_time ON test_attempts(start_time);

-- Student Answers
CREATE TABLE student_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id UUID REFERENCES test_attempts(id) NOT NULL,
    question_id UUID NOT NULL,
    answer TEXT,
    selected_options UUID[],
    answer_file_url VARCHAR(500),
    is_correct BOOLEAN,
    marks_obtained DECIMAL(5,2),
    marks_allocated DECIMAL(5,2),
    graded_by UUID REFERENCES users(id),
    graded_at TIMESTAMP,
    feedback TEXT,
    time_spent_seconds INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_student_answers_attempt_id ON student_answers(attempt_id);
CREATE INDEX idx_student_answers_question_id ON student_answers(question_id);

-- Grading Queue
CREATE TABLE grading_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id UUID REFERENCES test_attempts(id) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    priority INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_grading_queue_status ON grading_queue(status);
CREATE INDEX idx_grading_queue_priority ON grading_queue(priority);

-- Analytics/Performance Data
CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID REFERENCES schools(id),
    test_id UUID REFERENCES tests(id),
    class_id UUID REFERENCES classes(id),
    subject_id UUID REFERENCES subjects(id),
    student_id UUID REFERENCES users(id),
    teacher_id UUID REFERENCES users(id),
    metric_type VARCHAR(50) NOT NULL,
    metric_value DECIMAL(10,2),
    additional_data JSONB,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_performance_metrics_school_id ON performance_metrics(school_id);
CREATE INDEX idx_performance_metrics_test_id ON performance_metrics(test_id);
CREATE INDEX idx_performance_metrics_student_id ON performance_metrics(student_id);
CREATE INDEX idx_performance_metrics_recorded_at ON performance_metrics(recorded_at);

-- Notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    data JSONB DEFAULT '{}',
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);

-- Audit Logs
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    school_id UUID REFERENCES schools(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_school_id ON audit_logs(school_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- Settings
CREATE TABLE system_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Books
CREATE TABLE books (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID REFERENCES schools(id) NOT NULL,
    uploaded_by UUID REFERENCES users(id) NOT NULL,
    title VARCHAR(500) NOT NULL,
    author VARCHAR(255),
    publisher VARCHAR(255),
    isbn VARCHAR(50),
    edition VARCHAR(50),
    year INTEGER,
    class_id UUID REFERENCES classes(id),
    subject_id UUID REFERENCES subjects(id),
    file_url VARCHAR(500) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT,
    page_count INTEGER,
    language VARCHAR(50) DEFAULT 'english',
    description TEXT,
    tags TEXT[],
    is_public BOOLEAN DEFAULT false,
    processing_status VARCHAR(50) DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    processing_progress INTEGER DEFAULT 0,
    questions_extracted INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX idx_books_school_id ON books(school_id);
CREATE INDEX idx_books_class_id ON books(class_id);
CREATE INDEX idx_books_subject_id ON books(subject_id);
CREATE INDEX idx_books_processing_status ON books(processing_status);
CREATE INDEX idx_books_tags ON books USING GIN(tags);

-- Question Papers
CREATE TABLE question_papers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID REFERENCES schools(id) NOT NULL,
    uploaded_by UUID REFERENCES users(id) NOT NULL,
    title VARCHAR(500) NOT NULL,
    exam_name VARCHAR(255),
    exam_board VARCHAR(255),
    year INTEGER NOT NULL,
    semester VARCHAR(50),
    class_id UUID REFERENCES classes(id),
    subject_id UUID REFERENCES subjects(id),
    file_url VARCHAR(500) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT,
    page_count INTEGER,
    total_marks INTEGER,
    duration_minutes INTEGER,
    description TEXT,
    tags TEXT[],
    is_public BOOLEAN DEFAULT false,
    processing_status VARCHAR(50) DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    processing_progress INTEGER DEFAULT 0,
    questions_extracted INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX idx_question_papers_school_id ON question_papers(school_id);
CREATE INDEX idx_question_papers_class_id ON question_papers(class_id);
CREATE INDEX idx_question_papers_subject_id ON question_papers(subject_id);
CREATE INDEX idx_question_papers_year ON question_papers(year);
CREATE INDEX idx_question_papers_processing_status ON question_papers(processing_status);
CREATE INDEX idx_question_papers_tags ON question_papers USING GIN(tags);

-- Resource Chapters/Sections
CREATE TABLE resource_chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(50) NOT NULL CHECK (resource_type IN ('book', 'question_paper')),
    resource_id UUID NOT NULL,
    chapter_number INTEGER,
    chapter_title VARCHAR(500),
    page_start INTEGER,
    page_end INTEGER,
    topics TEXT[],
    questions_extracted INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_resource_chapters_resource ON resource_chapters(resource_type, resource_id);

-- Extracted Questions Tracking
CREATE TABLE extracted_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(50) NOT NULL CHECK (resource_type IN ('book', 'question_paper')),
    resource_id UUID NOT NULL,
    chapter_id UUID REFERENCES resource_chapters(id),
    question_id UUID NOT NULL,
  
    page_number INTEGER,
  
    extraction_confidence DECIMAL(3,2),
    extraction_method VARCHAR(50),
  
    is_verified BOOLEAN DEFAULT false,
    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMP,
    notes TEXT,
  
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_extracted_questions_resource ON extracted_questions(resource_type, resource_id);
CREATE INDEX idx_extracted_questions_question_id ON extracted_questions(question_id);
CREATE INDEX idx_extracted_questions_is_verified ON extracted_questions(is_verified);

-- Document Processing Jobs
CREATE TABLE document_processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type VARCHAR(50) NOT NULL CHECK (resource_type IN ('book', 'question_paper')),
    resource_id UUID NOT NULL,
  
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    priority INTEGER DEFAULT 0,
  
    progress INTEGER DEFAULT 0,
    current_step VARCHAR(255),
  
    error_message TEXT,
  
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
  
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_document_processing_jobs_resource ON document_processing_jobs(resource_type, resource_id);
CREATE INDEX idx_document_processing_jobs_status ON document_processing_jobs(status);
CREATE INDEX idx_document_processing_jobs_priority ON document_processing_jobs(priority);
```

### PostgreSQL Schema - Question Bank & Content

```sql
-- Questions Table (Schema-based design for all question types)
CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID REFERENCES schools(id) NOT NULL,
    created_by UUID REFERENCES users(id) NOT NULL,
    question_type VARCHAR(50) NOT NULL CHECK (question_type IN ('mcq', 'true_false', 'fill_blank', 'descriptive', 'coding', 'matching', 'drag_drop', 'hotspot')),
    
    -- Core question content
    question_text TEXT NOT NULL,
    question_media JSONB DEFAULT '[]', -- Array of media objects
    explanation TEXT,
    
    -- Question-specific data (JSONB for flexibility)
    question_data JSONB NOT NULL DEFAULT '{}', -- Structure varies by type
    
    -- Metadata
    difficulty VARCHAR(20) DEFAULT 'medium' CHECK (difficulty IN ('easy', 'medium', 'hard')),
    marks DECIMAL(5,2) NOT NULL DEFAULT 1.0,
    negative_marks DECIMAL(5,2) DEFAULT 0.0,
    time_limit_seconds INTEGER,
    
    -- Classification
    subject_id UUID REFERENCES subjects(id),
    topics TEXT[] DEFAULT '{}',
    chapter VARCHAR(255),
    tags TEXT[] DEFAULT '{}',
    language VARCHAR(10) DEFAULT 'en',
    
    -- Source tracking
    source_type VARCHAR(50) CHECK (source_type IN ('manual', 'book', 'question_paper', 'ai_generated', 'import')),
    source_resource_id UUID,
    source_resource_type VARCHAR(50),
    source_chapter_id UUID,
    source_page_number INTEGER,
    extraction_confidence DECIMAL(3,2), -- 0.00 to 1.00
    
    -- Versioning and relationships
    version INTEGER DEFAULT 1,
    parent_question_id UUID REFERENCES questions(id),
    
    -- Performance tracking
    usage_count INTEGER DEFAULT 0,
    average_score DECIMAL(5,2),
    average_time_seconds INTEGER,
    
    -- Access control
    is_public BOOLEAN DEFAULT false,
    is_verified BOOLEAN DEFAULT false,
    verified_by UUID REFERENCES users(id),
    verified_at TIMESTAMP,
    
    -- Advanced settings
    metadata JSONB DEFAULT '{}', -- Time limits, rubrics, etc.
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Question Options Table (for MCQ and similar types)
CREATE TABLE question_options (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
    option_text TEXT NOT NULL,
    option_media JSONB DEFAULT '{}',
    is_correct BOOLEAN DEFAULT false,
    option_order INTEGER NOT NULL,
    explanation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Question Answers Table (for descriptive and coding questions)
CREATE TABLE question_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
    answer_text TEXT,
    answer_data JSONB, -- For complex answers (code, formulas, etc.)
    is_sample_answer BOOLEAN DEFAULT false,
    explanation TEXT,
    marks_allocated DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Question Rubrics Table (for subjective questions)
CREATE TABLE question_rubrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
    criteria_name VARCHAR(255) NOT NULL,
    criteria_description TEXT,
    max_marks DECIMAL(5,2) NOT NULL,
    weight_percentage DECIMAL(5,2) DEFAULT 1.0,
    rubric_levels JSONB NOT NULL, -- Array of rubric levels with descriptions and marks
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Question Usage Analytics
CREATE TABLE question_usage_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
    test_id UUID REFERENCES tests(id),
    usage_date DATE DEFAULT CURRENT_DATE,
    attempts_count INTEGER DEFAULT 0,
    correct_attempts INTEGER DEFAULT 0,
    average_score DECIMAL(5,2),
    average_time_seconds INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Question Tags Table (for better tag management)
CREATE TABLE question_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tag_name VARCHAR(100) NOT NULL,
    tag_category VARCHAR(50), -- 'topic', 'difficulty', 'skill', etc.
    school_id UUID REFERENCES schools(id),
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(school_id, tag_name)
);

-- Question-Tag Junction Table
CREATE TABLE question_tag_mappings (
    question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES question_tags(id) ON DELETE CASCADE,
    added_by UUID REFERENCES users(id),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (question_id, tag_id)
);

-- Question Media Files Table
CREATE TABLE question_media_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID REFERENCES questions(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_url VARCHAR(500) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT,
    mime_type VARCHAR(100),
    alt_text TEXT,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Comprehensive Indexes for Performance
CREATE INDEX idx_questions_school_id ON questions(school_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_questions_subject_id ON questions(subject_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_questions_type_difficulty ON questions(question_type, difficulty) WHERE deleted_at IS NULL;
CREATE INDEX idx_questions_topics ON questions USING GIN(topics) WHERE deleted_at IS NULL;
CREATE INDEX idx_questions_tags ON questions USING GIN(tags) WHERE deleted_at IS NULL;
CREATE INDEX idx_questions_created_by ON questions(created_by) WHERE deleted_at IS NULL;
CREATE INDEX idx_questions_source ON questions(source_type, source_resource_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_questions_text_search ON questions USING GIN(to_tsvector('english', question_text)) WHERE deleted_at IS NULL;
CREATE INDEX idx_questions_full_text ON questions USING GIN(to_tsvector('english', question_text || ' ' || COALESCE(explanation, ''))) WHERE deleted_at IS NULL;

-- Composite indexes for common queries
CREATE INDEX idx_questions_composite ON questions(school_id, subject_id, question_type, difficulty) WHERE deleted_at IS NULL;
CREATE INDEX idx_questions_usage ON questions(usage_count DESC, average_score) WHERE deleted_at IS NULL;

-- JSONB indexes for flexible querying
CREATE INDEX idx_questions_data ON questions USING GIN(question_data);
CREATE INDEX idx_questions_metadata ON questions USING GIN(metadata);

-- Indexes for related tables
CREATE INDEX idx_question_options_question_id ON question_options(question_id, option_order);
CREATE INDEX idx_question_answers_question_id ON question_answers(question_id);
CREATE INDEX idx_question_rubrics_question_id ON question_rubrics(question_id);
CREATE INDEX idx_question_usage_question_date ON question_usage_analytics(question_id, usage_date);
CREATE INDEX idx_question_tags_name ON question_tags(tag_name) WHERE school_id IS NULL; -- Global tags
CREATE INDEX idx_question_tags_school ON question_tags(school_id, tag_name);

-- Full-text search configuration
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Trigram index for partial text matching
CREATE INDEX idx_questions_text_trgm ON questions USING GIN(question_text gin_trgm_ops) WHERE deleted_at IS NULL;

-- Partitioned table for question analytics (by date)
CREATE TABLE question_usage_analytics_partitioned (
    LIKE question_usage_analytics INCLUDING ALL
) PARTITION BY RANGE (usage_date);

-- Create monthly partitions
SELECT create_monthly_partitions('question_usage_analytics_partitioned', '2024-01-01', '2026-12-31');

-- Views for common queries
CREATE VIEW active_questions AS
SELECT q.*, 
       array_agg(o.option_text ORDER BY o.option_order) as options,
       COUNT(ua.attempts_count) as total_usage
FROM questions q
LEFT JOIN question_options o ON q.id = o.question_id
LEFT JOIN question_usage_analytics ua ON q.id = ua.question_id
WHERE q.deleted_at IS NULL
GROUP BY q.id;

CREATE VIEW question_search_view AS
SELECT 
    q.id,
    q.question_text,
    q.explanation,
    q.question_type,
    q.difficulty,
    q.subject_id,
    s.name as subject_name,
    q.topics,
    q.tags,
    q.usage_count,
    q.average_score,
    ts_rank_cd(
        to_tsvector('english', q.question_text || ' ' || COALESCE(q.explanation, '')),
        plainto_tsquery('english', COALESCE(:search_term, ''))
    ) as search_rank
FROM questions q
LEFT JOIN subjects s ON q.subject_id = s.id
WHERE q.deleted_at IS NULL
AND (
    to_tsvector('english', q.question_text || ' ' || COALESCE(q.explanation, '')) 
    @@ plainto_tsquery('english', COALESCE(:search_term, ''))
    OR :search_term IS NULL
);
```

### Smart, Scalable & Robust Database Architecture

#### **Multi-Layer Database Strategy**

##### **1. Smart Database Design**
- **Schema Validation**: Strict constraints, check constraints, triggers
- **Data Integrity**: Foreign keys with CASCADE options, unique constraints
- **Smart Indexing**: Composite indexes for common query patterns
- **Auto-Generated UUIDs**: Version 4 UUIDs for distributed systems
- **Soft Deletes**: Logical deletion with audit trails
- **Temporal Tables**: Automatic history tracking for critical data

##### **2. Advanced PostgreSQL Features**
```sql
-- Smart Constraints with Custom Error Messages
CREATE CONSTRAINT TRIGGER validate_test_configuration
AFTER INSERT OR UPDATE ON tests
FOR EACH ROW EXECUTE FUNCTION validate_test_config();

-- Generated Columns for Computed Values
ALTER TABLE tests ADD COLUMN estimated_time_minutes 
GENERATED ALWAYS AS (SELECT calculate_estimated_time(question_count, question_types)) STORED;

-- Partitioned Tables with Automatic Partition Management
CREATE TABLE test_attempts (
    LIKE test_attempts_template INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- Smart Indexes with Partial Indexing
CREATE INDEX idx_active_tests ON tests(school_id) WHERE deleted_at IS NULL AND status = 'published';
CREATE INDEX idx_recent_attempts ON test_attempts(student_id, created_at) 
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days';
```

##### **3. Comprehensive Scaling Strategy**

###### **Read Replicas Configuration**
- **Primary-Replica Setup**: 1 primary + 3 read replicas
- **Smart Routing**: Read queries automatically routed to nearest replica
- **Replica Types**:
  - **Analytics Replica**: Optimized for complex reporting queries
  - **Cache Replica**: In-memory optimized for frequent lookups
  - **Geo-Replica**: For low-latency access across regions
- **Failover Automation**: Automatic promotion of replica to primary
- **Replica Lag Monitoring**: Real-time lag alerts and automatic query routing

###### **Advanced Partitioning Strategy**
```sql
-- Time-based Partitioning with Automatic Management
CREATE TABLE test_attempts (
    id UUID,
    test_id UUID,
    student_id UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- other columns
) PARTITION BY RANGE (created_at);

-- Automatic Partition Creation
SELECT create_monthly_partitions('test_attempts', '2024-01-01', '2025-12-31');

-- Hash-based Partitioning for Load Distribution
CREATE TABLE questions (
    id UUID,
    school_id UUID,
    question_hash INTEGER DEFAULT (hashtext(id::text) % 16)
) PARTITION BY HASH (question_hash);
```

###### **Connection Pooling & Management**
- **PgBouncer Configuration**: Transaction-level pooling for high concurrency
- **Connection Limits**: Per-user and per-database connection limits
- **Health Checks**: Automatic connection validation and cleanup
- **Load Balancing**: Intelligent connection distribution

##### **4. High Availability & Disaster Recovery**

###### **Multi-Region Setup**
- **Primary Region**: Active database with real-time replication
- **Secondary Region**: Standby with synchronous replication
- **Tertiary Region**: Backup with asynchronous replication
- **Automatic Failover**: Zero-downtime failover with DNS switching

###### **Backup & Recovery Strategy**
```sql
-- Continuous Backup Pipeline
1. Real-time WAL archiving to S3
2. Hourly base backups compressed
3. Daily full backups with verification
4. Weekly cross-region backup replication
5. Monthly backup restoration testing

-- Point-in-Time Recovery (PITR)
-- Recovery to any second within 30 days
-- Recovery time objective (RTO): < 15 minutes
-- Recovery point objective (RPO): < 1 minute
```

##### **5. Performance Optimization**

###### **Query Optimization**
```sql
-- Smart Materialized Views
CREATE MATERIALIZED VIEW student_performance_summary AS
SELECT 
    student_id,
    AVG(percentage) as avg_score,
    COUNT(*) as total_attempts,
    MAX(created_at) as last_attempt
FROM test_attempts 
GROUP BY student_id
WITH DATA;

-- Auto-Refresh Strategy
CREATE OR REPLACE FUNCTION refresh_performance_summary()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY student_performance_summary;
END;
$$ LANGUAGE plpgsql;

-- Scheduled Refresh
SELECT cron.schedule('refresh-performance', '0 */6 * * *', 'SELECT refresh_performance_summary();');
```

###### **Caching Strategy**
- **Redis Clusters**: Multi-node Redis for session and query caching
- **Application-Level Caching**: Intelligent cache invalidation
- **Database Query Caching**: Automatic result caching for repeated queries
- **CDN Integration**: Static assets and API response caching

##### **6. Monitoring & Observability**

###### **Database Health Monitoring**
```sql
-- Comprehensive Monitoring Setup
1. Connection pool metrics
2. Query performance analysis
3. Index usage statistics
4. Lock contention monitoring
5. Disk space and I/O metrics
6. Replication lag tracking
7. Backup verification status

-- Alert Thresholds
- CPU usage > 80% for 5 minutes
- Memory usage > 85%
- Disk space < 20%
- Replication lag > 10 seconds
- Query duration > 5 seconds
```

##### **7. Security & Compliance**

###### **Data Security**
```sql
-- Row-Level Security for Multi-Tenant Isolation
ALTER TABLE tests ENABLE ROW LEVEL SECURITY;
CREATE POLICY school_isolation ON tests
FOR ALL TO application_role
USING (school_id = current_setting('app.current_school_id')::uuid);

-- Column-Level Encryption
CREATE EXTENSION IF NOT EXISTS pgcrypto;
ALTER TABLE users ADD COLUMN encrypted_email TEXT;
UPDATE users SET encrypted_email = pgp_sym_encrypt(email, current_setting('app.encryption_key'));

-- Audit Logging
CREATE OR REPLACE FUNCTION audit_trigger()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_logs (table_name, operation, old_values, new_values, user_id)
    VALUES (TG_TABLE_NAME, TG_OP, row_to_json(OLD), row_to_json(NEW), current_setting('app.current_user_id')::uuid);
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;
```

##### **8. Smart Error Handling & Recovery**

###### **Automatic Error Recovery**
```sql
-- Deadlock Detection and Resolution
CREATE OR REPLACE FUNCTION handle_deadlock()
RETURNS void AS $$
BEGIN
    -- Log deadlock details
    -- Retry transaction with exponential backoff
    -- Notify monitoring system
END;
$$ LANGUAGE plpgsql;

-- Data Consistency Checks
CREATE OR REPLACE FUNCTION validate_data_integrity()
RETURNS TABLE(table_name TEXT, issue_count BIGINT) AS $$
BEGIN
    -- Check for orphaned records
    -- Validate foreign key relationships
    -- Verify data constraints
    -- Report inconsistencies
END;
$$ LANGUAGE plpgsql;
```

##### **9. Database Migration Strategy**

###### **Zero-Downtime Migrations**
```sql
-- Blue-Green Deployment for Schema Changes
1. Create new schema version
2. Sync data to new schema
3. Validate data consistency
4. Switch application to new schema
5. Keep old schema for rollback

-- Backward-Compatible Changes
- Add new columns as nullable
- Use views for API compatibility
- Gradual data migration
- Feature flags for new functionality
```

##### **10. PostgreSQL Schema Optimization**

###### **Smart Schema Design**
```sql
-- Optimized Question Storage with JSONB
CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL,
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) NOT NULL,
    
    -- JSONB for flexible data storage
    question_data JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    
    -- Embedded frequently accessed data
    subject_name VARCHAR(255) GENERATED ALWAYS AS (
        SELECT name FROM subjects WHERE id = questions.subject_id
    ) STORED,
    
    -- Performance tracking
    usage_stats JSONB DEFAULT '{
        "times_used": 0,
        "avg_score": 0.0,
        "last_used": null
    }'::jsonb,
    
    -- Search optimization
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', question_text), 'A') ||
        setweight(to_tsvector('english', COALESCE(explanation, '')), 'B') ||
        setweight(to_tsvector('english', array_to_string(topics, ' ')), 'C')
    ) STORED,
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Compound Indexes for Performance
CREATE INDEX idx_questions_performance ON questions(
    school_id, 
    subject_id, 
    question_type, 
    (usage_stats->>'times_used')::INTEGER DESC
) WHERE deleted_at IS NULL;

-- JSONB-specific indexes
CREATE INDEX idx_questions_data_gin ON questions USING GIN(question_data);
CREATE INDEX idx_questions_usage_stats ON questions USING GIN(usage_stats);

-- Full-text search index
CREATE INDEX idx_questions_search ON questions USING GIN(search_vector);

-- Partial index for frequently accessed active questions
CREATE INDEX idx_questions_active ON questions(
    school_id, subject_id, question_type
) WHERE deleted_at IS NULL AND is_verified = true;
```

##### **11. Resilience Testing**

###### **Chaos Engineering**
- **Database Failover Tests**: Automatic failover validation
- **Network Partition Tests**: Split-brain scenario testing
- **Load Testing**: Simulated 10,000+ concurrent users
- **Data Corruption Tests**: Automatic corruption detection and recovery
- **Performance Degradation**: Graceful degradation under load

This comprehensive database architecture ensures:
- **Smart Design**: Intelligent constraints, validation, and optimization
- **Scalability**: Horizontal and vertical scaling capabilities
- **Robustness**: High availability, disaster recovery, and error resilience
- **Performance**: Optimized queries, caching, and monitoring
- **Security**: Multi-layer security and compliance features

---

## Database Crash Prevention & Zero-Downtime Architecture

### **Overview**

Implementing a bulletproof database architecture that ensures the system never crashes and maintains 99.99% uptime through comprehensive prevention, monitoring, and automatic recovery mechanisms.

### **1. Proactive Crash Prevention Strategies**

#### **Database Resource Management**
```sql
-- Connection Pool Configuration
ALTER SYSTEM SET max_connections = 500;
ALTER SYSTEM SET superuser_reserved_connections = 10;
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET work_mem = '256MB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';

-- Automatic Memory Management
ALTER SYSTEM SET autovacuum = on;
ALTER SYSTEM SET autovacuum_max_workers = 4;
ALTER SYSTEM SET autovacuum_naptime = '1min';
ALTER SYSTEM SET autovacuum_vacuum_scale_factor = 0.1;
ALTER SYSTEM SET autovacuum_analyze_scale_factor = 0.05;

-- Prevent Connection Exhaustion
ALTER SYSTEM SET idle_in_transaction_session_timeout = '5min';
ALTER SYSTEM SET statement_timeout = '30min';
ALTER SYSTEM SET lock_timeout = '10s';
```

#### **Query Performance Protection**
```sql
-- Slow Query Detection
CREATE OR REPLACE FUNCTION log_slow_queries()
RETURNS event_trigger AS $$
BEGIN
    IF pg_stat_statements.calls > 100 AND pg_stat_statements.mean_exec_time > 5000 THEN
        INSERT INTO slow_query_log (query, duration, user_id)
        VALUES (current_query(), pg_stat_statements.mean_exec_time, current_user);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Resource Usage Monitoring
CREATE OR REPLACE FUNCTION monitor_resource_usage()
RETURNS void AS $$
DECLARE
    cpu_usage FLOAT;
    memory_usage FLOAT;
    disk_usage FLOAT;
BEGIN
    -- Monitor system resources
    SELECT INTO cpu_usage, memory_usage, disk_usage 
    get_system_metrics();
    
    -- Auto-throttle if resources are high
    IF cpu_usage > 85 OR memory_usage > 90 OR disk_usage > 85 THEN
        PERFORM pg_reload_conf();
        -- Enable emergency mode
        PERFORM enable_emergency_throttling();
    END IF;
END;
$$ LANGUAGE plpgsql;
```

### **2. Real-Time Monitoring & Alerting System**

#### **Comprehensive Health Monitoring**
```sql
-- Database Health Dashboard
CREATE MATERIALIZED VIEW database_health_metrics AS
SELECT 
    'connection_pool' as metric_type,
    (SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
    (SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'idle') as idle_connections,
    (SELECT COUNT(*) FROM pg_stat_activity WHERE wait_event IS NOT NULL) as waiting_connections,
    (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_connections,
    ROUND(
        (SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active')::float / 
        (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') * 100, 2
    ) as connection_utilization_percent

UNION ALL

SELECT 
    'memory_usage' as metric_type,
    (SELECT shared_buffers_size FROM pg_settings) as shared_buffers,
    (SELECT work_mem_size FROM pg_settings) as work_mem,
    (SELECT maintenance_work_mem_size FROM pg_settings) as maintenance_work_mem,
    (SELECT effective_cache_size FROM pg_settings) as effective_cache_size,
    (SELECT total_memory_usage FROM system_metrics) as memory_utilization_percent

UNION ALL

SELECT 
    'disk_io' as metric_type,
    (SELECT reads FROM pg_stat_database WHERE datname = current_database()) as disk_reads,
    (SELECT writes FROM pg_stat_database WHERE datname = current_database()) as disk_writes,
    (SELECT blks_read FROM pg_stat_database WHERE datname = current_database()) as blocks_read,
    (SELECT blks_hit FROM pg_stat_database WHERE datname = current_database()) as blocks_hit,
    ROUND(
        (SELECT blks_hit::float / (blks_read + blks_hit)) * 100, 2
    ) as cache_hit_ratio;

-- Refresh every 30 seconds
CREATE OR REPLACE FUNCTION refresh_health_metrics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY database_health_metrics;
END;
$$ LANGUAGE plpgsql;

-- Schedule health checks
SELECT cron.schedule('health-check', '*/30 * * * *', 'SELECT refresh_health_metrics();');
```

#### **Automated Alerting System**
```sql
-- Alert Threshold Configuration
CREATE TABLE alert_thresholds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(100) NOT NULL,
    warning_threshold DECIMAL(5,2),
    critical_threshold DECIMAL(5,2),
    action_type VARCHAR(50) CHECK (action_type IN ('log', 'email', 'sms', 'auto_action')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO alert_thresholds VALUES
(gen_random_uuid(), 'connection_utilization', 70.0, 85.0, 'auto_action', true),
(gen_random_uuid(), 'memory_utilization', 80.0, 90.0, 'auto_action', true),
(gen_random_uuid(), 'disk_usage', 75.0, 85.0, 'auto_action', true),
(gen_random_uuid(), 'replication_lag', 10.0, 30.0, 'auto_action', true),
(gen_random_uuid(), 'query_duration', 5000.0, 10000.0, 'log', true),
(gen_random_uuid(), 'cache_hit_ratio', 95.0, 90.0, 'auto_action', true);

-- Alert Processing Function
CREATE OR REPLACE FUNCTION process_alerts()
RETURNS void AS $$
DECLARE
    alert_record RECORD;
    action_required BOOLEAN;
BEGIN
    FOR alert_record IN 
        SELECT 
            h.metric_type,
            h.connection_utilization_percent as value,
            t.warning_threshold,
            t.critical_threshold,
            t.action_type
        FROM database_health_metrics h
        CROSS JOIN alert_thresholds t
        WHERE h.metric_type = t.metric_name 
        AND t.is_active = true
        AND (h.connection_utilization_percent >= t.warning_threshold OR 
             h.connection_utilization_percent >= t.critical_threshold)
    LOOP
        IF alert_record.value >= alert_record.critical_threshold THEN
            -- Critical alert - take immediate action
            PERFORM handle_critical_alert(alert_record.metric_type, alert_record.value);
            PERFORM log_critical_event(alert_record.metric_type, alert_record.value);
        ELSIF alert_record.value >= alert_record.warning_threshold THEN
            -- Warning alert - log and notify
            PERFORM log_warning_event(alert_record.metric_type, alert_record.value);
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
```

### **3. Automatic Failover & Recovery**

#### **Multi-Master Replication Setup**
```sql
-- Patroni Configuration for High Availability
-- Configuration file: patroni.yml
restapi:
  listen: 0.0.0.0:8008
  connect_address: 10.0.1.10:8008

etcd:
  hosts: 10.0.1.10:2379,10.0.1.11:2379,10.0.1.12:2379

bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 10
    maximum_lag_on_failover: 1048576
    postgresql:
      use_pg_rewind: true
      parameters:
        wal_level: hot_standby
        hot_standby: "on"
        max_connections: 500
        max_prepared_transactions: 500
        max_locks_per_transaction: 64
        wal_log_hints: "on"
        max_wal_senders: 5
        wal_keep_segments: 8
        hot_standby_feedback: "on"
        track_commit_timestamp: "on"
        archive_mode: "on"
        archive_command: "cp %p /var/lib/postgresql/wal_archive/%f"

  pg_hba:
  - host replication replicator 10.0.1.0/24 md5
  - host all all 0.0.0.0/0 md5

postgresql:
  listen: 0.0.0.0:5432
  connect_address: 10.0.1.10:5432
  data_dir: /var/lib/postgresql/data
  pgpass: /tmp/pgpass
  authentication:
    replication:
      username: replicator
      password: rep-pass
    superuser:
      username: postgres
      password: su-pass
  parameters:
    unix_socket_directories: /var/run/postgresql
```

#### **Automatic Failover Logic**
```python
# Failover Controller Implementation
class DatabaseFailoverController:
    def __init__(self):
        self.health_checker = DatabaseHealthChecker()
        self.replication_manager = ReplicationManager()
        self.alert_system = AlertSystem()
        
    def monitor_and_failover(self):
        while True:
            try:
                health_status = self.health_checker.check_primary_health()
                
                if not health_status.is_healthy:
                    self.initiate_failover(health_status)
                    
                self.check_replication_lag()
                time.sleep(5)
                
            except Exception as e:
                self.alert_system.send_critical_alert(f"Failover controller error: {str(e)}")
                time.sleep(10)
    
    def initiate_failover(self, health_status):
        # Check if failover is needed
        if health_status.failure_type == 'primary_crash':
            # Promote most up-to-date replica
            best_replica = self.replication_manager.get_best_replica()
            
            if best_replica.lag < self.max_acceptable_lag:
                self.replication_manager.promote_replica(best_replica)
                self.alert_system.send_failover_notification(best_replica)
            else:
                self.alert_system.send_critical_alert("No suitable replica for failover")
                
        elif health_status.failure_type == 'network_partition':
            # Handle network split-brain
            self.handle_network_partition(health_status)
    
    def handle_network_partition(self, health_status):
        # Implement consensus-based recovery
        consensus = self.achieve_consensus()
        if consensus.majority_agrees:
            self.promote_consensus_leader(consensus.leader)
        else:
            self.enter_safe_mode()
```

### **4. Backup & Disaster Recovery**

#### **Continuous Backup Strategy**
```sql
-- WAL Archiving Configuration
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET archive_mode = on;
ALTER SYSTEM SET archive_command = '/usr/local/bin/wal-g wal-push %p';
ALTER SYSTEM SET archive_timeout = '60s';

-- Automated Backup Script
#!/bin/bash
# backup_database.sh

set -euo pipefail

# Configuration
BACKUP_DIR="/backups/postgresql"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/assessment_engine_$TIMESTAMP.dump"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Perform base backup
pg_basebackup -h localhost -D "$BACKUP_DIR/base_$TIMESTAMP" -U postgres -v -P -W

# Create compressed dump
pg_dump -h localhost -U postgres -Fc assessment_engine > "$BACKUP_FILE"

# Upload to cloud storage
aws s3 cp "$BACKUP_FILE" s3://assessment-engine-backups/database/
aws s3 cp "$BACKUP_DIR/base_$TIMESTAMP" s3://assessment-engine-backups/base-backups/

# Clean up old backups
find "$BACKUP_DIR" -name "*.dump" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "base_*" -mtime +$RETENTION_DAYS -delete

# Verify backup integrity
pg_restore --list "$BACKUP_FILE" > /dev/null
if [ $? -eq 0 ]; then
    echo "Backup verification successful: $BACKUP_FILE"
else
    echo "Backup verification failed: $BACKUP_FILE"
    exit 1
fi

# Log backup completion
echo "$(date): Database backup completed successfully: $BACKUP_FILE" >> /var/log/postgresql/backups.log
```

#### **Point-in-Time Recovery (PITR)**
```sql
-- Recovery Configuration
CREATE TABLE recovery_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recovery_name VARCHAR(255) NOT NULL,
    recovery_timestamp TIMESTAMP NOT NULL,
    wal_file_name VARCHAR(255),
    backup_file_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Automated Recovery Function
CREATE OR REPLACE FUNCTION initiate_pitr_recovery(recovery_name TEXT, target_time TIMESTAMP)
RETURNS TEXT AS $$
DECLARE
    recovery_point RECORD;
    wal_file TEXT;
    backup_file TEXT;
BEGIN
    -- Find appropriate recovery point
    SELECT INTO recovery_point 
    recovery_timestamp, wal_file_name, backup_file_path
    FROM recovery_points 
    WHERE recovery_name = recovery_name 
    AND recovery_timestamp <= target_time 
    ORDER BY recovery_timestamp DESC 
    LIMIT 1;
    
    -- Initiate recovery process
    PERFORM pg_start_backup('recovery_' || recovery_name);
    
    -- Restore from backup
    PERFORM restore_from_backup(recovery_point.backup_file_path);
    
    -- Apply WAL files up to target time
    PERFORM apply_wal_files(recovery_point.wal_file_name, target_time);
    
    -- Verify recovery
    PERFORM verify_recovery_integrity();
    
    RETURN format('Recovery completed: %s to %s', recovery_name, target_time);
END;
$$ LANGUAGE plpgsql;
```

### **5. Performance Optimization & Load Management**

#### **Query Optimization**
```sql
-- Automatic Query Optimization
CREATE OR REPLACE FUNCTION optimize_slow_queries()
RETURNS void AS $$
DECLARE
    slow_query RECORD;
BEGIN
    FOR slow_query IN 
        SELECT query, calls, total_exec_time, mean_exec_time
        FROM pg_stat_statements 
        WHERE mean_exec_time > 1000 
        ORDER BY mean_exec_time DESC 
        LIMIT 10
    LOOP
        -- Analyze query plan
        PERFORM analyze_query_plan(slow_query.query);
        
        -- Suggest indexes
        PERFORM suggest_missing_indexes(slow_query.query);
        
        -- Log for manual review
        INSERT INTO query_optimization_log 
        (query, execution_time, optimization_date, status)
        VALUES (slow_query.query, slow_query.mean_exec_time, NOW(), 'identified');
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Dynamic Connection Pool Adjustment
CREATE OR REPLACE FUNCTION adjust_connection_pool()
RETURNS void AS $$
DECLARE
    current_load FLOAT;
    optimal_connections INTEGER;
BEGIN
    -- Calculate current load
    SELECT INTO current_load 
    (SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active')::float / 
    (SELECT setting::int FROM pg_settings WHERE name = 'max_connections');
    
    -- Adjust pool size based on load
    IF current_load > 0.8 THEN
        -- High load - increase pool size
        optimal_connections := LEAST(600, current_setting('max_connections')::int + 100);
        PERFORM set_config('max_connections', optimal_connections::text, false);
        
    ELSIF current_load < 0.3 THEN
        -- Low load - decrease pool size
        optimal_connections := GREATEST(200, current_setting('max_connections')::int - 50);
        PERFORM set_config('max_connections', optimal_connections::text, false);
    END IF;
    
    -- Log adjustment
    INSERT INTO pool_adjustment_log (load_percentage, new_connections, adjustment_time)
    VALUES (current_load * 100, optimal_connections, NOW());
END;
$$ LANGUAGE plpgsql;
```

### **6. Security & Compliance**

#### **Data Protection**
```sql
-- Transparent Data Encryption (TDE)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Column-Level Encryption
CREATE OR REPLACE FUNCTION encrypt_sensitive_data(data TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_encrypt(data, current_setting('app.encryption_key'));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Row-Level Security Enhancement
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;
CREATE POLICY enhanced_school_isolation ON questions
FOR ALL TO application_role
USING (
    school_id = current_setting('app.current_school_id')::uuid AND
    deleted_at IS NULL
);

-- Audit Trail Enhancement
CREATE OR REPLACE FUNCTION enhanced_audit_trigger()
RETURNS TRIGGER AS $$
DECLARE
    audit_data JSONB;
BEGIN
    audit_data := jsonb_build_object(
        'table_name', TG_TABLE_NAME,
        'operation', TG_OP,
        'old_values', row_to_json(OLD),
        'new_values', row_to_json(NEW),
        'user_id', current_setting('app.current_user_id')::uuid,
        'session_id', current_setting('app.session_id'),
        'ip_address', inet_client_addr(),
        'user_agent', current_setting('app.user_agent'),
        'timestamp', NOW(),
        'transaction_id', txid_current()
    );
    
    INSERT INTO enhanced_audit_logs (audit_data) VALUES (audit_data);
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;
```

### **7. Testing & Validation**

#### **Chaos Engineering**
```python
# Chaos Testing Framework
class DatabaseChaosTester:
    def __init__(self):
        self.test_scenarios = [
            'primary_crash',
            'network_partition',
            'disk_full',
            'memory_exhaustion',
            'connection_exhaustion',
            'replication_lag',
            'corruption_detection'
        ]
    
    def run_chaos_tests(self):
        for scenario in self.test_scenarios:
            try:
                self.execute_chaos_scenario(scenario)
                self.validate_recovery(scenario)
            except Exception as e:
                self.log_chaos_failure(scenario, str(e))
    
    def execute_chaos_scenario(self, scenario):
        if scenario == 'primary_crash':
            self.simulate_primary_crash()
        elif scenario == 'network_partition':
            self.simulate_network_partition()
        elif scenario == 'disk_full':
            self.simulate_disk_full()
        # ... other scenarios
    
    def validate_recovery(self, scenario):
        # Verify system recovered correctly
        health_check = self.perform_health_check()
        if not health_check.is_healthy:
            raise Exception(f"Recovery validation failed for {scenario}")
```

### **8. 24/7 Monitoring Dashboard**

#### **Real-Time Health Dashboard**
```sql
-- Dashboard Metrics View
CREATE MATERIALIZED VIEW system_dashboard AS
SELECT 
    'system_health' as category,
    (SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
    (SELECT ROUND(100.0 * (blks_hit::float / (blks_read + blks_hit)), 2) 
     FROM pg_stat_database WHERE datname = current_database()) as cache_hit_ratio,
    (SELECT ROUND(100.0 * (xact_commit::float / (xact_commit + xact_rollback)), 2)
     FROM pg_stat_database WHERE datname = current_database()) as transaction_success_rate,
    (SELECT pg_size_pretty(pg_database_size(current_database()))) as database_size,
    (SELECT pg_size_pretty(sum(pg_relation_size(schemaname||'.'||tablename)))
     FROM pg_tables WHERE schemaname = 'public') as tables_size,
    (SELECT pg_size_pretty(sum(pg_relation_size(schemaname||'.'||indexname)))
     FROM pg_indexes WHERE schemaname = 'public') as indexes_size,
    (SELECT age(datfrozenxid) FROM pg_database WHERE datname = current_database()) as transaction_id_age,
    (SELECT max_failures FROM replication_status WHERE status = 'active') as replication_failures;

-- Auto-refresh dashboard
SELECT cron.schedule('dashboard-refresh', '*/10 * * * *', 'REFRESH MATERIALIZED VIEW system_dashboard;');
```

### **9. Emergency Response Procedures**

#### **Automated Emergency Response**
```sql
-- Emergency Response Triggers
CREATE OR REPLACE FUNCTION emergency_response()
RETURNS TRIGGER AS $$
BEGIN
    -- If critical threshold exceeded
    IF NEW.connection_utilization > 95 THEN
        -- Enable emergency mode
        PERFORM enable_emergency_mode();
        
        -- Scale up resources
        PERFORM trigger_auto_scaling();
        
        -- Notify all administrators
        PERFORM send_emergency_notification('critical_connection_load');
        
    ELSIF NEW.memory_utilization > 95 THEN
        -- Clear caches
        PERFORM clear_system_caches();
        
        -- Restart connections
        PERFORM restart_idle_connections();
        
    ELSIF NEW.replication_lag > 60 THEN
        -- Pause writes to allow catch-up
        PERFORM pause_write_operations();
        
        -- Check replica health
        PERFORM validate_replica_health();
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create emergency response trigger
CREATE TRIGGER emergency_response_trigger
AFTER UPDATE ON database_health_metrics
FOR EACH ROW
WHEN (NEW.connection_utilization > 95 OR NEW.memory_utilization > 95 OR NEW.replication_lag > 60)
EXECUTE FUNCTION emergency_response();
```

### **10. Zero-Downtime Deployment**

#### **Blue-Green Deployment**
```python
# Zero-Downtime Deployment Script
class ZeroDowntimeDeployer:
    def __init__(self):
        self.blue_environment = 'blue'
        self.green_environment = 'green'
        self.current_environment = self.blue_environment
        
    def deploy_schema_changes(self, migration_script):
        # Deploy to inactive environment
        inactive_env = self.get_inactive_environment()
        
        # Apply migrations to inactive environment
        self.apply_migrations(inactive_env, migration_script)
        
        # Validate migrations
        self.validate_migrations(inactive_env)
        
        # Switch traffic to new environment
        self.switch_traffic(inactive_env)
        
        # Monitor for issues
        self.monitor_post_deployment()
        
        # Keep old environment for rollback
        self.maintain_rollback_capability()
    
    def switch_traffic(self, target_environment):
        # Update load balancer configuration
        self.update_load_balancer(target_environment)
        
        # Update DNS if needed
        self.update_dns_records(target_environment)
        
        # Verify traffic routing
        self.verify_traffic_routing(target_environment)
```

### **Summary of Crash Prevention Measures**

✅ **Proactive Prevention**: Resource management, query optimization, connection pooling
✅ **Real-Time Monitoring**: Health metrics, alerting, automated responses
✅ **Automatic Failover**: Multi-master replication, consensus-based recovery
✅ **Backup & Recovery**: Continuous backups, PITR, automated restoration
✅ **Performance Optimization**: Dynamic scaling, query optimization, caching
✅ **Security**: Encryption, audit trails, access control
✅ **Testing**: Chaos engineering, recovery validation
✅ **Emergency Response**: Automated responses, escalation procedures
✅ **Zero-Downtime Deployment**: Blue-green deployment, traffic switching

This comprehensive crash prevention strategy ensures the database remains operational 24/7 with automatic recovery from any failure scenario, maintaining the assessment engine's reliability and availability.

## Resource Management & Question Extraction

### Overview

The Resource Management system enables schools to upload books (class-wise and subject-wise) and previous year question papers. The system uses AI/ML to automatically extract questions from these resources, making them available in the question bank for teachers to use when generating tests.

### User Roles & Permissions for Resource Upload

#### **Role-Based Access Control Matrix**

| Role | Upload Books | Upload Question Papers | View Resources | Edit Resources | Delete Resources | Share Resources | Extract Questions |
|------|--------------|----------------------|---------------|---------------|-----------------|---------------|------------------|
| **School Admin** | ✅ Full Access | ✅ Full Access | ✅ All Schools | ✅ All Resources | ✅ All Resources | ✅ Cross-School | ✅ Auto-Extract |
| **Teacher** | ✅ Assigned Classes | ✅ Assigned Classes | ✅ Own Resources | ✅ Own Resources | ✅ Own Resources | ✅ Within School | ✅ Auto-Extract |
| **Department Head** | ✅ Department | ✅ Department | ✅ Department | ✅ Department | ✅ Department | ✅ Within School | ✅ Auto-Extract |
| **Librarian** | ✅ All Classes | ✅ Limited | ✅ All Resources | ✅ Metadata Only | ❌ Limited | ✅ Within School | ✅ View Only |
| **Content Manager** | ✅ All Classes | ✅ All Classes | ✅ All Resources | ✅ All Resources | ✅ All Resources | ✅ Cross-School | ✅ Auto-Extract |
| **Student** | ❌ No Access | ❌ No Access | ✅ View Only | ❌ No Access | ❌ No Access | ❌ No Access | ❌ No Access |

#### **Detailed Permission Breakdown**

##### **1. School Administrator**
- **Upload Permissions**: Can upload any type of resource for any class/subject
- **Management**: Can manage all resources across the entire school
- **Sharing**: Can share resources with other schools in the district
- **Quality Control**: Can approve/reject resources uploaded by others
- **Storage Management**: Can manage storage quotas and cleanup policies

##### **2. Teacher (Class-Specific Access)**
- **Upload Permissions**: 
  - Can upload books for their assigned classes and subjects only
  - Can upload previous year question papers for their subjects
  - Cannot upload resources for classes they don't teach
- **Resource Scope**: Limited to their assigned classes and subjects
- **Collaboration**: Can share resources with other teachers in the same school
- **Quality Control**: Can verify and edit extracted questions from their uploads

##### **3. Department Head**
- **Upload Permissions**: Can upload resources for entire department
- **Oversight**: Can manage and review all department resources
- **Coordination**: Can coordinate resource sharing among department teachers
- **Quality Assurance**: Can set department-wide quality standards

##### **4. Librarian (Support Role)**
- **Upload Permissions**: Can upload general library books and reference materials
- **Management**: Can manage metadata and organization of resources
- **Access**: Full viewing access but limited editing capabilities
- **Support**: Can assist teachers with resource organization and cataloging

##### **5. Content Manager (Advanced Role)**
- **Upload Permissions**: Can upload any type of educational content
- **Cross-School**: Can share resources across multiple schools
- **Quality Control**: Can set extraction quality thresholds and validation rules
- **Advanced Features**: Access to advanced AI/ML extraction settings

#### **Upload Workflow by Role**

##### **Teacher Upload Process**
```
1. Authentication & Role Verification
   ↓
2. Class & Subject Assignment Check
   ↓
3. Upload Interface Access (Limited to assigned classes)
   ↓
4. Resource Upload & Validation
   ↓
5. AI/ML Processing (Automatic)
   ↓
6. Question Extraction & Verification
   ↓
7. Resource Publishing (Within school only)
```

##### **School Admin Upload Process**
```
1. Authentication & Admin Verification
   ↓
2. Full Upload Interface Access
   ↓
3. Resource Upload & Validation
   ↓
4. AI/ML Processing (Advanced settings)
   ↓
5. Quality Control & Review
   ↓
6. Cross-School Sharing Options
   ↓
7. Resource Publishing (Multi-school access)
```

#### **Permission Implementation**

##### **Database Schema for Permissions**
```sql
-- Resource Permissions Table
CREATE TABLE resource_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    resource_type VARCHAR(50), -- 'book', 'question_paper', 'all'
    permission_level VARCHAR(50), -- 'upload', 'view', 'edit', 'delete', 'share'
    scope_type VARCHAR(50), -- 'school', 'department', 'class', 'subject'
    scope_id UUID, -- Reference to specific scope
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Class-Subject Assignments for Teachers
CREATE TABLE teacher_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID REFERENCES users(id),
    class_id UUID REFERENCES classes(id),
    subject_id UUID REFERENCES subjects(id),
    academic_year VARCHAR(50),
    role VARCHAR(50) DEFAULT 'teacher', -- 'teacher', 'department_head'
    assigned_by UUID REFERENCES users(id),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);
```

##### **API Permission Checks**
```python
def check_upload_permission(user_id, resource_type, class_id, subject_id):
    # Check user role and assignments
    user = get_user(user_id)
    
    if user.role == 'school_admin':
        return True, 'Full access granted'
    
    elif user.role == 'teacher':
        # Check if teacher is assigned to this class and subject
        assignment = get_teacher_assignment(user_id, class_id, subject_id)
        if assignment and assignment.is_active:
            return True, 'Class-specific access granted'
        else:
            return False, 'Not assigned to this class/subject'
    
    elif user.role == 'department_head':
        # Check department-level permissions
        if is_department_head(user_id, subject_id):
            return True, 'Department access granted'
        else:
            return False, 'Not department head for this subject'
    
    # Additional role checks...
    return False, 'Insufficient permissions'

def upload_resource(user_id, resource_data, class_id, subject_id):
    # Permission check
    can_upload, message = check_upload_permission(user_id, resource_data['type'], class_id, subject_id)
    if not can_upload:
        raise PermissionError(message)
    
    # Proceed with upload
    return process_resource_upload(resource_data, user_id, class_id, subject_id)
```

#### **Resource Sharing Rules**

##### **Intra-School Sharing**
- **Teachers**: Can share with other teachers in the same school
- **Department Heads**: Can share within their department
- **School Admins**: Can share across entire school

##### **Inter-School Sharing**
- **School Admins**: Can share with affiliated schools
- **Content Managers**: Can share across school districts
- **System Admins**: Can create public resource libraries

#### **Quality Control Workflow**

##### **Teacher Upload Quality Control**
```
Upload → AI Extraction → Confidence Scoring → Teacher Review → Publish
```

##### **Admin Upload Quality Control**
```
Upload → AI Extraction → Confidence Scoring → Admin Review → School Approval → Publish
```

#### **Audit Trail & Compliance**
```sql
-- Resource Upload Audit Log
CREATE TABLE resource_upload_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    resource_id UUID,
    resource_type VARCHAR(50),
    action VARCHAR(50), -- 'upload', 'edit', 'delete', 'share'
    class_id UUID,
    subject_id UUID,
    permission_level VARCHAR(50),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Teacher Upload Interface & Workflow

        #### **Upload Dashboard Features**
        - **Class-wise Organization**: Select class (1st-12th), subject, academic year
        - **Subject-wise Categorization**: Automatic classification and tagging
        - **Metadata Entry**: Title, author, publisher, ISBN, edition, year, description
        - **File Validation**: Real-time size limits, format checks, password protection detection
        - **Progress Tracking**: Live upload progress, processing status updates

        #### **Supported File Formats**
        - **Books**: PDF (native/scanned), EPUB, DOCX, Images (JPG/PNG) for scanned pages
        - **Question Papers**: PDF (native/scanned), DOCX, Images (JPG/PNG) for scanned papers
        - **File Size Limits**: 100MB for direct upload, 500MB with chunked upload

        #### **Resource Upload Flow**

        ```
        ┌─────────────┐     ┌──────────────┐     ┌───────────────┐     ┌──────────────┐
        │   Teacher   │────▶│  Upload UI   │────▶│  Validation   │────▶│  S3 Storage  │
        │             │     │  Service     │     │   Service     │     │             │
        └─────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                           │                      │                   │
                           ▼                      ▼                   ▼
                   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
                   │  PostgreSQL  │    │  Processing  │    │  PostgreSQL  │
                   │  (Metadata)  │    │    Queue     │    │  (Status)    │
                   └──────────────┘    └──────────────┘    └──────────────┘
                           │                      │                   │
                           ▼                      ▼                   ▼
                   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
                   │  Document    │    │  Background  │    │  Notification│
                   │  Processing  │    │    Jobs      │    │   Service    │
                   │   Service    │    │             │    │             │
                   └──────────────┘    └──────────────┘    └──────────────┘
                           │                      │
           ┌───────────────┼───────────────┐      │
           │               │               │      ▼
           ▼               ▼               ▼  ┌──────────────┐
   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │  Question    │
   │  PDF Parser  │ │  OCR Engine  │ │  AI/ML       │ │  Bank (MongoDB)│
   │              │ │              │ │  Service     │ │              │
   └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
                           ▼
                   ┌──────────────┐
                   │  Quality     │
                   │  Control     │
                   └──────────────┘
        ```
- PDF (native and scanned)
- EPUB
- DOCX
- Images (JPG, PNG) - for scanned book pages

#### Question Papers
- PDF (native and scanned)
- DOCX
- Images (JPG, PNG) - for scanned papers

### Question Extraction Process

#### Step 1: File Upload & Validation
- Validate file type and size
- Check for password protection
- Extract basic metadata (title, author, page count)
- Store file in S3 with appropriate permissions

#### Step 2: Document Preprocessing
- **For Native PDFs**: Extract text directly using pdfplumber/PyPDF2
- **For Scanned PDFs/Images**: Apply OCR (Tesseract/AWS Textract)
  - Image preprocessing (deskewing, noise reduction, contrast enhancement)
  - OCR with multiple language support
  - Confidence scoring for each extracted text block

#### Step 3: Text Analysis & Segmentation
- Identify document structure (chapters, sections, headings)
- Detect question patterns using regex and NLP
- Classify content type (question, answer, explanation, content)
- Extract mathematical formulas using LaTeX/MathML

#### Step 4: Question Identification
- Use trained ML model to identify questions
- Pattern matching for common question formats:
  - "Q1.", "Question 1", "1."
  - "What is...", "How...", "Why..."
  - Multiple choice options (a), b), c), d))
  - True/False statements
- Confidence scoring for each identified question

#### Step 5: Question Extraction & Structuring
- Extract question text
- Extract options (for MCQs)
- Extract correct answers (when available)
- Extract explanations (when available)
- Detect question type (MCQ, True/False, Descriptive, etc.)
- Assign difficulty level (based on complexity analysis)

#### Step 6: Question Classification
- Tag questions by subject (using NLP classification)
- Tag questions by topic (keyword extraction)
- Assign difficulty (easy/medium/hard)
- Language detection
- Mark source information (book/paper, page number, chapter)

#### Step 7: Quality Control
- Filter questions with low confidence scores
- Detect and flag potential duplicates
- Validate question completeness
- Mark questions for manual review if needed

#### Step 8: Storage
- Store questions in PostgreSQL with structured schema
- Link questions to source resource via foreign keys
- Index for fast search and retrieval using PostgreSQL indexes
- Update resource processing status
- Utilize JSONB for flexible question data storage

### Question Generation from Resources

When teachers create tests, they can select questions from multiple sources:

#### Source Selection Options

1. **Manual Question Bank**: Questions created manually by teachers
2. **Book Questions**: Questions extracted from uploaded textbooks
3. **Question Papers**: Questions from previous year papers
4. **AI Generated**: Questions generated by AI based on topics
5. **Mixed**: Combination of all sources

#### Question Selection Interface

```
┌─────────────────────────────────────────────────────────┐
│  Select Questions for Test                               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Sources: [☑] Manual  [☑] Books  [☑] Question Papers    │
│                                                          │
│  Filters:                                                │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Subject: [Mathematics ▼]                          │  │
│  │ Class: [10th Grade ▼]                             │  │
│  │ Difficulty: [All ▼]                               │  │
│  │ Question Type: [All ▼]                            │  │
│  │ Topics: [Algebra, Geometry ▼]                     │  │
│  │ Year: [All Years ▼] (for question papers)        │  │
│  │ Books: [NCERT, RD Sharma ▼]                       │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  Available Questions: 1,234                              │
│  ┌───────────────────────────────────────────────────┐  │
│  │ ☑ Q1: What is the Pythagorean theorem?            │  │
│  │    Source: NCERT Class 10, Chapter 6, Page 123    │  │
│  │    Difficulty: Medium | Type: MCQ                 │  │
│  │    Confidence: 95%                                 │  │
│  ├───────────────────────────────────────────────────┤  │
│  │ ☐ Q2: Solve for x: 2x + 5 = 15                   │  │
│  │    Source: 2023 Question Paper, Board Exam         │  │
│  │    Difficulty: Easy | Type: Descriptive          │  │
│  │    Confidence: 88%                                 │  │
│  ├───────────────────────────────────────────────────┤  │
│  │ ☐ Q3: [More questions...]                         │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  Selected: 0 | Auto-select: [10 questions ▼]            │
│  [Add to Test] [Preview Selected]                       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### AI/ML Integration Details

#### Question Extraction Model

**Model Architecture**:
- **Base Model**: BERT or RoBERTa for text classification
- **Custom Fine-tuning**: Trained on educational question datasets
- **Multi-task Learning**: Question detection, type classification, difficulty prediction

**Training Data**:
- Labeled question datasets from educational resources
- Previous year question papers
- Textbook exercises
- Synthetic question generation

**Features**:
- Question pattern recognition
- Contextual understanding
- Multi-language support
- Mathematical formula handling

#### OCR Integration

**Options**:
1. **Tesseract OCR** (Open-source, self-hosted)
   - Good for basic text extraction
   - Requires preprocessing for best results
   - Free but lower accuracy

2. **AWS Textract** (Cloud-based)
   - High accuracy with ML-powered OCR
   - Automatic table and form detection
   - Pay-per-use pricing

3. **Google Vision API** (Cloud-based)
   - Excellent accuracy
   - Multiple language support
   - Pay-per-use pricing

**OCR Pipeline**:
```
Scanned PDF/Image
    ↓
Image Preprocessing
    ↓
OCR Engine
    ↓
Text Post-processing
    ↓
Layout Analysis
    ↓
Question Extraction
```

### Manual Verification Workflow

Questions extracted with low confidence scores or flagged for review go through a manual verification process:

#### Verification Queue
- Teachers can review pending questions
- Edit question text, options, answers
- Mark as verified or reject
- Add notes/corrections

#### Verification Interface
```
┌─────────────────────────────────────────────────────────┐
│  Question Verification Queue (45 pending)                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Question from: NCERT Class 10, Page 123                │
│  Confidence: 72% (Low - needs review)                   │
│                                                          │
│  Extracted Question:                                     │
│  ┌───────────────────────────────────────────────────┐  │
│  │ What is the formula for area of a circle?          │  │
│  │                                                    │  │
│  │ Options:                                           │  │
│  │ a) πr²  b) 2πr  c) πd  d) 4πr²                    │  │
│  │                                                    │  │
│  │ Correct Answer: a) πr²                            │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  Original Document View:                                 │
│  ┌───────────────────────────────────────────────────┐  │
│  │ [Page 123 from NCERT book]                       │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  Actions:                                                │
│  [✓ Approve] [Edit] [Reject] [Skip]                     │
│                                                          │
│  Notes: Add verification notes here...                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Search & Discovery

Teachers can search for questions across all resources:

#### Search Capabilities
- Full-text search across question text
- Filter by source (book, question paper, manual)
- Filter by class, subject, year
- Filter by difficulty, question type
- Filter by extraction confidence
- Semantic search using vector embeddings

#### Semantic Search
- Convert questions to vector embeddings using sentence transformers
- Store in vector database (Pinecone/Weaviate)
- Enable similarity-based question search
- Find conceptually similar questions

### Resource Sharing

#### School-Level Sharing
- Resources uploaded by teachers are shared within the school
- Admin can control sharing permissions
- Teachers can mark resources as public/private

#### Cross-School Sharing (Optional)
- Premium feature for sharing resources across schools
- Resource marketplace for verified questions
- Revenue sharing for content creators

### Performance Considerations

#### Large File Processing
- Chunked processing for large documents (100+ pages)
- Progress tracking and notifications
- Background job processing
- Priority queue for urgent requests

#### Scalability
- Horizontal scaling for document processing workers
- Distributed OCR processing
- Queue-based architecture for handling spikes
- Caching of processed documents

### Privacy & Security

#### Content Protection
- Encrypt stored documents at rest
- Signed URLs for secure access
- Watermarking for preview
- Access logging for all resource access

#### Copyright Compliance
- Terms of service for uploaded content
- Option to mark resources as "for educational use only"
- DMCA takedown process
- User responsibility for uploaded content

---

## Application Architecture

### Backend Architecture

#### Project Structure
```
backend/
├── src/
│   ├── config/           # Configuration files
│   ├── controllers/      # Request handlers
│   ├── services/         # Business logic
│   ├── models/           # Database models
│   ├── repositories/     # Data access layer
│   ├── middleware/       # Express middleware
│   ├── validators/       # Request validation
│   ├── utils/            # Utility functions
│   ├── workers/          # Background job workers
│   ├── routes/           # API routes
│   └── app.js            # App entry point
├── tests/
├── docker/
├── docs/
└── package.json
```

#### Design Patterns
- **Repository Pattern**: Data access abstraction
- **Factory Pattern**: Question creation
- **Strategy Pattern**: Different grading strategies
- **Observer Pattern**: Event-driven notifications
- **Decorator Pattern**: Question validation decorators

### Frontend Architecture

#### Project Structure
```
frontend/
├── src/
│   ├── components/       # Reusable components
│   │   ├── common/       # Common UI components
│   │   ├── test/         # Test-related components
│   │   ├── question/     # Question components
│   │   └── analytics/    # Analytics components
│   ├── pages/            # Page components
│   ├── layouts/          # Layout components
│   ├── hooks/            # Custom React hooks
│   ├── services/         # API services
│   ├── store/            # Redux store
│   ├── utils/            # Utility functions
│   ├── types/            # TypeScript types
│   ├── constants/        # Constants
│   └── App.tsx
├── public/
├── tests/
└── package.json
```

#### State Management
- Redux Toolkit for global state
- React Query for server state
- Context API for theme/auth
- Local state for component-specific data

---

## API Design

### RESTful API Endpoints

#### Authentication
```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/refresh
POST   /api/v1/auth/forgot-password
POST   /api/v1/auth/reset-password
POST   /api/v1/auth/verify-email
GET    /api/v1/auth/me
```

#### Users
```
GET    /api/v1/users
GET    /api/v1/users/:id
POST   /api/v1/users
PUT    /api/v1/users/:id
DELETE /api/v1/users/:id
GET    /api/v1/users/:id/tests
GET    /api/v1/users/:id/performance
```

#### Schools
```
GET    /api/v1/schools
GET    /api/v1/schools/:id
POST   /api/v1/schools
PUT    /api/v1/schools/:id
DELETE /api/v1/schools/:id
GET    /api/v1/schools/:id/teachers
GET    /api/v1/schools/:id/students
GET    /api/v1/schools/:id/analytics
```

#### Classes
```
GET    /api/v1/classes
GET    /api/v1/classes/:id
POST   /api/v1/classes
PUT    /api/v1/classes/:id
DELETE /api/v1/classes/:id
POST   /api/v1/classes/:id/students
DELETE /api/v1/classes/:id/students/:studentId
GET    /api/v1/classes/:id/tests
```

#### Subjects
```
GET    /api/v1/subjects
GET    /api/v1/subjects/:id
POST   /api/v1/subjects
PUT    /api/v1/subjects/:id
DELETE /api/v1/subjects/:id
```

#### Questions
```
GET    /api/v1/questions
GET    /api/v1/questions/:id
POST   /api/v1/questions
PUT    /api/v1/questions/:id
DELETE /api/v1/questions/:id
POST   /api/v1/questions/import
POST   /api/v1/questions/export
GET    /api/v1/questions/search
POST   /api/v1/questions/batch
```

#### Tests
```
GET    /api/v1/tests
GET    /api/v1/tests/:id
POST   /api/v1/tests
PUT    /api/v1/tests/:id
DELETE /api/v1/tests/:id
POST   /api/v1/tests/:id/publish
POST   /api/v1/tests/:id/unpublish
POST   /api/v1/tests/:id/duplicate
GET    /api/v1/tests/:id/preview
POST   /api/v1/tests/:id/questions
PUT    /api/v1/tests/:id/questions/:questionId
DELETE /api/v1/tests/:id/questions/:questionId
POST   /api/v1/tests/:id/schedule
GET    /api/v1/tests/:id/attempts
```

#### Test Taking
```
GET    /api/v1/tests/:id/start
POST   /api/v1/attempts/:id/answers
POST   /api/v1/attempts/:id/submit
GET    /api/v1/attempts/:id/progress
POST   /api/v1/attempts/:id/save-progress
GET    /api/v1/attempts/:id/result
```

#### Grading
```
GET    /api/v1/attempts/:id/grade
POST   /api/v1/attempts/:id/grade
GET    /api/v1/attempts/:id/answers/:answerId/grade
POST   /api/v1/attempts/:id/answers/:answerId/grade
GET    /api/v1/grading/queue
POST   /api/v1/grading/batch
```

#### Analytics
```
GET    /api/v1/analytics/test-performance/:testId
GET    /api/v1/analytics/class-performance/:classId
GET    /api/v1/analytics/student-performance/:studentId
GET    /api/v1/analytics/question-analysis/:questionId
GET    /api/v1/analytics/school-dashboard/:schoolId
POST   /api/v1/analytics/reports
```

#### Notifications
```
GET    /api/v1/notifications
PUT    /api/v1/notifications/:id/read
PUT    /api/v1/notifications/read-all
POST   /api/v1/notifications/settings
```

#### Resources - Books
```
GET    /api/v1/books
GET    /api/v1/books/:id
POST   /api/v1/books
PUT    /api/v1/books/:id
DELETE /api/v1/books/:id
GET    /api/v1/books/:id/chapters
GET    /api/v1/books/:id/questions
POST   /api/v1/books/:id/process
GET    /api/v1/books/search
```

#### Resources - Question Papers
```
GET    /api/v1/question-papers
GET    /api/v1/question-papers/:id
POST   /api/v1/question-papers
PUT    /api/v1/question-papers/:id
DELETE /api/v1/question-papers/:id
GET    /api/v1/question-papers/:id/questions
POST   /api/v1/question-papers/:id/process
GET    /api/v1/question-papers/search
GET    /api/v1/question-papers/by-year/:year
GET    /api/v1/question-papers/by-subject/:subjectId
```

#### Document Processing
```
GET    /api/v1/processing/jobs
GET    /api/v1/processing/jobs/:id
POST   /api/v1/processing/jobs/:id/cancel
GET    /api/v1/processing/jobs/:id/status
```

### WebSocket Events

#### Test Taking
```
// Client -> Server
join-test-room
submit-answer
save-progress
request-time-remaining

// Server -> Client
test-started
test-ended
time-warning
answer-saved
progress-updated
test-auto-submitted
student-joined
student-left
```

#### Real-time Monitoring
```
// Client -> Server
join-monitoring-room

// Server -> Client
student-started-test
student-submitted-test
student-flagged
attempt-count-update
```

### API Response Format

```json
{
  "success": true,
  "data": {},
  "message": "Success message",
  "errors": [],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 100
  }
}
```

### API Rate Limiting
- 1000 requests per minute per IP
- 100 requests per minute per user
- Stricter limits for test submission endpoints
- Burst allowance for critical operations

---

## Edge Cases & Error Handling

### Test Creation Edge Cases

#### 1. Invalid Test Configuration
- **Scenario**: Duration is 0 or negative
- **Handling**: Validate duration > 0, return error with message
- **Prevention**: Frontend validation, backend validation

#### 2. No Questions Added
- **Scenario**: Test published without questions
- **Handling**: Block publish, require at least 1 question
- **Prevention**: UI validation, disable publish button

#### 3. Overlapping Schedules
- **Scenario**: Student has multiple tests at same time
- **Handling**: Detect conflict, warn teacher, allow override
- **Prevention**: Calendar view, conflict detection

#### 4. Invalid Time Range
- **Scenario**: End time before start time
- **Handling**: Validate dates, return error
- **Prevention**: Date picker constraints

#### 5. Exceeding Question Limits
- **Scenario**: Too many questions for time limit
- **Handling**: Calculate estimated time, warn if insufficient
- **Prevention**: Real-time validation, suggested duration

### Test Taking Edge Cases

#### 1. Network Disconnection
- **Scenario**: Student loses internet during test
- **Handling**: 
  - Auto-save answers to localStorage
  - Show connection status
  - Allow offline continuation
  - Sync when reconnected
- **Prevention**: PWA support, periodic saves

#### 2. Browser Crash/Refresh
- **Scenario**: Student accidentally refreshes page
- **Handling**: 
  - Restore from last saved state
  - Show warning before refresh
  - Maintain timer state
- **Prevention**: BeforeUnload event handler

#### 3. Time Expiration
- **Scenario**: Timer reaches zero during answer submission
- **Handling**: 
  - Auto-submit current answers
  - Process partial submissions
  - Log auto-submit event
- **Prevention**: Time warnings at 5, 2, 1 minutes

#### 4. Multiple Tab/Window
- **Scenario**: Student opens test in multiple tabs
- **Handling**: 
  - Detect multiple sessions
  - Flag as suspicious
  - Allow teacher to invalidate
- **Prevention**: LocalStorage-based session tracking

#### 5. Device Switch
- **Scenario**: Student switches device mid-test
- **Handling**: 
  - Block new session if active exists
  - Allow with teacher approval
  - Log device change
- **Prevention**: Device fingerprinting

#### 6. Insufficient Permissions
- **Scenario**: Student tries to access unpublished test
- **Handling**: 403 error, redirect to dashboard
- **Prevention**: Backend permission checks

#### 7. Test Already Attempted
- **Scenario**: Student tries to retake beyond max attempts
- **Handling**: Show attempt limit reached, display previous results
- **Prevention**: Check attempts before allowing start

#### 8. Question Navigation Issues
- **Scenario**: Student tries to skip mandatory question
- **Handling**: Block navigation, require answer
- **Prevention**: UI validation, mandatory flag

### Grading Edge Cases

#### 1. Partial Credit Calculation
- **Scenario**: MCQ with multiple correct options
- **Handling**: 
  - Award partial credit for partial correct
  - Implement configurable scoring rules
  - Document scoring methodology
- **Prevention**: Clear rubric definition

#### 2. Subjective Answer Grading
- **Scenario**: No grader assigned for subjective questions
- **Handling**: 
  - Queue for manual grading
  - Notify teachers
  - Show "pending" status to students
- **Prevention**: Auto-assign graders, deadline alerts

#### 3. Grading Conflicts
- **Scenario**: Multiple teachers grading same answer
- **Handling**: 
  - Implement optimistic locking
  - Last write wins with audit
  - Show conflict resolution UI
- **Prevention**: Assignment locking

#### 4. Invalid Answer Format
- **Scenario**: Student submits answer in wrong format
- **Handling**: 
  - Validate on submission
  - Provide format hints
  - Allow re-submission if time permits
- **Prevention**: Input validation, format examples

#### 5. Late Submission Handling
- **Scenario**: Answers submitted after deadline
- **Handling**: 
  - Mark as late
  - Apply penalty if configured
  - Log late submission
- **Prevention**: Hard stop vs grace period config

### Performance Edge Cases

#### 1. High Concurrent Load
- **Scenario**: 1000+ students start test simultaneously
- **Handling**: 
  - Load balancing
  - Database connection pooling
  - Queue non-critical operations
  - Cache test configurations
- **Prevention**: Capacity planning, load testing

#### 2. Large Question Bank
- **Scenario**: Search across 100,000+ questions
- **Handling**: 
  - Pagination
  - Indexed search
  - Full-text search optimization
  - Result caching
- **Prevention**: Database indexing, search optimization

#### 3. Large File Uploads
- **Scenario**: Student uploads large answer files
- **Handling**: 
  - File size limits
  - Chunked upload
  - Progress indication
  - Virus scanning
- **Prevention**: Client-side validation, upload limits

#### 4. Report Generation Timeout
- **Scenario**: Complex report takes too long
- **Handling**: 
  - Background job processing
  - Email when ready
  - Progress tracking
  - Timeout with partial results
- **Prevention**: Query optimization, incremental loading

### Data Integrity Edge Cases

#### 1. Orphaned Records
- **Scenario**: Test deleted but attempts exist
- **Handling**: 
  - Soft delete only
  - Cascade delete with confirmation
  - Archive old data
- **Prevention**: Foreign key constraints, soft deletes

#### 2. Concurrent Updates
- **Scenario**: Two teachers edit same test simultaneously
- **Handling**: 
  - Optimistic locking
  - Version control
  - Merge conflict resolution
- **Prevention**: Edit locking, real-time collaboration

#### 3. Data Migration Issues
- **Scenario**: Schema changes break existing data
- **Handling**: 
  - Versioned migrations
  - Rollback capability
  - Data validation post-migration
- **Prevention**: Migration testing, backward compatibility

### Security Edge Cases

#### 1. Brute Force Attacks
- **Scenario**: Repeated login attempts
- **Handling**: 
  - Rate limiting
  - Account lockout
  - CAPTCHA after failures
  - IP blocking
- **Prevention**: Rate limiting, monitoring

#### 2. SQL Injection
- **Scenario**: Malicious input in search
- **Handling**: 
  - Parameterized queries
  - Input sanitization
  - ORM usage
- **Prevention**: Secure coding practices

#### 3. XSS Attacks
- **Scenario**: Malicious script in question text
- **Handling**: 
  - Input sanitization
  - Output encoding
  - CSP headers
- **Prevention**: Content security policy

#### 4. CSRF Attacks
- **Scenario**: Fake form submission
- **Handling**: 
  - CSRF tokens
  - SameSite cookies
  - Origin validation
- **Prevention**: CSRF middleware

#### 5. Data Exposure
- **Scenario**: API returns other students' data
- **Handling**: 
  - Strict permission checks
  - Data filtering
  - Audit logging
- **Prevention**: Role-based access control

### Resource Management Edge Cases

#### **1. Large File Upload**
- **Scenario**: Book/PDF file exceeds size limit (>500MB)
- **Handling**: 
  - Client-side validation with chunked upload support
  - Progress indication with pause/resume capability
  - Automatic compression suggestions
  - Alternative upload methods (FTP, direct S3 upload)
  - Email notification when upload completes
- **Prevention**: 
  - File size limits displayed prominently
  - Pre-upload compression tools
  - Bandwidth detection for upload time estimation
- **Technical Implementation**:
  ```javascript
  // Chunked upload with retry logic
  const uploadLargeFile = async (file, chunks = 10) => {
    const chunkSize = Math.ceil(file.size / chunks);
    for (let i = 0; i < chunks; i++) {
      const chunk = file.slice(i * chunkSize, (i + 1) * chunkSize);
      await uploadChunk(chunk, i, chunks);
    }
  };
  ```

#### **2. Corrupted Document**
- **Scenario**: Uploaded PDF is corrupted, password-protected, or malformed
- **Handling**: 
  - Multi-stage validation (header check, structure validation, content verification)
  - Password detection with user notification
  - Automatic repair attempts for minor corruption
  - Detailed error messages with suggested solutions
  - Fallback processing with partial extraction
- **Prevention**: 
  - Pre-upload file format validation
  - Supported format documentation
  - File integrity checksum verification
- **Technical Implementation**:
  ```python
  def validate_pdf_integrity(file_path):
      try:
          with open(file_path, 'rb') as f:
              header = f.read(5)
              if header != b'%PDF-':
                  return False, "Invalid PDF header"
          # Additional validation checks
          return True, "Valid PDF"
      except Exception as e:
          return False, f"Corruption detected: {str(e)}"
  ```

#### **3. OCR Failure**
- **Scenario**: Scanned document has poor quality, OCR accuracy < 60%
- **Handling**: 
  - Multi-engine OCR approach (Tesseract + AWS Textract + Google Vision)
  - Image preprocessing pipeline (deskewing, noise reduction, contrast enhancement)
  - Quality scoring with confidence thresholds
  - Manual review queue with prioritization
  - Progressive enhancement (basic OCR → advanced OCR → manual review)
- **Prevention**: 
  - Upload quality guidelines
  - Real-time quality assessment
  - Image format recommendations
- **Technical Implementation**:
  ```python
  def enhanced_ocr_pipeline(image):
      engines = ['tesseract', 'aws_textract', 'google_vision']
      results = []
      
      for engine in engines:
          try:
              result = ocr_with_engine(image, engine)
              confidence = calculate_confidence(result)
              if confidence > 0.7:
                  return result, confidence
              results.append((result, confidence))
          except Exception:
              continue
      
      # Fallback to best result or manual review
      return best_result_or_manual_review(results)
  ```

#### **4. Question Extraction Accuracy**
- **Scenario**: AI extracts questions with low confidence or incorrect classification
- **Handling**: 
  - Multi-model consensus approach (BERT + RoBERTa + custom models)
  - Confidence scoring with uncertainty quantification
  - Human-in-the-loop verification workflow
  - Active learning for model improvement
  - Context-aware validation (cross-reference with source material)
- **Prevention**: 
  - Model ensemble approach
  - Continuous training with user feedback
  - Quality thresholds and validation rules
- **Technical Implementation**:
  ```python
  class QuestionExtractionPipeline:
      def extract_with_confidence(self, text):
          models = [BERTModel(), RoBERTaModel(), CustomModel()]
          predictions = []
          
          for model in models:
              pred = model.predict(text)
              predictions.append(pred)
          
          # Ensemble prediction with confidence
          consensus = self.calculate_consensus(predictions)
          return consensus
  ```

#### **5. Duplicate Questions**
- **Scenario**: Same or similar questions extracted from multiple resources
- **Handling**: 
  - Semantic similarity detection using sentence embeddings
  - Hash-based exact duplicate detection
  - Fuzzy matching for near-duplicates
  - Source tracking and attribution
  - Merge strategies (keep best version, combine sources)
- **Prevention**: 
  - Pre-processing deduplication
  - Real-time duplicate detection during extraction
  - Source-aware question management
- **Technical Implementation**:
  ```python
  def detect_duplicate_questions(new_question, existing_questions):
      # Exact match
      exact_matches = find_exact_matches(new_question, existing_questions)
      
      # Semantic similarity
      embeddings = generate_embeddings([new_question] + existing_questions)
      similarities = cosine_similarity(embeddings[0], embeddings[1:])
      
      # Fuzzy matching
      fuzzy_matches = find_fuzzy_matches(new_question, existing_questions)
      
      return combine_duplicate_results(exact_matches, similarities, fuzzy_matches)
  ```

#### **6. Unsupported File Format**
- **Scenario**: User uploads unsupported or proprietary file format
- **Handling**: 
  - File type detection using magic bytes
  - Automatic format conversion when possible
  - Detailed error messages with conversion suggestions
  - Integration with online conversion services
  - Alternative upload methods
- **Prevention**: 
  - Clear format specification
  - Client-side file type validation
  - Drag-and-drop format checking
- **Technical Implementation**:
  ```python
  def handle_unsupported_format(file):
      file_type = detect_file_type(file)
      if file_type in SUPPORTED_FORMATS:
          return process_file(file)
      
      # Attempt conversion
      converted_file = attempt_conversion(file)
      if converted_file:
          return process_file(converted_file)
      
      # Provide guidance
      return suggest_conversion_options(file_type)
  ```

#### **7. Processing Timeout**
- **Scenario**: Large document (>1000 pages) takes too long to process
- **Handling**: 
  - Chunked processing with progress tracking
  - Background job queue with priority management
  - Real-time progress notifications
  - Cancellation and resume capabilities
  - Partial result delivery
- **Prevention**: 
  - Time estimation based on document complexity
  - Resource allocation scaling
  - Progressive processing strategies
- **Technical Implementation**:
  ```python
  def process_large_document(document):
      chunks = split_document_into_chunks(document, max_pages=50)
      job_id = create_background_job()
      
      for i, chunk in enumerate(chunks):
          process_chunk_async(chunk, job_id, i)
          update_progress(job_id, i/len(chunks))
      
      return job_id
  ```

#### **8. Language Detection**
- **Scenario**: Document in unsupported language or mixed languages
- **Handling**: 
  - Multi-language detection with confidence scoring
  - Language-specific OCR models
  - Manual language tagging interface
  - Translation integration for supported languages
  - Fallback processing with limited features
- **Prevention**: 
  - Language specification during upload
  - Supported language documentation
  - Automatic language detection warnings
- **Technical Implementation**:
  ```python
  def detect_and_handle_language(text):
      detected_languages = detect_languages(text)
      primary_language = max(detected_languages, key=lambda x: x['confidence'])
      
      if primary_language['code'] in SUPPORTED_LANGUAGES:
          return process_with_language_model(text, primary_language['code'])
      else:
          return handle_unsupported_language(text, detected_languages)
  ```

#### **9. Mathematical Formulas**
- **Scenario**: Document contains complex mathematical formulas and equations
- **Handling**: 
  - Specialized math OCR (Mathpix, LaTeX OCR)
  - Formula detection and extraction
  - Multiple format output (LaTeX, MathML, image)
  - Manual review for complex formulas
  - Integration with computer algebra systems
- **Prevention**: 
  - Math-aware preprocessing
  - Formula quality assessment
  - Alternative extraction methods
- **Technical Implementation**:
  ```python
  def extract_mathematical_formulas(document):
      # Detect formula regions
      formula_regions = detect_math_regions(document)
      
      extracted_formulas = []
      for region in formula_regions:
          # Try multiple extraction methods
          latex_result = extract_latex_formula(region)
          mathml_result = extract_mathml_formula(region)
          
          # Choose best result or flag for manual review
          best_result = choose_best_extraction(latex_result, mathml_result)
          extracted_formulas.append(best_result)
      
      return extracted_formulas
  ```

#### **10. Table Extraction**
- **Scenario**: Questions and data presented in complex table formats
- **Handling**: 
  - Advanced table detection algorithms
  - Structure analysis and reconstruction
  - Cell content extraction with context
  - Table-to-text conversion
  - Manual review for complex layouts
- **Prevention**: 
  - Table-aware OCR models
  - Multiple extraction strategies
  - Layout analysis preprocessing
- **Technical Implementation**:
  ```python
  def extract_table_content(image):
      # Detect table structure
      table_structure = detect_table_structure(image)
      
      # Extract cells with context
      cells = extract_table_cells(image, table_structure)
      
      # Reconstruct logical flow
      reconstructed_content = reconstruct_table_logic(cells)
      
      return reconstructed_content
  ```

#### **11. Storage Quota Exceeded**
- **Scenario**: School or user exceeds storage allocation limits
- **Handling**: 
  - Real-time quota monitoring
  - Graceful degradation with warnings
  - Automatic cleanup of old/temporary files
  - Upgrade options and recommendations
  - Data archiving solutions
- **Prevention**: 
  - Quota visibility in dashboard
  - Storage usage analytics
  - Automated cleanup policies

#### **12. Concurrent Processing Conflicts**
- **Scenario**: Multiple users processing same resource simultaneously
- **Handling**: 
  - Resource locking mechanisms
  - Distributed processing coordination
  - Conflict resolution strategies
  - Real-time status synchronization
  - Queue management with priorities
- **Prevention**: 
  - Resource state tracking
  - Distributed locking
  - Processing status broadcasting

#### **13. Network Interruption During Upload**
- **Scenario**: Network connection lost during large file upload
- **Handling**: 
  - Resumable upload support
  - Chunk-level retry logic
  - Automatic reconnection
  - Upload progress persistence
  - Bandwidth adaptation
- **Prevention**: 
  - Chunked upload architecture
  - Connection health monitoring
  - Upload state persistence

#### **14. Malicious File Upload**
- **Scenario**: User uploads malicious files (viruses, malware, exploits)
- **Handling**: 
  - Multi-layer security scanning
  - Sandboxed file processing
  - Content sanitization
  - Threat detection and quarantine
  - Security incident response
- **Prevention**: 
  - File type restrictions
  - Content validation
  - Security scanning integration

#### **15. Resource Version Conflicts**
- **Scenario**: Multiple versions of same resource uploaded
- **Handling**: 
  - Version control system
  - Change tracking and diff visualization
  - Merge strategies for different versions
  - Rollback capabilities
  - Conflict resolution workflows
- **Prevention**: 
  - Version management policies
  - Change detection
  - Automated versioning

This comprehensive edge case handling ensures robust resource management with proper error recovery, user guidance, and system resilience.

### Integration Edge Cases

#### 1. Payment Gateway Failure
- **Scenario**: Subscription payment fails
- **Handling**: 
  - Retry logic
  - Grace period
  - Notification to admin
  - Service downgrade
- **Prevention**: Webhook handling, retry queues

#### 2. Email Service Downtime
- **Scenario**: Cannot send notifications
- **Handling**: 
  - Queue emails
  - Retry with backoff
  - In-app notifications fallback
  - Alert monitoring
- **Prevention**: Multiple email providers, fallback

#### 3. File Storage Issues
- **Scenario**: S3 upload fails
- **Handling**: 
  - Retry with exponential backoff
  - Local fallback storage
  - User notification
  - Queue for retry
- **Prevention**: Health checks, monitoring

#### 4. AI/ML Service Unavailable
- **Scenario**: Question extraction service is down
- **Handling**: 
  - Queue processing jobs
  - Retry with exponential backoff
  - Fallback to manual processing
  - User notification
- **Prevention**: Service health checks, multiple providers

### Error Handling Strategy

#### Error Categories
1. **Validation Errors** (400)
   - Invalid input
   - Missing required fields
   - Format errors

2. **Authentication Errors** (401)
   - Invalid credentials
   - Token expired
   - Session invalid

3. **Authorization Errors** (403)
   - Insufficient permissions
   - Resource access denied

4. **Not Found Errors** (404)
   - Resource doesn't exist
   - Invalid endpoint

5. **Conflict Errors** (409)
   - Resource already exists
   - Version conflicts

6. **Rate Limit Errors** (429)
   - Too many requests
   - API quota exceeded

7. **Server Errors** (500)
   - Unexpected errors
   - Database failures
   - External service failures

#### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  },
  "requestId": "uuid"
}
```

#### Error Logging
- Log all errors with context
- Include request ID for tracing
- Stack traces for server errors
- Sanitize sensitive data
- Alert for critical errors

#### User-Friendly Error Messages
- Technical details for developers
- User-friendly messages for end users
- Suggested actions when possible
- Support contact information

---

## Security Considerations

### Authentication & Authorization

#### Authentication
- JWT-based stateless authentication
- Access token (15 min expiry) + Refresh token (7 days)
- Multi-factor authentication for admins
- OAuth 2.0 integration (Google, Microsoft)
- Password strength requirements
- Account lockout after failed attempts

#### Authorization
- Role-based access control (RBAC)
- Permission checks at API level
- Resource-level ownership validation
- Attribute-based access control (ABAC) for complex rules
- Audit logging for permission changes

### Data Security

#### Encryption
- TLS 1.3 for all communications
- AES-256 encryption for sensitive data at rest
- Password hashing with bcrypt/scrypt/argon2
- Encrypted backups
- Field-level encryption for PII

#### Data Privacy
- GDPR compliance
- Data retention policies
- Right to deletion
- Data export functionality
- Privacy policy integration

### API Security

#### Rate Limiting
- IP-based rate limiting
- User-based rate limiting
- Endpoint-specific limits
- Burst allowance configuration
- Distributed rate limiting (Redis)

#### Input Validation
- Schema validation (Joi/Zod)
- SQL injection prevention
- XSS prevention
- CSRF protection
- File upload validation

#### Secure Headers
- Content Security Policy (CSP)
- X-Frame-Options
- X-Content-Type-Options
- Strict-Transport-Security
- X-XSS-Protection

### Application Security

#### Session Management
- Secure cookie flags (HttpOnly, Secure, SameSite)
- Session timeout configuration
- Concurrent session limits
- Session invalidation on logout
- Session revocation for compromised accounts

#### Anti-Cheating Measures
- Browser tab detection
- Copy-paste prevention
- Print prevention
- Screen capture detection
- Proctoring integration options
- IP-based location tracking
- Device fingerprinting

#### Secure File Handling
- Virus scanning for uploads
- File type validation
- File size limits
- Secure file storage (S3 with policies)
- Signed URLs for downloads
- Temporary upload URLs

### Infrastructure Security

#### Network Security
- VPC isolation
- Security groups/firewalls
- Private subnets for databases
- VPN for admin access
- DDoS protection

#### Container Security
- Minimal base images
- Security scanning (Trivy)
- Non-root container users
- Resource limits
- Secrets management (HashiCorp Vault/AWS Secrets)

#### Secrets Management
- Environment-specific configs
- Encrypted secrets storage
- Rotation policies
- Audit access to secrets
- No secrets in code

### Monitoring & Incident Response

#### Security Monitoring
- Intrusion detection
- Anomaly detection
- Failed login monitoring
- Permission change alerts
- Data access logging

#### Incident Response
- Incident response plan
- Security team contact
- Breach notification procedures
- Post-incident analysis
- Regular security audits

---

## Performance Optimization

### Database Optimization

#### Query Optimization
- Index optimization
- Query plan analysis
- N+1 query prevention
- Batch operations
- Read replica usage

#### Caching Strategy
- Redis for session caching
- Application-level caching
- Query result caching
- CDN for static assets
- Browser caching headers

#### Connection Management
- Connection pooling (PgBouncer)
- Max connection limits
- Connection timeout configuration
- Idle connection cleanup

### Application Optimization

#### Code Optimization
- Async/await for I/O operations
- Efficient algorithms
- Memory leak prevention
- Profiling and monitoring
- Code splitting (frontend)

#### API Optimization
- Response compression (gzip/brotli)
- Pagination for large datasets
- Field selection (GraphQL-like)
- Batch API endpoints
- Response caching

#### Background Processing
- Async job processing
- Queue for heavy operations
- Worker scaling
- Job prioritization
- Dead letter queues

### Frontend Optimization

#### Bundle Optimization
- Code splitting
- Lazy loading
- Tree shaking
- Minification
- Asset optimization

#### Rendering Optimization
- Virtual scrolling for lists
- Memoization (React.memo)
- Debouncing/throttling
- Image optimization
- Font optimization

#### Network Optimization
- HTTP/2 or HTTP/3
- CDN usage
- Preloading critical resources
- Service worker for offline
- Progressive loading

### Load Testing Strategy

#### Test Scenarios
- Normal load: 1000 concurrent users
- Peak load: 5000 concurrent users
- Stress test: 10000+ concurrent users
- Test start spike: 2000 users in 1 minute
- Submission spike: 1000 submissions in 1 minute

#### Tools
- k6 for load testing
- Artillery for API testing
- Lighthouse for frontend
- Database load testing

#### Metrics to Monitor
- Response time (p50, p95, p99)
- Error rate
- Throughput (requests/sec)
- Database query times
- Memory/CPU usage

---

## Deployment Strategy

### Infrastructure

#### Cloud Provider
- AWS (recommended) or GCP/Azure
- Multi-region deployment for disaster recovery
- Region selection based on user base

#### Components
- **Application**: Kubernetes (EKS/GKE/AKS)
- **Database**: AWS RDS PostgreSQL
- **Cache**: AWS ElastiCache Redis
- **File Storage**: AWS S3
- **CDN**: CloudFront
- **Load Balancer**: AWS ALB
- **Message Queue**: AWS SQS/RabbitMQ

### CI/CD Pipeline

#### Stages
1. **Code Quality**
   - Linting (ESLint, Prettier)
   - Unit tests (Jest)
   - Integration tests
   - Security scanning (Snyk)

2. **Build**
   - Docker image build
   - Image optimization
   - Vulnerability scanning
   - Image tagging

3. **Deploy to Staging**
   - Kubernetes deployment
   - Database migrations
   - Smoke tests
   - E2E tests (Playwright)

4. **Deploy to Production**
   - Blue-green deployment
   - Canary release (10% traffic)
   - Monitoring and validation
   - Full rollout

#### Tools
- GitHub Actions or GitLab CI
- Docker for containerization
- Kubernetes for orchestration
- ArgoCD for GitOps
- Prometheus/Grafana for monitoring

### Environment Configuration

#### Environments
- Development (local)
- Staging (cloud)
- Production (cloud)

#### Configuration Management
- Environment variables
- Config maps (Kubernetes)
- Secrets (Kubernetes Secrets/AWS Secrets)
- Feature flags

### Database Migrations

#### Migration Strategy
- Version-controlled migrations
- Rollback capability
- Dry-run before production
- Zero-downtime migrations
- Data validation post-migration

#### Tools
- Flyway or node-pg-migrate
- Migration testing
- Backup before migration

### Monitoring & Logging

#### Application Monitoring
- APM (Datadog/New Relic)
- Error tracking (Sentry)
- Performance monitoring
- Custom metrics

#### Logging
- Structured logging (JSON)
- Log aggregation (ELK stack)
- Log retention policies
- Sensitive data filtering

#### Infrastructure Monitoring
- CloudWatch (AWS)
- Prometheus/Grafana
- Alert configuration
- Dashboard creation

### Backup & Disaster Recovery

#### Backup Strategy
- Daily automated backups
- Point-in-time recovery
- Cross-region replication
- Backup validation
- Restoration drills

#### Disaster Recovery
- RTO (Recovery Time Objective): 4 hours
- RPO (Recovery Point Objective): 15 minutes
- Failover procedures
- Documentation
- Regular testing

---

## Monitoring & Observability

### Metrics to Track

#### Application Metrics
- Request rate
- Response time (p50, p95, p99)
- Error rate
- Active users
- Test attempts per minute
- Grading queue size

#### Business Metrics
- Daily active users
- Tests created per day
- Tests completed per day
- Average test completion rate
- User engagement metrics

#### Infrastructure Metrics
- CPU/Memory usage
- Disk I/O
- Network I/O
- Database connections
- Cache hit rate

### Alerting

#### Critical Alerts
- Service down
- Error rate > 5%
- Response time > 2s (p95)
- Database connection pool exhausted
- Disk space < 10%

#### Warning Alerts
- High memory usage > 80%
- Slow queries > 1s
- Cache hit rate < 70%
- Queue backlog > 1000

#### Notification Channels
- PagerDuty for critical
- Slack for warnings
- Email for non-urgent
- SMS for emergencies

### Logging Strategy

#### Log Levels
- ERROR: Errors requiring attention
- WARN: Warning conditions
- INFO: Informational messages
- DEBUG: Debugging information

#### Log Structure
```json
{
  "timestamp": "2024-01-01T00:00:00Z",
  "level": "INFO",
  "service": "test-service",
  "environment": "production",
  "requestId": "uuid",
  "userId": "uuid",
  "message": "Test started",
  "metadata": {}
}
```

### Distributed Tracing

#### Implementation
- OpenTelemetry
- Jaeger or AWS X-Ray
- Trace context propagation
- Service dependency mapping

---

## Implementation Phases

### Phase 1: Foundation (4-6 weeks)

#### Backend
- [ ] Project setup and configuration
- [ ] Database schema design and implementation
- [ ] Authentication service
- [ ] User management service
- [ ] Basic API structure
- [ ] Docker setup
- [ ] CI/CD pipeline setup

#### Frontend
- [ ] Project setup (React + TypeScript)
- [ ] Routing and layout structure
- [ ] Authentication UI
- [ ] User profile UI
- [ ] Basic component library
- [ ] State management setup

#### Infrastructure
- [ ] Cloud account setup
- [ ] Kubernetes cluster setup
- [ ] Database setup (PostgreSQL)
- [ ] Redis setup
- [ ] CI/CD infrastructure
- [ ] Monitoring setup

### Phase 2: Core Features (6-8 weeks)

#### Backend
- [ ] School management
- [ ] Class management
- [ ] Subject management
- [ ] Question bank service (basic CRUD)
- [ ] Test management service (basic CRUD)
- [ ] Test scheduling
- [ ] File upload service
- [ ] Resource management service (basic CRUD)
- [ ] Book upload and metadata extraction
- [ ] Question paper upload and metadata extraction

#### Frontend
- [ ] School management UI
- [ ] Class management UI
- [ ] Subject management UI
- [ ] Question bank UI
- [ ] Test creation UI
- [ ] Test scheduling UI
- [ ] File upload component
- [ ] Book upload UI
- [ ] Question paper upload UI
- [ ] Resource library UI

### Phase 3: Test Taking (4-6 weeks)

#### Backend
- [ ] Test taking service
- [ ] Answer submission
- [ ] Progress tracking
- [ ] Timer management
- [ ] Auto-save functionality
- [ ] WebSocket implementation

#### Frontend
- [ ] Test taking interface
- [ ] Question display components
- [ ] Timer component
- [ ] Navigation component
- [ ] Answer submission
- [ ] Progress indicator

### Phase 4: Grading & Analytics (4-6 weeks)

#### Backend
- [ ] Auto-grading service
- [ ] Manual grading interface
- [ ] Grading queue
- [ ] Analytics service
- [ ] Report generation
- [ ] Performance metrics calculation

#### Frontend
- [ ] Grading interface
- [ ] Results display
- [ ] Analytics dashboard
- [ ] Performance charts
- [ ] Report generation UI
- [ ] Export functionality

### Phase 5: Advanced Features (4-6 weeks)

#### Backend
- [ ] Question bank advanced features (tags, search)
- [ ] Test templates
- [ ] Bulk operations
- [ ] Notification service
- [ ] Email integration
- [ ] SMS integration
- [ ] Resource search and filtering
- [ ] Resource sharing functionality
- [ ] Document processing queue management

#### Frontend
- [ ] Advanced question search
- [ ] Test templates
- [ ] Bulk operations UI
- [ ] Notification center
- [ ] Settings management
- [ ] Resource search UI
- [ ] Resource sharing UI
- [ ] Processing status dashboard

### Phase 6: AI/ML & Question Extraction (6-8 weeks)

#### Backend
- [ ] Document processing service setup
- [ ] PDF parser integration (pdfplumber/PyPDF2)
- [ ] OCR engine integration (Tesseract/AWS Textract)
- [ ] AI/ML service setup
- [ ] Question extraction model training/fine-tuning
- [ ] Question identification and classification
- [ ] Answer extraction logic
- [ ] Quality scoring and confidence calculation
- [ ] Duplicate detection algorithm
- [ ] Chapter/section detection
- [ ] Mathematical formula recognition
- [ ] Background job processing for documents
- [ ] Processing queue management
- [ ] Vector database setup for semantic search
- [ ] Embedding generation for questions

#### Frontend
- [ ] Document upload with progress tracking
- [ ] Processing status display
- [ ] Question verification queue UI
- [ ] Manual verification interface
- [ ] Source selection in question picker
- [ ] Resource filtering in test creation
- [ ] Preview extracted questions
- [ ] Bulk verification tools

### Phase 7: Security & Hardening (2-3 weeks)

#### Backend
- [ ] Security audit
- [ ] Rate limiting implementation
- [ ] Input validation enhancement
- [ ] SQL injection prevention
- [ ] XSS prevention
- [ ] CSRF protection

#### Frontend
- [ ] Security hardening
- [ ] CSP implementation
- [ ] Secure cookie configuration
- [ ] Input sanitization

### Phase 8: Performance Optimization (2-3 weeks)

#### Backend
- [ ] Query optimization
- [ ] Caching implementation
- [ ] Database indexing
- [ ] Connection pooling
- [ ] Background job optimization

#### Frontend
- [ ] Bundle optimization
- [ ] Lazy loading
- [ ] Code splitting
- [ ] Image optimization
- [ ] Performance testing

### Phase 9: Testing & QA (3-4 weeks)

#### Testing
- [ ] Unit tests (80% coverage)
- [ ] Integration tests
- [ ] E2E tests
- [ ] Load testing
- [ ] Security testing
- [ ] Performance testing

#### QA
- [ ] Manual testing
- [ ] User acceptance testing
- [ ] Bug fixes
- [ ] Documentation review

### Phase 10: Deployment & Launch (2-3 weeks)

#### Deployment
- [ ] Production environment setup
- [ ] Database migration
- [ ] Full deployment
- [ ] Smoke tests
- [ ] Monitoring validation

#### Launch
- [ ] User training
- [ ] Documentation finalization
- [ ] Support setup
- [ ] Go-live

### Phase 11: Post-Launch Support (Ongoing)

#### Support
- [ ] Bug fixes
- [ ] Performance monitoring
- [ ] User feedback collection
- [ ] Feature requests prioritization
- [ ] Regular updates

#### Maintenance
- [ ] Security updates
- [ ] Dependency updates
- [ ] Database maintenance
- [ ] Backup verification
- [ ] Cost optimization

---

## Success Criteria

### Technical Metrics
- 99.9% uptime
- < 500ms p95 response time
- Support 10,000 concurrent users
- < 1% error rate
- 80%+ test coverage

### Business Metrics
- 100+ schools onboarded in first 6 months
- 10,000+ tests created in first 6 months
- 100,000+ test attempts in first 6 months
- < 5% user churn rate
- 4.5+ star user rating

---

## Risks & Mitigations

### Technical Risks

#### Risk: Database Performance Issues
- **Mitigation**: Proper indexing, read replicas, caching, query optimization

#### Risk: Scalability Challenges
- **Mitigation**: Load testing, horizontal scaling, auto-scaling configuration

#### Risk: Security Vulnerabilities
- **Mitigation**: Security audits, penetration testing, regular updates

#### Risk: Third-party Service Downtime
- **Mitigation**: Multiple providers, fallback mechanisms, monitoring

### Business Risks

#### Risk: Low User Adoption
- **Mitigation**: User training, excellent support, continuous improvement

#### Risk: Competition
- **Mitigation**: Unique features, better UX, competitive pricing

#### Risk: Regulatory Compliance
- **Mitigation**: Legal consultation, compliance audits, data protection

---

## Conclusion

This implementation plan provides a comprehensive roadmap for building a scalable, robust assessment engine. The phased approach ensures manageable development cycles while delivering value incrementally. The architecture is designed for scalability from day one, with clear strategies for handling growth and edge cases.

Key success factors:
- Adherence to the phased implementation plan
- Continuous testing and quality assurance
- Regular performance monitoring and optimization
- Strong security practices
- Responsive user support and feedback incorporation

The system is designed to handle the complexities of educational assessment while providing a seamless experience for all stakeholders - schools, teachers, and students.
