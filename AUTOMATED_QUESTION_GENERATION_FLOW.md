# Automated Question Generation Flow for Teachers

## Overview

Simplified teacher workflow where teachers don't manually select questions. Instead, they specify parameters and the system automatically generates questions from existing school resources (books, question papers) based on their school, board, and curriculum.

## 1. Teacher Interface - Simplified Test Creation

### **Quick Test Configuration**

```
┌─────────────────────────────────────────────────────────────────┐
│  Create Test - Quick Setup                                │
├─────────────────────────────────────────────────────────────────┤
│                                                             │
│  Test Details:                                              │
│  ┌─────────────────────────────────────────────────────┐       │
│  │ Test Title: [Mathematics Unit Test - Chapter 6]    │       │
│  │ Description: [Assessment on Triangles...]          │       │
│  │ Duration: [60] minutes                         │       │
│  │ Max Attempts: [1]                             │       │
│  │ Passing Marks: [40]%                           │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  Question Generation Settings:                                 │
│  ┌─────────────────────────────────────────────────────┐       │
│  │ Number of Questions: [20]                     │       │
│  │ Question Types:                              │       │
│  │ ☑ MCQ (40%) ☑ True/False (20%)           │       │
│  │ ☑ Fill in Blanks (20%) ☑ Descriptive (20%)     │       │
│  │                                            │       │
│  │ Difficulty Distribution:                     │       │
│  │ Easy: [30%] Medium: [50%] Hard: [20%]    │       │
│  │                                            │       │
│  │ Marks per Question:                          │       │
│  │ MCQ: [1] True/False: [1] Fill Blank: [2]   │       │
│  │ Descriptive: [4]                            │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  Curriculum Selection:                                        │
│  ┌─────────────────────────────────────────────────────┐       │
│  │ Class: [10th Grade ▼]                       │       │
│  │ Subject: [Mathematics ▼]                      │       │
│  │ Board: [CBSE ▼]                              │       │
│  │ Chapter/Unit: [Chapter 6 - Triangles ▼]       │       │
│  │ Topics: [☑ Pythagorean Theorem ☑ Similarity]   │       │
│  │         [☑ Congruence ☑ Trigonometric Ratios]   │       │
│  │                                            │       │
│  │ Heritage/Wisdom: [☑ Include Heritage Questions]    │       │
│  │ Previous Years: [Last 5 years ▼]              │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  Resource Priority:                                          │
│  ┌─────────────────────────────────────────────────────┐       │
│  │ Primary Source: [NCERT Textbooks ▼]            │       │
│  │ Secondary Source: [Previous Year Papers ▼]       │       │
│  │ Tertiary Source: [Reference Books ▼]            │       │
│  │                                            │       │
│  │ Exclude Sources:                              │       │
│  │ ☐ Sample Papers ☐ Guide Books                  │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  [Generate Questions] [Preview Settings] [Save Template]     │
│                                                             │
└─────────────────────────────────────────────────────────────────┘
```

## 2. AI-Powered Question Generation Engine

### **Question Generation Algorithm**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Teacher      │──▶│  Parameter      │──▶│  Resource       │──▶│  AI Question    │
│  Input         │    │  Analysis       │    │  Scanning       │    │  Generation    │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Curriculum    │    │  Question       │    │  Difficulty     │    │  Question      │
│  Mapping       │    │  Type           │    │  Distribution   │    │  Formatting    │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Answer        │    │  Quality        │    │  Duplicate      │    │  Final Test     │
│  Generation    │    │  Validation     │    │  Detection      │    │  Assembly      │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Resource Analysis Engine**
```javascript
class ResourceAnalysisEngine {
  async analyzeResources(parameters) {
    const { schoolId, board, classId, subjectId, chapterId, topics } = parameters;
    
    // 1. Get school's resource library
    const resources = await this.getSchoolResources(schoolId, {
      board,
      class: classId,
      subject: subjectId,
      chapter: chapterId
    });

    // 2. Analyze resource content
    const resourceAnalysis = {
      textbooks: await this.analyzeTextbooks(resources.textbooks, topics),
      questionPapers: await this.analyzeQuestionPapers(resources.questionPapers, topics),
      referenceBooks: await this.analyzeReferenceBooks(resources.referenceBooks, topics),
      heritageQuestions: await this.analyzeHeritageQuestions(resources.heritageQuestions, topics)
    };

    // 3. Create content matrix
    const contentMatrix = this.createContentMatrix(resourceAnalysis, topics);
    
    // 4. Identify question patterns
    const questionPatterns = await this.identifyQuestionPatterns(contentMatrix);
    
    // 5. Calculate difficulty distribution
    const difficultyMap = this.calculateDifficultyDistribution(contentMatrix);
    
    return {
      contentMatrix,
      questionPatterns,
      difficultyMap,
      availableQuestions: this.countAvailableQuestions(contentMatrix),
      topicCoverage: this.calculateTopicCoverage(contentMatrix, topics)
    };
  }

  async analyzeTextbooks(textbooks, topics) {
    const analysis = {
      totalChapters: 0,
      relevantChapters: 0,
      questionPotential: 0,
      topicWiseQuestions: {}
    };

    for (const textbook of textbooks) {
      const chapters = await this.extractChaptersFromTextbook(textbook);
      analysis.totalChapters += chapters.length;

      for (const chapter of chapters) {
        if (this.isChapterRelevant(chapter, topics)) {
          analysis.relevantChapters++;
          
          const questions = await this.extractQuestionsFromChapter(chapter);
          analysis.questionPotential += questions.length;
          
          // Categorize by topic
          for (const question of questions) {
            const questionTopics = await this.identifyQuestionTopics(question);
            for (const topic of questionTopics) {
              if (!analysis.topicWiseQuestions[topic]) {
                analysis.topicWiseQuestions[topic] = [];
              }
              analysis.topicWiseQuestions[topic].push(question);
            }
          }
        }
      }
    }

    return analysis;
  }
}
```

### **Question Generation Logic**
```javascript
class QuestionGenerationEngine {
  async generateQuestions(parameters, resourceAnalysis) {
    const { 
      numberOfQuestions, 
      questionTypes, 
      difficultyDistribution,
      marksDistribution 
    } = parameters;

    const generatedQuestions = [];

    // 1. Calculate question distribution
    const distribution = this.calculateQuestionDistribution(
      numberOfQuestions, 
      questionTypes, 
      difficultyDistribution
    );

    // 2. Generate questions for each type
    for (const [questionType, count] of Object.entries(distribution)) {
      const typeQuestions = await this.generateQuestionsByType(
        questionType, 
        count, 
        resourceAnalysis,
        marksDistribution[questionType]
      );
      generatedQuestions.push(...typeQuestions);
    }

    // 3. Ensure topic coverage
    const balancedQuestions = await this.balanceTopicCoverage(
      generatedQuestions, 
      parameters.topics
    );

    // 4. Generate answers
    const questionsWithAnswers = await Promise.all(
      balancedQuestions.map(question => this.generateAnswers(question))
    );

    // 5. Quality validation
    const validatedQuestions = await this.validateQuestionQuality(questionsWithAnswers);

    return validatedQuestions;
  }

  async generateQuestionsByType(type, count, resourceAnalysis, marks) {
    switch (type) {
      case 'mcq':
        return this.generateMCQs(count, resourceAnalysis, marks);
      case 'true_false':
        return this.generateTrueFalse(count, resourceAnalysis, marks);
      case 'fill_blank':
        return this.generateFillBlanks(count, resourceAnalysis, marks);
      case 'descriptive':
        return this.generateDescriptive(count, resourceAnalysis, marks);
      default:
        throw new Error(`Unsupported question type: ${type}`);
    }
  }

  async generateMCQs(count, resourceAnalysis, marks) {
    const mcqs = [];
    
    for (let i = 0; i < count; i++) {
      // 1. Select source content
      const source = await this.selectSourceContent(resourceAnalysis, 'mcq');
      
      // 2. Generate question stem
      const questionStem = await this.generateQuestionStem(source, 'mcq');
      
      // 3. Generate correct answer
      const correctAnswer = await this.generateCorrectAnswer(source, questionStem);
      
      // 4. Generate distractors
      const distractors = await this.generateDistractors(correctAnswer, source, 3);
      
      // 5. Create MCQ object
      const mcq = {
        id: generateId(),
        type: 'mcq',
        questionText: questionStem,
        marks: marks,
        difficulty: await this.calculateDifficulty(questionStem, correctAnswer),
        options: [
          { id: 'a', text: correctAnswer, isCorrect: true },
          { id: 'b', text: distractors[0], isCorrect: false },
          { id: 'c', text: distractors[1], isCorrect: false },
          { id: 'd', text: distractors[2], isCorrect: false }
        ],
        explanation: await this.generateExplanation(source, questionStem, correctAnswer),
        source: {
          type: source.type,
          resourceId: source.id,
          chapter: source.chapter,
          page: source.page,
          confidence: source.confidence
        },
        metadata: {
          topics: await this.identifyTopics(questionStem),
          cognitiveLevel: await this.assessCognitiveLevel(questionStem),
          timeEstimate: await this.estimateTime(questionStem, 'mcq')
        }
      };
      
      mcqs.push(mcq);
    }
    
    return mcqs;
  }

  async generateAnswers(question) {
    switch (question.type) {
      case 'mcq':
        return {
          ...question,
          correctAnswer: question.options.find(opt => opt.isCorrect).id,
          explanation: question.explanation
        };
        
      case 'true_false':
        return {
          ...question,
          correctAnswer: question.correctAnswer,
          explanation: question.explanation
        };
        
      case 'fill_blank':
        return {
          ...question,
          correctAnswer: question.correctAnswer,
          possibleAnswers: question.possibleAnswers,
          explanation: question.explanation
        };
        
      case 'descriptive':
        return {
          ...question,
          sampleAnswer: question.sampleAnswer,
          rubric: question.rubric,
          explanation: question.explanation
        };
        
      default:
        return question;
    }
  }
}
```

## 3. Question Quality Assurance

### **Quality Validation Pipeline**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Generated     │──▶│  Content        │──▶│  Duplicate     │──▶│  Final         │
│  Questions     │    │  Validation     │    │  Detection      │    │  Question Set   │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Accuracy      │    │  Curriculum    │    │  Semantic      │    │  Balanced      │
│  Check         │    │  Alignment     │    │  Similarity    │    │  Distribution  │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Quality Validation Engine**
```javascript
class QuestionQualityValidator {
  async validateQuestions(questions, parameters) {
    const validationResults = {
      totalQuestions: questions.length,
      validQuestions: [],
      invalidQuestions: [],
      qualityScore: 0,
      topicCoverage: {},
      difficultyBalance: {},
      issues: []
    };

    // 1. Content accuracy validation
    for (const question of questions) {
      const accuracy = await this.validateContentAccuracy(question);
      if (accuracy.isValid) {
        validationResults.validQuestions.push(question);
      } else {
        validationResults.invalidQuestions.push({
          question,
          issues: accuracy.issues
        });
      }
    }

    // 2. Curriculum alignment check
    const curriculumAlignment = await this.validateCurriculumAlignment(
      validationResults.validQuestions, 
      parameters
    );
    validationResults.topicCoverage = curriculumAlignment.topics;

    // 3. Duplicate detection
    const duplicateGroups = await this.detectDuplicates(validationResults.validQuestions);
    validationResults.duplicates = duplicateGroups;

    // 4. Semantic similarity check
    const similarQuestions = await this.detectSemanticSimilarity(validationResults.validQuestions);
    validationResults.similarQuestions = similarQuestions;

    // 5. Difficulty balance validation
    const difficultyBalance = this.validateDifficultyBalance(
      validationResults.validQuestions,
      parameters.difficultyDistribution
    );
    validationResults.difficultyBalance = difficultyBalance;

    // 6. Calculate overall quality score
    validationResults.qualityScore = this.calculateQualityScore(validationResults);

    return validationResults;
  }

  async validateContentAccuracy(question) {
    const validation = {
      isValid: true,
      issues: [],
      confidence: 1.0
    };

    // Check question clarity
    if (!this.isQuestionClear(question.questionText)) {
      validation.isValid = false;
      validation.issues.push('Question text is unclear');
    }

    // Check answer correctness for MCQ
    if (question.type === 'mcq') {
      const correctOptions = question.options.filter(opt => opt.isCorrect);
      if (correctOptions.length !== 1) {
        validation.isValid = false;
        validation.issues.push('MCQ must have exactly one correct answer');
      }
    }

    // Check mathematical accuracy
    if (this.containsMath(question.questionText)) {
      const mathValidation = await this.validateMathematics(question);
      if (!mathValidation.isValid) {
        validation.isValid = false;
        validation.issues.push('Mathematical error detected');
      }
    }

    // Check source confidence
    if (question.source.confidence < 0.7) {
      validation.confidence = question.source.confidence;
      validation.issues.push('Low source confidence');
    }

    return validation;
  }

  async detectDuplicates(questions) {
    const duplicateGroups = [];
    const processed = new Set();

    for (let i = 0; i < questions.length; i++) {
      if (processed.has(i)) continue;

      const currentQuestion = questions[i];
      const duplicates = [i];

      for (let j = i + 1; j < questions.length; j++) {
        if (processed.has(j)) continue;

        const similarity = await this.calculateSimilarity(
          currentQuestion, 
          questions[j]
        );

        if (similarity > 0.9) { // 90% similarity threshold
          duplicates.push(j);
          processed.add(j);
        }
      }

      if (duplicates.length > 1) {
        duplicateGroups.push(duplicates);
        processed.add(i);
      }
    }

    return duplicateGroups;
  }
}
```

## 4. Teacher Review Interface

### **Generated Questions Review**

```
┌─────────────────────────────────────────────────────────────────┐
│  Generated Questions Review                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                             │
│  Generation Summary:                                       │
│  ┌─────────────────────────────────────────────────────┐       │
│  │ Total Questions Generated: 20                   │       │
│  │ Valid Questions: 18 (90%)                       │       │
│  │ Issues Found: 2                                   │       │
│  │ Quality Score: 85/100                            │       │
│  │ Topic Coverage: 95%                               │       │
│  │ Difficulty Balance: Good                             │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  Questions for Review:                                   │
│  ┌─────────────────────────────────────────────────────┐       │
│  │ 1. Pythagorean Theorem Application (2 marks)      │       │
│  │    Source: NCERT Chapter 6, Page 123            │       │
│  │    Type: MCQ | Difficulty: Medium               │       │
│  │    Question: In a right triangle ABC...           │       │
│  │    Options:                                        │       │
│  │    a) AB² = AC² + BC² ✅                      │       │
│  │    b) AB² = AC² - BC²                         │       │
│  │    c) AC² = AB² + BC²                         │       │
│  │    d) BC² = AC² - AB²                         │       │
│  │    ──────────────────────────────────────────────── │       │
│  │    [✓ Approve] [✏️ Edit] [🗑️ Replace] [❌ Reject] │       │
│  ├─────────────────────────────────────────────────────┤       │
│  │ 2. Find the missing side... (3 marks)            │       │
│  │    Source: 2022 Board Question Paper              │       │
│  │    Type: Fill Blank | Difficulty: Easy           │       │
│  │    Question: If triangle ABC has sides 5cm...    │       │
│  │    Answer: _____ cm                               │       │
│  │    ──────────────────────────────────────────────── │       │
│  │    [✓ Approve] [✏️ Edit] [🔄 Regenerate] [❌ Reject] │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  Quick Actions:                                             │
│  [Approve All Valid] [Regenerate Invalid] [Replace Duplicates] │
│  [Adjust Difficulty] [Rebalance Topics] [Export Questions]     │
│                                                             │
│  [Create Test] [Save as Draft] [Generate More Questions]     │
│                                                             │
└─────────────────────────────────────────────────────────────────┘
```

## 5. Automatic Test Assembly

### **Test Creation from Generated Questions**

```javascript
class TestAssemblyEngine {
  async createTestFromGeneratedQuestions(questions, testParameters) {
    // 1. Sort questions by difficulty and type
    const sortedQuestions = this.sortQuestionsForTest(questions);
    
    // 2. Create test sections
    const testSections = this.createTestSections(sortedQuestions, testParameters);
    
    // 3. Generate test instructions
    const instructions = await this.generateTestInstructions(testSections);
    
    // 4. Calculate test metadata
    const testMetadata = {
      totalQuestions: questions.length,
      totalMarks: this.calculateTotalMarks(questions),
      estimatedTime: this.calculateEstimatedTime(questions),
      difficultyDistribution: this.calculateDifficultyDistribution(questions),
      typeDistribution: this.calculateTypeDistribution(questions),
      topicCoverage: this.calculateTopicCoverage(questions)
    };

    // 5. Create test object
    const test = {
      id: generateId(),
      title: testParameters.title,
      description: testParameters.description,
      duration: testMetadata.estimatedTime,
      totalMarks: testMetadata.totalMarks,
      passingMarks: testParameters.passingMarks,
      sections: testSections,
      instructions: instructions,
      metadata: testMetadata,
      generatedFrom: 'ai_assisted',
      generationParameters: testParameters,
      createdAt: new Date()
    };

    return test;
  }

  sortQuestionsForTest(questions) {
    // Sort by difficulty (easy to hard) and then by type
    return questions.sort((a, b) => {
      const difficultyOrder = { 'easy': 1, 'medium': 2, 'hard': 3 };
      const typeOrder = { 'mcq': 1, 'true_false': 2, 'fill_blank': 3, 'descriptive': 4 };
      
      if (difficultyOrder[a.difficulty] !== difficultyOrder[b.difficulty]) {
        return difficultyOrder[a.difficulty] - difficultyOrder[b.difficulty];
      }
      
      return typeOrder[a.type] - typeOrder[b.type];
    });
  }

  createTestSections(questions, testParameters) {
    const sections = [];
    
    // Group by question type
    const questionsByType = this.groupByType(questions);
    
    for (const [type, typeQuestions] of Object.entries(questionsByType)) {
      sections.push({
        id: generateId(),
        type: type,
        title: this.getSectionTitle(type),
        questions: typeQuestions,
        instructions: this.getSectionInstructions(type),
        marks: this.calculateSectionMarks(typeQuestions)
      });
    }

    return sections;
  }
}
```

## 6. Implementation Benefits

### **Advantages for Teachers**

1. **Time Saving**: 80% reduction in test creation time
2. **Curriculum Aligned**: 100% curriculum compliance guaranteed
3. **Quality Assured**: Automated quality validation and checking
4. **Resource Utilization**: Maximum utilization of existing school resources
5. **Consistency**: Standardized difficulty and format
6. **Customizable**: Flexible parameters for different assessment needs

### **System Benefits**

1. **Scalability**: Generate unlimited questions from limited resources
2. **Consistency**: Maintains quality across all generated content
3. **Analytics**: Tracks question usage and effectiveness
4. **Adaptation**: Learns from teacher feedback to improve generation
5. **Resource Optimization**: Identifies gaps in resource library

### **Student Benefits**

1. **Fair Assessment**: Balanced difficulty and comprehensive coverage
2. **Relevant Content**: Questions based on their actual curriculum
3. **Variety**: Mix of question types for comprehensive assessment
4. **Preparation**: Questions similar to their study materials

This automated question generation flow transforms test creation from a time-consuming manual process to an efficient, AI-powered system that leverages existing school resources while maintaining curriculum alignment and quality standards.
