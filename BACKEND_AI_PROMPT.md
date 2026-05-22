# Backend Development AI Prompt

## Task Overview
Generate a complete, production-ready backend for the Assessment Engine based on the comprehensive implementation plan. The frontend is already built, so focus solely on backend implementation with zero errors.

## Architecture Requirements

### **Technology Stack**
- **Backend**: Node.js with Express.js
- **Database**: PostgreSQL only (no MongoDB)
- **ORM**: Prisma for database management
- **Authentication**: JWT with refresh tokens
- **Validation**: Joi/Zod for input validation
- **File Storage**: AWS S3/MinIO
- **Queue System**: Bull Queue with Redis
- **AI/ML**: Python microservices for question extraction
- **Real-time**: Socket.io for live features
- **Testing**: Jest + Supertest
- **Documentation**: Swagger/OpenAPI

### **Project Structure**
```
backend/
├── src/
│   ├── controllers/
│   │   ├── auth.controller.js
│   │   ├── user.controller.js
│   │   ├── school.controller.js
│   │   ├── test.controller.js
│   │   ├── question.controller.js
│   │   ├── resource.controller.js
│   │   ├── analytics.controller.js
│   │   └── notification.controller.js
│   ├── services/
│   │   ├── auth.service.js
│   │   ├── user.service.js
│   │   ├── test.service.js
│   │   ├── question.service.js
│   │   ├── resource.service.js
│   │   ├── ai-extraction.service.js
│   │   ├── email.service.js
│   │   └── analytics.service.js
│   ├── middleware/
│   │   ├── auth.middleware.js
│   │   ├── validation.middleware.js
│   │   ├── permission.middleware.js
│   │   ├── rate-limit.middleware.js
│   │   └── error.middleware.js
│   ├── models/
│   │   ├── User.js
│   │   ├── School.js
│   │   ├── Test.js
│   │   ├── Question.js
│   │   ├── Resource.js
│   │   └── associations.js
│   ├── routes/
│   │   ├── auth.routes.js
│   │   ├── user.routes.js
│   │   ├── school.routes.js
│   │   ├── test.routes.js
│   │   ├── question.routes.js
│   │   ├── resource.routes.js
│   │   └── analytics.routes.js
│   ├── utils/
│   │   ├── database.js
│   │   ├── redis.js
│   │   ├── s3.js
│   │   ├── email.js
│   │   ├── logger.js
│   │   └── helpers.js
│   ├── config/
│   │   ├── database.config.js
│   │   ├── redis.config.js
│   │   ├── s3.config.js
│   │   └── app.config.js
│   ├── jobs/
│   │   ├── resource-processing.job.js
│   │   ├── question-extraction.job.js
│   │   ├── email-notification.job.js
│   │   └── analytics-calculation.job.js
│   └── app.js
├── prisma/
│   ├── schema.prisma
│   ├── migrations/
│   └── seed.js
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
│   └── api/
├── package.json
├── .env.example
└── README.md
```

## Database Implementation

### **Prisma Schema Requirements**
Create a complete Prisma schema based on the PostgreSQL schema from the implementation plan:

```prisma
// This is a template - implement the full schema
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model School {
  id                String   @id @default(cuid())
  name              String
  code              String   @unique
  domain            String?
  logoUrl           String?  @map("logo_url")
  address           String?
  contactEmail      String?  @map("contact_email")
  contactPhone      String?  @map("contact_phone")
  subscriptionPlan  String   @default("basic") @map("subscription_plan")
  subscriptionStatus String  @default("active") @map("subscription_status")
  subscriptionExpiry DateTime? @map("subscription_expiry")
  settings          Json     @default("{}")
  createdAt         DateTime @default(now()) @map("created_at")
  updatedAt         DateTime @updatedAt @map("updated_at")
  deletedAt         DateTime? @map("deleted_at")

  users     User[]
  classes   Class[]
  subjects  Subject[]
  tests     Test[]
  books     Book[]
  questionPapers QuestionPaper[]

  @@map("schools")
}

// Implement all other models from the implementation plan
// User, Class, Subject, Test, TestAttempt, Question, etc.
```

### **Database Connection & Configuration**
```javascript
// src/utils/database.js
const { PrismaClient } = require('@prisma/client');
const logger = require('./logger');

class Database {
  constructor() {
    this.prisma = new PrismaClient({
      log: ['query', 'info', 'warn', 'error'],
      errorFormat: 'pretty'
    });
  }

  async connect() {
    try {
      await this.prisma.$connect();
      logger.info('Database connected successfully');
      
      // Run migrations in production
      if (process.env.NODE_ENV === 'production') {
        await this.runMigrations();
      }
    } catch (error) {
      logger.error('Database connection failed:', error);
      process.exit(1);
    }
  }

  async disconnect() {
    await this.prisma.$disconnect();
  }

  async runMigrations() {
    // Implement migration logic
  }

  async healthCheck() {
    try {
      await this.prisma.$queryRaw`SELECT 1`;
      return { status: 'healthy', timestamp: new Date() };
    } catch (error) {
      return { status: 'unhealthy', error: error.message };
    }
  }
}

module.exports = new Database();
```

## Core Features Implementation

### **1. Authentication System**
Implement JWT-based authentication with:
- Access tokens (15 minutes)
- Refresh tokens (7 days)
- Role-based permissions
- Multi-factor authentication support
- Session management
- Password reset functionality

```javascript
// src/services/auth.service.js
class AuthService {
  async register(userData) {
    // Implement user registration with validation
    // Hash passwords with bcrypt
    // Send verification email
    // Create default roles
  }

  async login(credentials) {
    // Validate credentials
    // Generate JWT tokens
    // Track login attempts
    // Return user data with permissions
  }

  async refreshToken(refreshToken) {
    // Validate refresh token
    // Generate new access token
    // Revoke old refresh token if needed
  }

  async logout(token) {
    // Revoke token
    // Clear session data
  }

  async forgotPassword(email) {
    // Generate reset token
    // Send reset email
  }

  async resetPassword(token, newPassword) {
    // Validate reset token
    // Update password
    // Clear reset token
  }
}
```

### **2. User Management System**
Implement role-based user management:
- School Admin, Teacher, Student roles
- Department Head, Librarian, Content Manager roles
- Permission-based access control
- User profile management
- Bulk user operations

```javascript
// src/services/user.service.js
class UserService {
  async createProfile(userId, profileData) {
    // Create or update user profile
    // Validate role-specific fields
    // Handle file uploads for profile pictures
  }

  async getUsers(filters, pagination) {
    // Implement filtering by role, school, class
    // Apply pagination and sorting
    // Return user data with permissions
  }

  async updateUser(userId, updateData) {
    // Update user information
    // Validate permissions
    // Audit changes
  }

  async assignRole(userId, roleId, permissions) {
    // Assign roles to users
    // Update permissions
    // Notify user of role changes
  }

  async bulkImportUsers(userData, schoolId) {
    // Import multiple users from CSV/Excel
    // Validate data
    // Create accounts with default passwords
    // Send welcome emails
  }
}
```

### **3. Test Management System**
Implement comprehensive test management:
- Test creation with multiple question types
- Test scheduling and publishing
- Question randomization
- Time limits and attempts
- Test templates and duplication

```javascript
// src/services/test.service.js
class TestService {
  async createTest(testData, createdBy) {
    // Validate test configuration
    // Check for schedule conflicts
    // Create test with questions
    // Set up notifications
  }

  async addQuestionsToTest(testId, questions) {
    // Add questions to test
    // Calculate estimated time
    // Validate question distribution
    // Update test metadata
  }

  async scheduleTest(testId, scheduleData) {
    // Validate schedule timing
    // Check for conflicts
    // Create test schedules
    // Send notifications
  }

  async publishTest(testId) {
    // Validate test readiness
    // Publish test
    // Create test instances for students
    // Send notifications
  }

  async duplicateTest(testId, newTestData) {
    // Duplicate test configuration
    // Copy questions or create new selection
    // Create new test instance
    // Return new test ID
  }
}
```

### **4. Question Bank System**
Implement flexible question management:
- Multiple question types (MCQ, True/False, Descriptive, Coding, etc.)
- Question categorization and tagging
- Question versioning
- Import/export functionality
- AI-powered question generation

```javascript
// src/services/question.service.js
class QuestionService {
  async createQuestion(questionData, createdBy) {
    // Validate question structure
    // Handle different question types
    // Store options, answers, rubrics
    // Set metadata and tags
  }

  async getQuestions(filters, pagination) {
    // Implement advanced filtering
    // Search by text, tags, difficulty
    // Apply role-based access
    // Return paginated results
  }

  async importQuestions(fileData, format) {
    // Parse CSV/JSON/Excel files
    // Validate question structure
    // Import questions with error handling
    // Return import report
  }

  async exportQuestions(filters, format) {
    // Filter questions based on criteria
    // Export in requested format
    // Include media files if needed
  }

  async generateQuestionsAI(topics, count, difficulty) {
    // Call AI service for question generation
    // Validate generated questions
    // Store in question bank
    // Return generated questions
  }
}
```

### **5. Resource Management System**
Implement book and question paper management:
- File upload with validation
- AI/ML question extraction
- Resource categorization
- Processing status tracking
- Version control

```javascript
// src/services/resource.service.js
class ResourceService {
  async uploadResource(fileData, metadata, uploadedBy) {
    // Validate file type and size
    // Upload to S3/MinIO
    // Create resource record
    // Queue for AI processing
  }

  async processResource(resourceId) {
    // Download file from storage
    // Extract text using appropriate parser
    // Run AI question extraction
    // Update processing status
  }

  async extractQuestionsAI(resourceId) {
    // Call AI extraction service
    // Process extracted questions
    // Store questions with source tracking
    // Update resource metadata
  }

  async getResources(filters, pagination) {
    // Filter by type, class, subject
    // Apply user permissions
    // Return paginated results
  }

  async verifyExtractedQuestions(resourceId, questionUpdates) {
    // Update question data based on verification
    // Mark questions as verified
    // Update resource processing status
  }
}
```

### **6. AI/ML Integration**
Implement Python microservices for:
- OCR and text extraction
- Question identification and extraction
- Question classification and tagging
- Duplicate detection
- Quality scoring

```javascript
// src/services/ai-extraction.service.js
class AIExtractionService {
  async extractTextFromPDF(fileUrl) {
    // Call Python OCR service
    // Return extracted text with confidence scores
  }

  async identifyQuestions(text) {
    // Call AI question detection service
    // Return identified questions with metadata
  }

  async classifyQuestion(questionText) {
    // Call AI classification service
    // Return question type, difficulty, topics
  }

  async detectDuplicates(questions) {
    // Call AI duplicate detection service
    // Return duplicate groups and suggestions
  }

  async generateQuestions(topics, count, difficulty) {
    // Call AI question generation service
    // Return generated questions with confidence
  }
}
```

### **7. Test Taking System**
Implement secure test taking:
- Real-time test delivery
- Answer auto-save
- Timer management
- Anti-cheating measures
- Offline support

```javascript
// src/services/test-taking.service.js
class TestTakingService {
  async startTest(testId, studentId) {
    // Validate test availability
    // Create test attempt
    // Return test questions (randomized if needed)
    // Start timer
  }

  async submitAnswer(attemptId, questionId, answer) {
    // Validate answer format
    // Save answer to database
    // Update progress
    // Check for time expiration
  }

  async submitTest(attemptId, answers) {
    // Validate all answers
    // Calculate scores for objective questions
    // Queue subjective questions for grading
    // Update attempt status
  }

  async autoSubmitTest(attemptId) {
    // Handle time expiration
    // Submit current answers
    // Calculate partial scores
    // Notify student
  }
}
```

### **8. Grading System**
Implement automated and manual grading:
- Auto-grading for objective questions
- Manual grading interface for subjective
- Grade calculation and reporting
- Rubric-based grading

```javascript
// src/services/grading.service.js
class GradingService {
  async autoGradeObjectiveQuestions(attemptId) {
    // Grade MCQ, True/False, Fill-in-blank
    // Calculate scores
    // Update attempt results
  }

  async getGradingQueue(teacherId) {
    // Get pending subjective questions
    // Filter by teacher's subjects
    // Return prioritized queue
  }

  async gradeSubjectiveQuestion(attemptId, questionId, gradeData) {
    // Validate grading data
    // Update question grade
    // Calculate total score
    // Update attempt if complete
  }

  async calculateFinalScore(attemptId) {
    // Sum all question scores
    // Apply negative marking if needed
    // Determine pass/fail status
    // Generate grade report
  }
}
```

### **9. Analytics System**
Implement comprehensive analytics:
- Performance metrics
- Class-wise analytics
- Question-wise analysis
- Progress tracking
- Report generation

```javascript
// src/services/analytics.service.js
class AnalyticsService {
  async getTestAnalytics(testId) {
    // Calculate test statistics
    // Generate performance charts
    // Analyze question difficulty
    // Return comprehensive analytics
  }

  async getStudentPerformance(studentId, filters) {
    // Get student's test history
    // Calculate performance trends
    // Identify strengths/weaknesses
    // Generate progress report
  }

  async getClassPerformance(classId, subjectId, timeframe) {
    // Calculate class averages
    // Compare performance across tests
    // Identify improvement areas
    // Generate class report
  }

  async generateReport(reportType, filters) {
    // Generate various report types
    // Export in multiple formats
    // Include visualizations
    // Schedule report delivery
  }
}
```

### **10. Notification System**
Implement multi-channel notifications:
- Email notifications
- In-app notifications
- SMS notifications
- Push notifications
- Real-time updates

```javascript
// src/services/notification.service.js
class NotificationService {
  async sendEmailNotification(userId, template, data) {
    // Generate email content
    // Send via email service
    // Track delivery status
  }

  async createInAppNotification(userId, notificationData) {
    // Create notification record
    // Send real-time via Socket.io
    // Update notification count
  }

  async sendSMSNotification(phoneNumber, message) {
    // Send SMS via provider
    // Track delivery status
  }

  async scheduleNotification(notificationData, scheduleTime) {
    // Queue notification for later delivery
    // Handle recurring notifications
  }
}
```

## API Implementation

### **RESTful API Design**
Implement comprehensive REST APIs following OpenAPI 3.0 specification:

```javascript
// src/routes/auth.routes.js
const express = require('express');
const authController = require('../controllers/auth.controller');
const validateRequest = require('../middleware/validation.middleware');
const { authSchemas } = require('../schemas/auth.schemas');

const router = express.Router();

router.post('/register', validateRequest(authSchemas.register), authController.register);
router.post('/login', validateRequest(authSchemas.login), authController.login);
router.post('/refresh', authController.refreshToken);
router.post('/logout', authController.logout);
router.post('/forgot-password', validateRequest(authSchemas.forgotPassword), authController.forgotPassword);
router.post('/reset-password', validateRequest(authSchemas.resetPassword), authController.resetPassword);

module.exports = router;
```

### **Validation Schemas**
Implement comprehensive input validation:

```javascript
// src/schemas/auth.schemas.js
const Joi = require('joi');

const authSchemas = {
  register: Joi.object({
    email: Joi.string().email().required(),
    password: Joi.string().min(8).pattern(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/).required(),
    firstName: Joi.string().min(2).max(50).required(),
    lastName: Joi.string().min(2).max(50).required(),
    role: Joi.string().valid('admin', 'teacher', 'student').required(),
    schoolCode: Joi.string().required(),
    phone: Joi.string().pattern(/^[+]?[\d\s-()]+$/).optional(),
    dateOfBirth: Joi.date().optional()
  }),

  login: Joi.object({
    email: Joi.string().email().required(),
    password: Joi.string().required(),
    rememberMe: Joi.boolean().default(false)
  }),

  forgotPassword: Joi.object({
    email: Joi.string().email().required()
  }),

  resetPassword: Joi.object({
    token: Joi.string().required(),
    password: Joi.string().min(8).pattern(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/).required()
  })
};

module.exports = { authSchemas };
```

### **Error Handling**
Implement comprehensive error handling:

```javascript
// src/middleware/error.middleware.js
const logger = require('../utils/logger');

class AppError extends Error {
  constructor(message, statusCode, isOperational = true) {
    super(message);
    this.statusCode = statusCode;
    this.isOperational = isOperational;
    this.status = `${statusCode}`.startsWith('4') ? 'fail' : 'error';

    Error.captureStackTrace(this, this.constructor);
  }
}

const errorHandler = (err, req, res, next) => {
  let error = { ...err };
  error.message = err.message;

  // Log error
  logger.error(err);

  // Prisma errors
  if (err.code === 'P2002') {
    const message = 'Duplicate field value entered';
    error = new AppError(message, 400);
  }

  // JWT errors
  if (err.name === 'JsonWebTokenError') {
    const message = 'Invalid token';
    error = new AppError(message, 401);
  }

  // Validation errors
  if (err.isJoi) {
    const message = err.details[0].message;
    error = new AppError(message, 400);
  }

  res.status(error.statusCode || 500).json({
    status: error.status || 'error',
    message: error.message || 'Internal server error',
    ...(process.env.NODE_ENV === 'development' && { stack: error.stack })
  });
};

module.exports = { AppError, errorHandler };
```

## Security Implementation

### **Authentication Middleware**
```javascript
// src/middleware/auth.middleware.js
const jwt = require('jsonwebtoken');
const { promisify } = require('util');
const { AppError } = require('./error.middleware');
const User = require('../models/User');
const logger = require('../utils/logger');

const protect = async (req, res, next) => {
  try {
    // Get token from header
    let token;
    if (req.headers.authorization && req.headers.authorization.startsWith('Bearer')) {
      token = req.headers.authorization.split(' ')[1];
    }

    if (!token) {
      return next(new AppError('Access token is required', 401));
    }

    // Verify token
    const decoded = await promisify(jwt.verify)(token, process.env.JWT_SECRET);

    // Check if user still exists
    const user = await User.findById(decoded.id);
    if (!user) {
      return next(new AppError('User not found', 401));
    }

    // Check if user is active
    if (!user.isActive) {
      return next(new AppError('User account is deactivated', 401));
    }

    // Grant access
    req.user = user;
    next();
  } catch (error) {
    logger.error('Auth middleware error:', error);
    return next(new AppError('Invalid token', 401));
  }
};

const restrictTo = (...roles) => {
  return (req, res, next) => {
    if (!roles.includes(req.user.role)) {
      return next(new AppError('Insufficient permissions', 403));
    }
    next();
  };
};

module.exports = { protect, restrictTo };
```

### **Rate Limiting**
```javascript
// src/middleware/rate-limit.middleware.js
const rateLimit = require('express-rate-limit');
const RedisStore = require('rate-limit-redis');
const redisClient = require('../utils/redis');

const createRateLimiter = (windowMs, max, message) => {
  return rateLimit({
    store: new RedisStore({
      client: redisClient,
      prefix: 'rl:'
    }),
    windowMs,
    max,
    message: { status: 'error', message },
    standardHeaders: true,
    legacyHeaders: false
  });
};

const authLimiter = createRateLimiter(15 * 60 * 1000, 5, 'Too many auth attempts');
const generalLimiter = createRateLimiter(15 * 60 * 1000, 100, 'Too many requests');
const uploadLimiter = createRateLimiter(60 * 60 * 1000, 10, 'Too many upload attempts');

module.exports = { authLimiter, generalLimiter, uploadLimiter };
```

## Background Jobs

### **Resource Processing Jobs**
```javascript
// src/jobs/resource-processing.job.js
const Queue = require('bull');
const redisConfig = require('../config/redis.config');
const ResourceService = require('../services/resource.service');
const AIExtractionService = require('../services/ai-extraction.service');
const logger = require('../utils/logger');

const resourceProcessingQueue = new Queue('resource processing', redisConfig);

resourceProcessingQueue.process(async (job) => {
  const { resourceId, processingType } = job.data;
  
  try {
    logger.info(`Processing resource ${resourceId} with type ${processingType}`);
    
    // Update status to processing
    await ResourceService.updateProcessingStatus(resourceId, 'processing');
    
    // Download and process file
    const fileData = await ResourceService.downloadResource(resourceId);
    
    // Extract text based on file type
    const extractedText = await AIExtractionService.extractTextFromPDF(fileData.url);
    
    // Identify and extract questions
    const questions = await AIExtractionService.identifyQuestions(extractedText);
    
    // Classify and store questions
    const processedQuestions = await Promise.all(
      questions.map(async (question) => {
        const classified = await AIExtractionService.classifyQuestion(question.text);
        return ResourceService.storeExtractedQuestion(resourceId, question, classified);
      })
    );
    
    // Update resource status
    await ResourceService.updateProcessingStatus(resourceId, 'completed', processedQuestions.length);
    
    logger.info(`Successfully processed resource ${resourceId}`);
    return { success: true, questionsCount: processedQuestions.length };
    
  } catch (error) {
    logger.error(`Error processing resource ${resourceId}:`, error);
    await ResourceService.updateProcessingStatus(resourceId, 'failed', 0, error.message);
    throw error;
  }
});

module.exports = resourceProcessingQueue;
```

## Testing Implementation

### **Unit Tests**
```javascript
// tests/unit/services/auth.service.test.js
const AuthService = require('../../../src/services/auth.service');
const User = require('../../../src/models/User');
const jwt = require('jsonwebtoken');

jest.mock('../../../src/models/User');
jest.mock('jsonwebtoken');

describe('AuthService', () => {
  describe('register', () => {
    it('should register a new user successfully', async () => {
      // Mock user data
      const userData = {
        email: 'test@example.com',
        password: 'Password123!',
        firstName: 'Test',
        lastName: 'User',
        role: 'student'
      };

      // Mock User.create
      User.create.mockResolvedValue({ id: '1', ...userData });

      // Call service
      const result = await AuthService.register(userData);

      // Assertions
      expect(User.create).toHaveBeenCalledWith(userData);
      expect(result).toBeDefined();
    });

    it('should throw error for duplicate email', async () => {
      const userData = {
        email: 'existing@example.com',
        password: 'Password123!',
        firstName: 'Test',
        lastName: 'User',
        role: 'student'
      };

      User.create.mockRejectedValue(new Error('Email already exists'));

      await expect(AuthService.register(userData)).rejects.toThrow('Email already exists');
    });
  });

  describe('login', () => {
    it('should login user with valid credentials', async () => {
      const credentials = {
        email: 'test@example.com',
        password: 'Password123!'
      };

      const mockUser = {
        id: '1',
        email: credentials.email,
        password: 'hashedPassword',
        role: 'student'
      };

      User.findByEmail.mockResolvedValue(mockUser);
      jwt.sign.mockReturnValue('mockToken');

      const result = await AuthService.login(credentials);

      expect(result).toHaveProperty('token');
      expect(result).toHaveProperty('refreshToken');
    });
  });
});
```

### **Integration Tests**
```javascript
// tests/integration/auth.test.js
const request = require('supertest');
const app = require('../../src/app');
const { setupTestDB, cleanupTestDB } = require('../helpers/database');

describe('Auth Integration Tests', () => {
  beforeAll(async () => {
    await setupTestDB();
  });

  afterAll(async () => {
    await cleanupTestDB();
  });

  describe('POST /api/auth/register', () => {
    it('should register a new user', async () => {
      const userData = {
        email: 'test@example.com',
        password: 'Password123!',
        firstName: 'Test',
        lastName: 'User',
        role: 'student',
        schoolCode: 'TEST001'
      };

      const response = await request(app)
        .post('/api/auth/register')
        .send(userData)
        .expect(201);

      expect(response.body).toHaveProperty('token');
      expect(response.body.user.email).toBe(userData.email);
    });
  });
});
```

## Configuration Management

### **Environment Configuration**
```javascript
// src/config/app.config.js
const dotenv = require('dotenv');

dotenv.config();

const config = {
  app: {
    name: process.env.APP_NAME || 'Assessment Engine',
    port: parseInt(process.env.PORT) || 3000,
    env: process.env.NODE_ENV || 'development',
    url: process.env.APP_URL || 'http://localhost:3000'
  },
  
  database: {
    url: process.env.DATABASE_URL,
    ssl: process.env.NODE_ENV === 'production'
  },
  
  redis: {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT) || 6379,
    password: process.env.REDIS_PASSWORD,
    db: parseInt(process.env.REDIS_DB) || 0
  },
  
  jwt: {
    secret: process.env.JWT_SECRET,
    expiresIn: process.env.JWT_EXPIRES_IN || '15m',
    refreshSecret: process.env.JWT_REFRESH_SECRET,
    refreshExpiresIn: process.env.JWT_REFRESH_EXPIRES_IN || '7d'
  },
  
  aws: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
    region: process.env.AWS_REGION || 'us-east-1',
    s3Bucket: process.env.AWS_S3_BUCKET
  },
  
  email: {
    host: process.env.EMAIL_HOST,
    port: parseInt(process.env.EMAIL_PORT) || 587,
    user: process.env.EMAIL_USER,
    pass: process.env.EMAIL_PASS,
    from: process.env.EMAIL_FROM
  }
};

module.exports = config;
```

## Documentation

### **API Documentation with Swagger**
```javascript
// src/docs/swagger.js
const swaggerJsdoc = require('swagger-jsdoc');
const swaggerUi = require('swagger-ui-express');

const options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'Assessment Engine API',
      version: '1.0.0',
      description: 'Comprehensive assessment management system API',
    },
    servers: [
      {
        url: process.env.API_URL || 'http://localhost:3000',
        description: 'Development server',
      },
    ],
    components: {
      securitySchemes: {
        bearerAuth: {
          type: 'http',
          scheme: 'bearer',
          bearerFormat: 'JWT',
        },
      },
    },
  },
  apis: ['./src/routes/*.js'],
};

const specs = swaggerJsdoc(options);

module.exports = {
  serve: swaggerUi.serve,
  setup: swaggerUi.setup(specs),
};
```

## Deployment Requirements

### **Docker Configuration**
```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

RUN npx prisma generate
RUN npx prisma migrate deploy

EXPOSE 3000

CMD ["npm", "start"]
```

### **Docker Compose**
```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://user:password@postgres:5432/assessment_engine
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=assessment_engine
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## Performance Requirements

### **Caching Strategy**
- Redis for session storage
- Query result caching
- API response caching
- Static asset caching

### **Database Optimization**
- Connection pooling
- Query optimization
- Index optimization
- Read replicas

### **Load Balancing**
- Horizontal scaling
- Load balancer configuration
- Health checks
- Auto-scaling

## Monitoring & Logging

### **Logging Implementation**
```javascript
// src/utils/logger.js
const winston = require('winston');

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { service: 'assessment-engine' },
  transports: [
    new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
    new winston.transports.File({ filename: 'logs/combined.log' }),
  ],
});

if (process.env.NODE_ENV !== 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.simple()
  }));
}

module.exports = logger;
```

### **Health Checks**
```javascript
// src/routes/health.routes.js
const express = require('express');
const database = require('../utils/database');
const redis = require('../utils/redis');

const router = express.Router();

router.get('/health', async (req, res) => {
  const health = {
    status: 'ok',
    timestamp: new Date(),
    services: {
      database: await database.healthCheck(),
      redis: await redis.healthCheck()
    }
  };

  const isHealthy = Object.values(health.services).every(service => service.status === 'healthy');
  health.status = isHealthy ? 'ok' : 'error';

  res.status(isHealthy ? 200 : 503).json(health);
});

module.exports = router;
```

## Implementation Checklist

### **Phase 1: Core Infrastructure**
- [ ] Set up project structure
- [ ] Configure Prisma with PostgreSQL schema
- [ ] Implement authentication system
- [ ] Set up Redis for caching and sessions
- [ ] Configure environment variables

### **Phase 2: User Management**
- [ ] Implement user CRUD operations
- [ ] Add role-based permissions
- [ ] Create user profile management
- [ ] Implement bulk user operations

### **Phase 3: Test Management**
- [ ] Create test CRUD operations
- [ ] Implement test scheduling
- [ ] Add question management
- [ ] Create test taking functionality

### **Phase 4: Resource Management**
- [ ] Implement file upload system
- [ ] Create AI/ML integration
- [ ] Add resource processing jobs
- [ ] Implement question extraction

### **Phase 5: Advanced Features**
- [ ] Implement grading system
- [ ] Create analytics dashboard
- [ ] Add notification system
- [ ] Implement real-time features

### **Phase 6: Testing & Deployment**
- [ ] Write comprehensive tests
- [ ] Set up CI/CD pipeline
- [ ] Configure monitoring
- [ ] Deploy to production

## Key Requirements Summary

1. **Zero Errors**: All code must be error-free and production-ready
2. **Complete Implementation**: Follow implementation plan exactly
3. **Security First**: Implement all security measures
4. **Performance Optimized**: Include caching and optimization
5. **Well Documented**: Comprehensive API documentation
6. **Fully Tested**: Unit, integration, and e2e tests
7. **Production Ready**: Docker, monitoring, logging
8. **Scalable Architecture**: Handle 10,000+ concurrent users

Generate the complete backend implementation following these requirements exactly as specified in the implementation plan.
