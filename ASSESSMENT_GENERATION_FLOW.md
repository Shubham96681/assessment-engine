# Assessment Generation Flow

## Overview

Complete assessment generation workflow from test creation to student completion, including all user interactions, system processes, and data flows.

## 1. Test Creation Flow

### **Teacher Test Creation Workflow**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Teacher      │──▶│  Test Creation  │──▶│  Question      │──▶│  Test          │
│   Dashboard     │    │  Interface      │    │  Selection     │    │  Configuration │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Test Template  │    │  Question Bank  │    │  Resource      │    │  AI Generated  │
│  Selection      │    │  Search         │    │  Upload        │    │  Questions     │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
```

#### **Step 1: Test Template Selection**
- **Choose Template**: New test, from template, duplicate existing
- **Basic Information**: Title, description, instructions
- **Test Settings**: Duration, attempts allowed, randomization
- **Grading Settings**: Negative marking, passing criteria

#### **Step 2: Question Selection**
```
┌─────────────────────────────────────────────────────────────────┐
│  Question Selection Interface                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                             │
│  Sources: ☑ Manual  ☑ Books  ☑ Question Papers  ☑ AI  │
│                                                             │
│  Filters:                                                    │
│  ┌─────────────────────────────────────────────────────┐       │
│  │ Subject: [Mathematics ▼]                    │       │
│  │ Class: [10th Grade ▼]                       │       │
│  │ Difficulty: [Medium ▼]                        │       │
│  │ Question Type: [All Types ▼]                 │       │
│  │ Topics: [Algebra, Geometry, Trigonometry ▼]   │       │
│  │ Marks Range: [1-5 marks]                     │       │
│  │ Time Limit: [30-60 minutes]                   │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  Available Questions: 1,234                               │
│  ┌─────────────────────────────────────────────────────┐       │
│  │ ☑ Q1: Pythagorean Theorem (2 marks)          │       │
│  │    Source: NCERT Class 10, Chapter 6           │       │
│  │    Difficulty: Medium | Type: MCQ               │       │
│  │    Confidence: 95% | Usage: 234 times        │       │
│  ├─────────────────────────────────────────────────────┤       │
│  │ ☑ Q2: Solve for x: 2x + 5 = 15 (3 marks)   │       │
│  │    Source: 2023 Board Exam                     │       │
│  │    Difficulty: Easy | Type: Descriptive        │       │
│  │    Confidence: 88% | Usage: 156 times        │       │
│  ├─────────────────────────────────────────────────────┤       │
│  │ ☐ Q3: Find area of triangle... (4 marks)       │       │
│  │    Source: AI Generated                        │       │
│  │    Difficulty: Hard | Type: Problem Solving     │       │
│  │    Confidence: 92% | Usage: 89 times         │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  Selected: 2 questions | Total Marks: 5 | Est. Time: 8min │
│  [Add More] [Auto-Select 10 Questions] [Preview Test]     │
│                                                             │
└─────────────────────────────────────────────────────────────────┘
```

#### **Step 3: Test Configuration**
```
┌─────────────────────────────────────────────────────────────────┐
│  Test Configuration                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                             │
│  Basic Settings:                                            │
│  ┌─────────────────────────────────────────────────────┐       │
│  │ Test Title: [Mathematics Mid-Term Exam]        │       │
│  │ Description: [Comprehensive assessment...]       │       │
│  │ Instructions: [Read all questions carefully...]   │       │
│  │ Duration: [60] minutes                       │       │
│  │ Max Attempts: [1]                             │       │
│  │ Randomize Questions: ☑                       │       │
│  │ Randomize Options: ☑                         │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  Scheduling:                                                │
│  ┌─────────────────────────────────────────────────────┐       │
│  │ Start Date: [2024-03-15 09:00 AM]          │       │
│  │ End Date: [2024-03-15 11:00 AM]            │       │
│  │ Result Date: [2024-03-16 09:00 AM]           │       │
│  │ Publish Results: ☑ Immediately                  │       │
│  │ Allow Late Submission: ☐                       │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  Grading Settings:                                           │
│  ┌─────────────────────────────────────────────────────┐       │
│  │ Passing Marks: [40]%                        │       │
│  │ Negative Marking: ☐                          │       │
│  │ Show Correct Answers: ☐                        │       │
│  │ Allow Review: ☑                              │       │
│  │ Auto-Grade Objective: ☑                      │       │
│  │ Manual Grade Subjective: ☑                     │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  [Save as Draft] [Preview] [Publish Test]                │
│                                                             │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Test Publishing & Scheduling

### **Publication Workflow**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Test Config   │──▶│  Validation     │──▶│  Scheduling    │──▶│  Publishing     │
│  Complete      │    │  Check          │    │  Engine        │    │  Service       │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Test Rules     │    │  Conflict       │    │  Notification  │    │  Student       │
│  Validation    │    │  Detection      │    │  Queue         │    │  Instances     │
│                │    │                │    │                │    │  Creation      │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
```

#### **Validation Process**
1. **Test Completeness Check**
   - Minimum questions required
   - Total marks within limits
   - Time allocation reasonable
   - Question distribution balanced

2. **Conflict Detection**
   - Student schedule conflicts
   - Resource availability
   - Teacher availability
   - System capacity check

3. **Permission Validation**
   - Teacher's subject access
   - Class assignment verification
   - School policy compliance
   - Subscription limits

#### **Scheduling Engine**
```javascript
// Test Scheduling Algorithm
class TestSchedulingService {
  async scheduleTest(testData, teacherId) {
    // 1. Validate test configuration
    const validation = await this.validateTestConfig(testData);
    if (!validation.isValid) {
      throw new ValidationError(validation.errors);
    }

    // 2. Check for conflicts
    const conflicts = await this.detectConflicts(testData);
    if (conflicts.length > 0) {
      return { conflicts, suggestions: await this.suggestAlternatives(testData) };
    }

    // 3. Calculate resource requirements
    const resources = await this.calculateResourceNeeds(testData);

    // 4. Schedule test
    const scheduledTest = await this.createScheduledTest(testData, resources);

    // 5. Create student instances
    await this.createStudentInstances(scheduledTest);

    // 6. Queue notifications
    await this.queueNotifications(scheduledTest);

    return scheduledTest;
  }

  async detectConflicts(testData) {
    const conflicts = [];

    // Check student schedule conflicts
    const studentConflicts = await this.checkStudentScheduleConflicts(testData);
    if (studentConflicts.length > 0) {
      conflicts.push({ type: 'student_schedule', data: studentConflicts });
    }

    // Check teacher availability
    const teacherConflicts = await this.checkTeacherAvailability(testData);
    if (teacherConflicts.length > 0) {
      conflicts.push({ type: 'teacher_availability', data: teacherConflicts });
    }

    // Check system capacity
    const systemLoad = await this.checkSystemLoad(testData);
    if (systemLoad > 0.8) {
      conflicts.push({ type: 'system_capacity', data: { currentLoad: systemLoad } });
    }

    return conflicts;
  }
}
```

## 3. Student Test Taking Flow

### **Test Access and Start**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Student      │──▶│  Test          │──▶│  Authentication│──▶│  Test          │
│   Dashboard    │    │  Selection      │    │  & Validation  │    │  Instance      │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Available     │    │  Security       │    │  Question      │    │  Timer &       │
│  Tests List     │    │  Checks         │    │  Generation    │    │  Progress      │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
```

#### **Student Test Interface**
```
┌─────────────────────────────────────────────────────────────────┐
│  Mathematics Mid-Term Exam - Student View                    │
├─────────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐       │
│  │  Timer: 45:23 | Progress: 3/10 (30%)        │       │
│  │  [Save Progress] [Submit Test] [Help]           │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐       │
│  │  Question 3 of 10 (4 marks)                   │       │
│  │  ──────────────────────────────────────────────── │       │
│  │  Find the area of a triangle with sides 5cm,      │       │
│  │  12cm, and 13cm. Show your work.             │       │
│  │  ──────────────────────────────────────────────── │       │
│  │  [Drawing Canvas] [Formula Reference]           │       │
│  │  ──────────────────────────────────────────────── │       │
│  │  Answer: [Rich Text Editor]                     │       │
│  │         [Upload Image] [Drawing Tools]          │       │
│  │  ──────────────────────────────────────────────── │       │
│  │  [Previous Question] [Save & Next] [Mark for Review]│       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐       │
│  │  Question Panel:                                    │       │
│  │  ● Q1 (2m)  ● Q2 (3m)  ○ Q3 (4m)       │       │
│  │  ○ Q4 (2m)  ○ Q5 (3m)  ○ Q6 (5m)       │       │
│  │  ● Q7 (2m)  ○ Q8 (4m)  ○ Q9 (3m)       │       │
│  │  ○ Q10 (5m)                                     │       │
│  │                                                   │       │
│  │  [Answered: 3] [Marked: 0] [Remaining: 7]     │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
└─────────────────────────────────────────────────────────────────┘
```

### **Real-time Features**

#### **Auto-Save Mechanism**
```javascript
// Auto-save implementation
class TestAutoSaveService {
  constructor(testInstanceId) {
    this.testInstanceId = testInstanceId;
    this.saveInterval = 30000; // 30 seconds
    this.pendingSave = false;
    this.lastSaveTime = null;
  }

  startAutoSave() {
    this.saveTimer = setInterval(async () => {
      if (!this.pendingSave) {
        await this.saveProgress();
      }
    }, this.saveInterval);
  }

  async saveProgress() {
    try {
      this.pendingSave = true;
      const currentAnswers = this.getCurrentAnswers();
      const progress = this.calculateProgress();

      await this.saveToDatabase(currentAnswers, progress);
      this.lastSaveTime = new Date();
      
      // Update UI
      this.updateSaveStatus('Saved');
      
    } catch (error) {
      this.updateSaveStatus('Save Failed');
      console.error('Auto-save failed:', error);
    } finally {
      this.pendingSave = false;
    }
  }

  async saveToDatabase(answers, progress) {
    await TestAttempt.updateAnswers(this.testInstanceId, {
      answers: answers,
      progress: progress,
      lastSavedAt: new Date(),
      timeSpent: this.calculateTimeSpent()
    });
  }
}
```

#### **Anti-Cheating Measures**
```javascript
// Anti-cheating implementation
class AntiCheatingService {
  constructor(testInstanceId) {
    this.testInstanceId = testInstanceId;
    this.suspiciousActivities = [];
    this.tabSwitchCount = 0;
    this.copyAttempts = 0;
    this.timePatterns = [];
  }

  monitorTabSwitch() {
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.tabSwitchCount++;
        this.logSuspiciousActivity('tab_switch', {
          count: this.tabSwitchCount,
          timestamp: new Date()
        });

        if (this.tabSwitchCount > 3) {
          this.triggerWarning('Multiple tab switches detected');
        }
      }
    });
  }

  monitorCopyPaste() {
    document.addEventListener('copy', (e) => {
      this.copyAttempts++;
      this.logSuspiciousActivity('copy_attempt', {
        content: e.clipboardData.getData('text'),
        timestamp: new Date()
      });
    });

    document.addEventListener('paste', (e) => {
      this.logSuspiciousActivity('paste_attempt', {
        content: e.clipboardData.getData('text'),
        timestamp: new Date()
      });
      
      // Prevent paste in certain question types
      if (this.isSecureQuestion()) {
        e.preventDefault();
        this.triggerWarning('Paste not allowed in this question');
      }
    });
  }

  monitorTimePatterns() {
    setInterval(() => {
      const currentTime = new Date();
      const timeSpent = this.calculateTimeSpent();
      
      // Detect unusually fast answering
      if (timeSpent < this.getExpectedTime()) {
        this.logSuspiciousActivity('unusual_time_pattern', {
          actualTime: timeSpent,
          expectedTime: this.getExpectedTime(),
          timestamp: currentTime
        });
      }
    }, 5000); // Check every 5 seconds
  }
}
```

## 4. Test Submission & Grading

### **Submission Process**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Student       │──▶│  Answer        │──▶│  Validation    │──▶│  Submission     │
│  Submits Test  │    │  Collection     │    │  & Scoring    │    │  Processing    │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Final Save    │    │  Objective     │    │  Subjective    │    │  Grade         │
│  & Validation  │    │  Auto-Grading   │    │  Question      │    │  Calculation   │
│                │    │                │    │  Queue         │    │                │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
```

#### **Auto-Grading Engine**
```javascript
// Auto-grading implementation
class AutoGradingService {
  async gradeTestAttempt(testAttemptId) {
    const testAttempt = await TestAttempt.findById(testAttemptId);
    const test = await Test.findById(testAttempt.testId);
    
    const gradingResults = {
      totalMarks: 0,
      obtainedMarks: 0,
      questionResults: [],
      percentage: 0,
      grade: null,
      passed: false
    };

    // Grade each question
    for (const question of test.questions) {
      const answer = testAttempt.answers[question.id];
      const result = await this.gradeQuestion(question, answer);
      
      gradingResults.questionResults.push(result);
      gradingResults.totalMarks += question.marks;
      gradingResults.obtainedMarks += result.obtainedMarks;
    }

    // Calculate final results
    gradingResults.percentage = (gradingResults.obtainedMarks / gradingResults.totalMarks) * 100;
    gradingResults.grade = this.calculateGrade(gradingResults.percentage);
    gradingResults.passed = gradingResults.percentage >= test.passingMarks;

    // Save results
    await TestAttempt.updateResults(testAttemptId, gradingResults);

    return gradingResults;
  }

  async gradeQuestion(question, answer) {
    switch (question.questionType) {
      case 'mcq':
        return this.gradeMCQ(question, answer);
      case 'true_false':
        return this.gradeTrueFalse(question, answer);
      case 'fill_blank':
        return this.gradeFillBlank(question, answer);
      case 'descriptive':
        return this.queueForManualGrading(question, answer);
      case 'coding':
        return this.gradeCodingQuestion(question, answer);
      default:
        return { obtainedMarks: 0, feedback: 'Unknown question type' };
    }
  }

  gradeMCQ(question, answer) {
    const correctOption = question.options.find(opt => opt.isCorrect);
    const selectedOption = question.options.find(opt => opt.id === answer.selectedOptionId);
    
    const isCorrect = selectedOption?.id === correctOption?.id;
    const obtainedMarks = isCorrect ? question.marks : (question.negativeMarks || 0);

    return {
      questionId: question.id,
      questionType: 'mcq',
      isCorrect,
      obtainedMarks,
      correctAnswer: correctOption.id,
      studentAnswer: answer.selectedOptionId,
      timeSpent: answer.timeSpent,
      feedback: isCorrect ? 'Correct!' : `Incorrect. Correct answer: ${correctOption.text}`
    };
  }
}
```

### **Manual Grading Interface**
```
┌─────────────────────────────────────────────────────────────────┐
│  Teacher Grading Dashboard                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                             │
│  Pending Grading: 23 questions | Assigned to Me: 8         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐       │
│  │  Question: "Explain Pythagorean theorem..."      │       │
│  │  Student: John Doe | Class: 10A | Marks: 4      │       │
│  │  ──────────────────────────────────────────────── │       │
│  │  Student Answer:                                    │       │
│  │  "The Pythagorean theorem states that in a right..."   │       │
│  │  ──────────────────────────────────────────────── │       │
│  │  Rubric:                                          │       │
│  │  ┌─────────────────────────────────────────────┐   │       │
│  │  │ Explanation (2 marks):                      │   │       │
│  │  │ ☐ 0 pts ☐ 1 pts ☑ 2 pts              │   │       │
│  │  │ Formula Application (1 mark):               │   │       │
│  │  │ ☐ 0 pts ☑ 1 pts                         │   │       │
│  │  │ Example (1 mark):                          │   │       │
│  │  │ ☐ 0 pts ☐ 1 pts                         │   │       │
│  │  └─────────────────────────────────────────────┘   │       │
│  │  ──────────────────────────────────────────────── │       │
│  │  Total: [3] / 4 marks                       │       │
│  │  Feedback: [Rich Text Editor]                   │       │
│  │  ──────────────────────────────────────────────── │       │
│  │  [Save Grade] [Next Question] [Previous]       │       │
│  │  [Auto-Save: On]                              │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  Quick Actions:                                            │
│  [Grade All Similar] [Use Previous Rubric] [AI Assist]    │
│                                                             │
└─────────────────────────────────────────────────────────────────┘
```

## 5. Results & Analytics

### **Result Generation**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Grade         │──▶│  Result        │──▶│  Analytics     │──▶│  Report        │
│  Calculation   │    │  Compilation    │    │  Processing    │    │  Generation    │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Individual     │    │  Class-wise     │    │  Question      │    │  Performance   │
│  Reports       │    │  Analytics     │    │  Analysis      │    │  Trends       │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Student Result Interface**
```
┌─────────────────────────────────────────────────────────────────┐
│  Test Results - Mathematics Mid-Term Exam                  │
├─────────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐       │
│  │  Overall Performance:                               │       │
│  │  ┌─────────────────────────────────────────────┐   │       │
│  │  │ Total Marks: 50 | Obtained: 38/50       │   │       │
│  │  │ Percentage: 76% | Grade: A+               │   │       │
│  │  │ Status: PASSED ✅                          │   │       │
│  │  │ Rank: 5/45 students                         │   │       │
│  │  │ Time Taken: 48 minutes                       │   │       │
│  │  └─────────────────────────────────────────────┘   │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐       │
│  │  Question-wise Performance:                       │       │
│  │  ┌─────────────────────────────────────────────┐   │       │
│  │  │ Q1: Pythagorean Theorem (2/2) ✅         │   │       │
│  │  │ Q2: Solve for x (3/3) ✅                │   │       │
│  │  │ Q3: Triangle Area (3/4) ⚠️                │   │       │
│  │  │ Q4: Trigonometry (4/4) ✅                │   │       │
│  │  │ Q5: Word Problem (2/3) ⚠️                │   │       │
│  │  │ [View Detailed Answers]                     │   │       │
│  │  └─────────────────────────────────────────────┘   │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐       │
│  │  Topic-wise Analysis:                             │       │
│  │  ┌─────────────────────────────────────────────┐   │       │
│  │  │ Algebra: 85% (17/20)                     │   │       │
│  │  │ Geometry: 70% (14/20)                     │   │       │
│  │  │ Trigonometry: 75% (6/8)                    │   │       │
│  │  │ Word Problems: 67% (4/6)                    │   │       │
│  │  └─────────────────────────────────────────────┘   │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  Actions:                                                   │
│  [Download Report] [View Solutions] [Compare with Class]     │
│  [Request Re-evaluation] [Share Results]                 │
│                                                             │
└─────────────────────────────────────────────────────────────────┘
```

### **Teacher Analytics Dashboard**
```
┌─────────────────────────────────────────────────────────────────┐
│  Class 10A - Mathematics Performance Analytics              │
├─────────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐       │
│  │  Overall Class Performance:                       │       │
│  │  ┌─────────────────────────────────────────────┐   │       │
│  │  │ Average Score: 68.5%                        │   │       │
│  │  │ Highest Score: 95% (Student A)               │   │       │
│  │  │ Lowest Score: 32% (Student B)                │   │       │
│  │  │ Pass Rate: 78% (35/45 students)            │   │       │
│  │  │ Average Time: 52 minutes                    │   │       │
│  │  └─────────────────────────────────────────────┘   │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐       │
│  │  Performance Distribution:                        │       │
│  │  ┌─────────────────────────────────────────────┐   │       │
│  │  │ Grade A+: 5 students (11%)                 │   │       │
│  │  │ Grade A: 8 students (18%)                   │   │       │
│  │  │ Grade B: 12 students (27%)                  │   │       │
│  │  │ Grade C: 15 students (33%)                  │   │       │
│  │  │ Grade D: 3 students (7%)                   │   │       │
│  │  │ Grade F: 2 students (4%)                   │   │       │
│  │  └─────────────────────────────────────────────┘   │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐       │
│  │  Question Analysis:                              │       │
│  │  ┌─────────────────────────────────────────────┐   │       │
│  │  │ Most Difficult: Q3 (Triangle Area)         │   │       │
│  │  │    Correct Rate: 42% (19/45)              │   │       │
│  │  │ Average Time: 8.5 minutes                 │   │       │
│  │  │                                            │   │       │
│  │  │ Easiest: Q1 (Pythagorean Theorem)          │   │       │
│  │  │    Correct Rate: 89% (40/45)              │   │       │
│  │  │ Average Time: 2.3 minutes                 │   │       │
│  │  └─────────────────────────────────────────────┘   │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                             │
│  Actions:                                                   │
│  [Export Results] [Generate Report] [Identify Weak Areas]   │
│  [Parent Notifications] [Individual Student Reports]         │
│                                                             │
└─────────────────────────────────────────────────────────────────┘
```

## 6. Notification System

### **Notification Flow**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Event         │──▶│  Trigger       │──▶│  Notification  │──▶│  Delivery      │
│  Occurs       │    │  Detection      │    │  Generation    │    │  Channels      │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Test          │    │  Email          │    │  In-App        │    │  SMS           │
│  Scheduled     │    │  Notifications  │    │  Notifications  │    │  Notifications  │
│  Results       │    │                │    │                │    │                │
│  Deadlines     │    │                │    │                │    │                │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
```

#### **Notification Templates**
```javascript
// Notification templates
const NotificationTemplates = {
  TEST_SCHEDULED: {
    email: {
      subject: 'Test Scheduled: {{testTitle}}',
      body: `
        Dear {{studentName}},
        
        You have a test scheduled:
        Test: {{testTitle}}
        Subject: {{subject}}
        Date: {{startDate}}
        Duration: {{duration}} minutes
        Link: {{testLink}}
        
        Best regards,
        {{teacherName}}
      `
    },
    sms: `Test scheduled: {{testTitle}} on {{startDate}}`,
    inApp: {
      title: 'Test Scheduled',
      message: '{{testTitle}} is scheduled for {{startDate}}',
      action: 'View Test',
      actionUrl: '{{testLink}}'
    }
  },

  TEST_RESULTS_PUBLISHED: {
    email: {
      subject: 'Test Results Available: {{testTitle}}',
      body: `
        Dear {{studentName}},
        
        Your test results are ready:
        Test: {{testTitle}}
        Score: {{percentage}}% ({{grade}})
        Status: {{passed ? 'PASSED' : 'FAILED'}}
        
        View detailed results: {{resultsLink}}
        
        Best regards,
        {{schoolName}}
      `
    },
    inApp: {
      title: 'Results Available',
      message: 'Your results for {{testTitle}} are ready',
      action: 'View Results',
      actionUrl: '{{resultsLink}}'
    }
  }
};
```

## 7. Error Handling & Recovery

### **Error Recovery Flows**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Error         │──▶│  Detection      │──▶│  Classification│──▶│  Recovery      │
│  Occurrence    │    │  & Logging      │    │  & Priority    │    │  Strategies    │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Auto-Save     │    │  Graceful      │    │  User          │    │  Admin         │
│  Recovery      │    │  Degradation    │    │  Notification  │    │  Alerting      │
│                │    │                │    │                │    │                │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
```

#### **Test Session Recovery**
```javascript
// Session recovery implementation
class TestSessionRecovery {
  async recoverSession(studentId, testInstanceId) {
    try {
      // Check for incomplete session
      const session = await this.findIncompleteSession(studentId, testInstanceId);
      
      if (!session) {
        return { success: false, message: 'No session to recover' };
      }

      // Validate session integrity
      const integrity = await this.validateSessionIntegrity(session);
      if (!integrity.isValid) {
        return { 
          success: false, 
          message: 'Session corrupted',
          options: ['restart_test', 'contact_support']
        };
      }

      // Calculate remaining time
      const remainingTime = this.calculateRemainingTime(session);
      
      if (remainingTime <= 0) {
        // Auto-submit if time expired
        await this.autoSubmitTest(session);
        return { 
          success: true, 
          message: 'Test auto-submitted due to time expiry',
          action: 'view_results'
        };
      }

      // Restore session
      return {
        success: true,
        sessionData: {
          answers: session.answers,
          currentQuestion: session.currentQuestion,
          timeRemaining: remainingTime,
          progress: session.progress
        },
        message: 'Session recovered successfully'
      };

    } catch (error) {
      console.error('Session recovery failed:', error);
      return { 
        success: false, 
        message: 'Recovery failed',
        options: ['restart_test', 'contact_support']
      };
    }
  }
}
```

## 8. Performance Optimization

### **Caching Strategy**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Question      │──▶│  Redis Cache   │──▶│  CDN Cache     │──▶│  Browser       │
│  Cache         │    │  (Questions,   │    │  (Static       │    │  Cache        │
│                │    │  Results,      │    │  Assets)       │    │                │
└─────────────────┘    │  Sessions)     │    │                │    │                │
         │              └──────────────────┘    └─────────────────┘    └─────────────────┘
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Database      │    │  Load          │    │  Content       │    │  Offline       │
│  Query        │    │  Balancer      │    │  Delivery      │    │  Support       │
│  Optimization │    │                │    │  Network       │    │                │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
```

This comprehensive assessment generation flow covers all aspects from test creation to result delivery, ensuring a smooth, reliable, and feature-rich experience for all users in the assessment system.
