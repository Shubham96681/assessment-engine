# Non-AI Question Generation Methods

## Overview

Generate questions directly from textbook chapters using traditional extraction techniques, pattern matching, and educational methodologies without requiring AI/ML models.

## 1. Text Processing & Content Analysis

### **Chapter Content Extraction**
```javascript
class ChapterContentProcessor {
  async extractContent(pdfPath) {
    // 1. Extract text from PDF
    const text = await this.extractPDFText(pdfPath);
    
    // 2. Clean and structure content
    const cleanText = this.cleanText(text);
    const sections = this.identifySections(cleanText);
    
    // 3. Identify question-worthy content
    const questionSources = this.identifyQuestionSources(sections);
    
    return {
      rawText: cleanText,
      sections: sections,
      questionSources: questionSources
    };
  }

  identifySections(text) {
    const sections = [];
    
    // Look for section headers
    const sectionPatterns = [
      /^(\d+\.\d+)\s+(.+)/gm,           // 1.1 Section Name
      /^(Exercise\s+\d+)/gmi,              // Exercise 1
      /^(Examples?):/gmi,                  // Examples:
      /^(Key\s+Concepts?):/gmi,            // Key Concepts:
      /^(Summary):/gmi,                    // Summary:
      /^(Points\s+to\s+Remember):/gmi       // Points to Remember:
    ];
    
    sectionPatterns.forEach(pattern => {
      const matches = text.match(pattern);
      if (matches) {
        sections.push({
          type: this.getSectionType(pattern),
          content: matches
        });
      }
    });
    
    return sections;
  }

  identifyQuestionSources(sections) {
    const sources = [];
    
    sections.forEach(section => {
      switch (section.type) {
        case 'definitions':
          sources.push(...this.extractDefinitions(section.content));
          break;
        case 'examples':
          sources.push(...this.extractExamples(section.content));
          break;
        case 'exercises':
          sources.push(...this.extractExercises(section.content));
          break;
        case 'keyConcepts':
          sources.push(...this.extractKeyConcepts(section.content));
          break;
      }
    });
    
    return sources;
  }
}
```

## 2. Question Type Generation Strategies

### **Multiple Choice Questions (MCQ)**
```javascript
class MCQGenerator {
  generateFromDefinition(definition) {
    const question = {
      type: 'mcq',
      question: this.createDefinitionQuestion(definition),
      options: this.createMCQOptions(definition),
      correctAnswer: definition.term,
      explanation: definition.explanation
    };
    
    return question;
  }

  createDefinitionQuestion(definition) {
    const templates = [
      `What is the definition of ${definition.term}?`,
      `Which of the following best describes ${definition.term}?`,
      `${definition.term} can be defined as:`,
      `The term ${definition.term} refers to:`
    ];
    
    return templates[Math.floor(Math.random() * templates.length)];
  }

  createMCQOptions(definition) {
    const options = [definition.correctAnswer];
    
    // Generate distractors
    const distractors = this.generateDistractors(definition);
    options.push(...distractors);
    
    // Shuffle options
    return this.shuffleArray(options).map((option, index) => ({
      id: String.fromCharCode(65 + index), // A, B, C, D
      text: option,
      isCorrect: option === definition.correctAnswer
    }));
  }

  generateDistractors(definition) {
    const distractors = [];
    
    // 1. Similar sounding terms
    const similarTerms = this.findSimilarTerms(definition.term);
    distractors.push(...similarTerms.slice(0, 2));
    
    // 2. Common misconceptions
    const misconceptions = this.findCommonMisconceptions(definition.term);
    distractors.push(...misconceptions.slice(0, 1));
    
    return distractors;
  }
}
```

### **Fill in the Blanks**
```javascript
class FillBlankGenerator {
  generateFromSentence(sentence) {
    // Identify keywords to blank
    const keywords = this.identifyKeywords(sentence);
    
    if (keywords.length === 0) return null;
    
    const keyword = keywords[0]; // Use first keyword
    const blankedSentence = sentence.replace(keyword, '_____');
    
    return {
      type: 'fill_blank',
      question: blankedSentence,
      correctAnswer: keyword,
      possibleAnswers: this.getVariations(keyword),
      hints: this.generateHints(keyword)
    };
  }

  identifyKeywords(sentence) {
    // Look for important terms
    const patterns = [
      /\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b/g, // Capitalized terms
      /\b\d+(?:\.\d+)?\s*(?:kg|m|cm|km|°C|°F)\b/g, // Measurements
      /\b[a-z]+(?:tion|ment|ness|ity|ism)\b/g, // Abstract nouns
      /\b(?:is|are|was|were|has|have)\s+\w+\b/g // Verb phrases
    ];
    
    const keywords = [];
    patterns.forEach(pattern => {
      const matches = sentence.match(pattern);
      if (matches) keywords.push(...matches);
    });
    
    return keywords.filter(keyword => keyword.length > 3); // Filter short words
  }
}
```

### **True/False Questions**
```javascript
class TrueFalseGenerator {
  generateFromStatement(statement) {
    // Convert statement to question
    const question = this.createQuestion(statement);
    
    // Determine correct answer based on content
    const isTrue = this.evaluateStatement(statement);
    
    return {
      type: 'true_false',
      question: question,
      correctAnswer: isTrue,
      explanation: this.generateExplanation(statement, isTrue)
    };
  }

  createQuestion(statement) {
    const templates = [
      `State whether the following is true or false: ${statement}`,
      `True or False: ${statement}`,
      `Is the following statement correct? ${statement}`,
      `${statement} (True/False)`
    ];
    
    return templates[Math.floor(Math.random() * templates.length)];
  }
}
```

## 3. Subject-Specific Generators

### **Mathematics Questions**
```javascript
class MathQuestionGenerator {
  generateFromExample(example) {
    const questionTypes = [
      'similar_problem',
      'variation',
      'application',
      'reverse_problem'
    ];
    
    const type = questionTypes[Math.floor(Math.random() * questionTypes.length)];
    
    switch (type) {
      case 'similar_problem':
        return this.generateSimilarProblem(example);
      case 'variation':
        return this.generateVariation(example);
      case 'application':
        return this.generateApplication(example);
      case 'reverse_problem':
        return this.generateReverseProblem(example);
    }
  }

  generateSimilarProblem(example) {
    // Parse the original problem
    const problem = this.parseMathProblem(example);
    
    // Create similar problem with different numbers
    const newProblem = {
      ...problem,
      values: this.generateNewValues(problem.values),
      question: example.question.replace(/\d+/g, () => 
        this.generateRandomValue(problem.type)
      )
    };
    
    return {
      type: 'calculation',
      question: newProblem.question,
      solution: this.solveProblem(newProblem),
      steps: this.generateSolutionSteps(newProblem)
    };
  }

  generateApplication(example) {
    // Convert abstract problem to real-world scenario
    const scenarios = this.getRealWorldScenarios(example.type);
    const scenario = scenarios[Math.floor(Math.random() * scenarios.length)];
    
    return {
      type: 'word_problem',
      question: this.createWordProblem(example, scenario),
      solution: example.solution,
      context: scenario
    };
  }
}
```

### **Science Questions**
```javascript
class ScienceQuestionGenerator {
  generateFromConcept(concept) {
    const generators = [
      this.generateDefinitionQuestion,
      this.generateProcessQuestion,
      this.generateApplicationQuestion,
      this.generateComparisonQuestion
    ];
    
    const generator = generators[Math.floor(Math.random() * generators.length)];
    return generator.call(this, concept);
  }

  generateProcessQuestion(concept) {
    if (concept.type === 'process') {
      return {
        type: 'sequence',
        question: `Arrange the following steps of ${concept.name} in the correct order:`,
        options: this.shuffleArray(concept.steps),
        correctAnswer: concept.steps,
        explanation: concept.description
      };
    }
  }

  generateApplicationQuestion(concept) {
    const applications = this.findRealWorldApplications(concept);
    
    return {
      type: 'application',
      question: `Which of the following is a real-world application of ${concept.name}?`,
      options: this.createApplicationOptions(applications, concept),
      correctAnswer: applications[0],
      explanation: `${concept.name} is used in ${applications.join(', ')}`
    };
  }
}
```

## 4. Pattern-Based Extraction

### **Exercise and Problem Set Extraction**
```javascript
class ExerciseExtractor {
  extractExercises(text) {
    const exercises = [];
    
    // Look for exercise patterns
    const exercisePatterns = [
      /Exercise\s+(\d+)[\s\S]*?(?=Exercise\s+\d+|$)/gmi,
      /Q\.?\s*(\d+)[\.\)]\s*(.*?)(?=Q\.?\s*\d+|$)/gmi,
      /(\d+)\.\s*(.*?)(?=\d+\.|$)/gm
    ];
    
    exercisePatterns.forEach(pattern => {
      let match;
      while ((match = pattern.exec(text)) !== null) {
        exercises.push({
          number: match[1],
          content: match[2] || match[0],
          type: this.identifyExerciseType(match[0])
        });
      }
    });
    
    return exercises;
  }

  identifyExerciseType(content) {
    if (content.includes('prove') || content.includes('show that')) return 'proof';
    if (content.includes('calculate') || content.includes('find')) return 'calculation';
    if (content.includes('draw') || content.includes('sketch')) return 'diagram';
    if (content.includes('explain') || content.includes('describe')) return 'explanation';
    return 'general';
  }
}
```

### **Key Term Extraction**
```javascript
class KeyTermExtractor {
  extractKeyTerms(text) {
    const terms = [];
    
    // 1. Bold/italic terms (PDF formatting indicators)
    const boldTerms = text.match(/\*\*(.*?)\*\*/g) || [];
    const italicTerms = text.match(/\*(.*?)\*/g) || [];
    
    // 2. Definition patterns
    const definitionPattern = /(\w+(?:\s+\w+)*)\s+(?:is|are|refers to|means?)\s+(.+?)(?:\.|$)/gi;
    const definitions = text.match(definitionPattern) || [];
    
    // 3. Lists and bullet points
    const listPattern = /^[•\-\*]\s*(.+)$/gm;
    const listItems = text.match(listPattern) || [];
    
    // Process and deduplicate
    const allTerms = [...boldTerms, ...italicTerms, ...definitions, ...listItems];
    const uniqueTerms = [...new Set(allTerms)];
    
    uniqueTerms.forEach(term => {
      terms.push({
        term: this.cleanTerm(term),
        context: this.getContext(term, text),
        importance: this.calculateImportance(term, text)
      });
    });
    
    return terms.sort((a, b) => b.importance - a.importance);
  }

  calculateImportance(term, text) {
    let score = 0;
    
    // Frequency in text
    const frequency = (text.match(new RegExp(term, 'gi')) || []).length;
    score += frequency * 10;
    
    // Position in text (earlier = more important)
    const position = text.indexOf(term);
    score += Math.max(0, 100 - position / 100);
    
    // Length and complexity
    score += term.length * 2;
    
    // Formatting indicators
    if (term.includes('**') || term.includes('*')) score += 50;
    
    return score;
  }
}
```

## 5. Question Quality Control

### **Difficulty Assessment**
```javascript
class DifficultyAssessor {
  assessDifficulty(question) {
    let difficulty = 0;
    
    // 1. Vocabulary complexity
    const vocabScore = this.assessVocabulary(question.question);
    difficulty += vocabScore * 0.3;
    
    // 2. Sentence complexity
    const complexityScore = this.assessComplexity(question.question);
    difficulty += complexityScore * 0.3;
    
    // 3. Conceptual depth
    const conceptScore = this.assessConceptDepth(question);
    difficulty += conceptScore * 0.4;
    
    return this.categorizeDifficulty(difficulty);
  }

  assessVocabulary(text) {
    const words = text.split(/\s+/);
    const complexWords = words.filter(word => word.length > 8);
    const technicalTerms = words.filter(word => this.isTechnicalTerm(word));
    
    return (complexWords.length + technicalTerms.length * 2) / words.length;
  }

  categorizeDifficulty(score) {
    if (score < 0.3) return 'easy';
    if (score < 0.7) return 'medium';
    return 'hard';
  }
}
```

### **Validation and Filtering**
```javascript
class QuestionValidator {
  validateQuestion(question) {
    const issues = [];
    
    // 1. Check question clarity
    if (!this.isClear(question.question)) {
      issues.push('Question is unclear or ambiguous');
    }
    
    // 2. Check answer correctness
    if (!this.isAnswerCorrect(question)) {
      issues.push('Answer may be incorrect');
    }
    
    // 3. Check options quality (for MCQ)
    if (question.type === 'mcq') {
      const optionIssues = this.validateOptions(question.options);
      issues.push(...optionIssues);
    }
    
    // 4. Check educational value
    if (!this.hasEducationalValue(question)) {
      issues.push('Low educational value');
    }
    
    return {
      isValid: issues.length === 0,
      issues: issues,
      confidence: this.calculateConfidence(issues)
    };
  }

  isClear(question) {
    // Check for common clarity issues
    const unclearPatterns = [
      /\b(?:etc|approximately|about|roughly)\b/i,
      /\?\s*\?/,  // Multiple question marks
      /\.{3,}/,    // Excessive ellipsis
      /\b(?:maybe|perhaps|possibly)\b/i
    ];
    
    return !unclearPatterns.some(pattern => pattern.test(question));
  }
}
```

## 6. Implementation Example

### **Complete Question Generation Pipeline**
```javascript
class NonAIQuestionGenerator {
  async generateQuestionsFromChapter(pdfPath, targetCount = 20) {
    // 1. Extract and process content
    const processor = new ChapterContentProcessor();
    const content = await processor.extractContent(pdfPath);
    
    // 2. Initialize generators
    const generators = {
      mcq: new MCQGenerator(),
      fillBlank: new FillBlankGenerator(),
      trueFalse: new TrueFalseGenerator(),
      math: new MathQuestionGenerator(),
      science: new ScienceQuestionGenerator()
    };
    
    // 3. Generate questions from different sources
    const questions = [];
    
    // From definitions
    content.questionSources.definitions.forEach(def => {
      questions.push(generators.mcq.generateFromDefinition(def));
      questions.push(generators.fillBlank.generateFromSentence(def.sentence));
    });
    
    // From examples
    content.questionSources.examples.forEach(example => {
      if (this.isMathContent(example)) {
        questions.push(generators.math.generateFromExample(example));
      } else {
        questions.push(generators.trueFalse.generateFromStatement(example));
      }
    });
    
    // From exercises
    content.questionSources.exercises.forEach(exercise => {
      const question = this.convertExerciseToQuestion(exercise);
      if (question) questions.push(question);
    });
    
    // 4. Validate and filter questions
    const validator = new QuestionValidator();
    const validQuestions = questions.filter(q => {
      const validation = validator.validateQuestion(q);
      return validation.isValid && validation.confidence > 0.7;
    });
    
    // 5. Select best questions
    const selectedQuestions = this.selectBestQuestions(validQuestions, targetCount);
    
    return selectedQuestions;
  }

  selectBestQuestions(questions, targetCount) {
    // Sort by quality metrics
    questions.sort((a, b) => {
      const scoreA = this.calculateQualityScore(a);
      const scoreB = this.calculateQualityScore(b);
      return scoreB - scoreA;
    });
    
    // Ensure diverse question types
    const selected = [];
    const typeCounts = { mcq: 0, fill_blank: 0, true_false: 0 };
    
    for (const question of questions) {
      if (selected.length >= targetCount) break;
      
      // Balance question types
      if (typeCounts[question.type] < targetCount / 3) {
        selected.push(question);
        typeCounts[question.type]++;
      }
    }
    
    return selected;
  }

  calculateQualityScore(question) {
    let score = 0;
    
    // Educational value (40%)
    score += this.assessEducationalValue(question) * 0.4;
    
    // Clarity (30%)
    score += this.assessClarity(question) * 0.3;
    
    // Difficulty appropriateness (20%)
    score += this.assessDifficulty(question) * 0.2;
    
    // Uniqueness (10%)
    score += this.assessUniqueness(question) * 0.1;
    
    return score;
  }
}
```

## 7. Benefits of Non-AI Approach

### **Advantages:**
- **No API Costs**: Completely free to operate
- **Fast Processing**: Local processing, no network latency
- **Predictable Results**: Consistent output quality
- **Full Control**: Complete customization of question types
- **Privacy**: No external data sharing
- **Reliability**: Works offline, no service dependencies

### **Quality Assurance:**
- **Curriculum Aligned**: Directly from textbook content
- **Accurate**: Based on actual source material
- **Consistent**: Standardized generation patterns
- **Validated**: Built-in quality checks

### **Scalability:**
- **Batch Processing**: Generate hundreds of questions quickly
- **Multi-format Support**: PDF, DOC, TXT files
- **Subject Coverage**: Works for all academic subjects
- **Grade Level Adaptation**: Adjustable complexity

This non-AI approach provides a robust, cost-effective alternative for generating quality questions directly from textbook chapters while maintaining educational standards and curriculum alignment.
