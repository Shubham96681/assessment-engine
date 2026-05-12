# Wolfram Alpha Integration Implementation Plan

## Overview

Integrate Wolfram Alpha computational knowledge engine into the assessment engine to enhance mathematical question generation, answer validation, and step-by-step solution generation.

## 1. Integration Architecture

### **System Architecture**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Assessment     │──▶│  Wolfram Alpha   │──▶│  Response       │──▶│  Question      │
│  Engine         │    │  API Service    │    │  Processing    │    │  Generation    │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Question      │    │  Computational  │    │  Answer         │    │  Step-by-Step  │
│  Validation    │    │  Queries        │    │  Verification   │    │  Solutions     │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Formula        │    │  Graph          │    │  Unit          │    │  Enhanced      │
│  Generation     │    │  Generation     │    │  Conversions    │    │  Learning      │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
```

### **API Integration Setup**

```javascript
// src/services/wolfram-alpha.service.js
const axios = require('axios');
const config = require('../config/wolfram-alpha.config');

class WolframAlphaService {
  constructor() {
    this.appId = config.wolframAlpha.appId;
    this.baseUrl = config.wolframAlpha.baseUrl;
    this.maxRetries = 3;
    this.rateLimit = 100; // requests per minute
  }

  async queryWolframAlpha(input, options = {}) {
    try {
      const params = {
        appid: this.appId,
        input: input,
        output: 'json',
        format: 'plaintext,image',
        ...options
      };

      const response = await axios.get(this.baseUrl, { params });
      
      if (response.data.queryresult.success === false) {
        throw new Error(`Wolfram Alpha query failed: ${response.data.queryresult.error}`);
      }

      return this.parseResponse(response.data.queryresult);
    } catch (error) {
      console.error('Wolfram Alpha API error:', error);
      throw new Error(`Wolfram Alpha integration failed: ${error.message}`);
    }
  }

  parseResponse(queryResult) {
    const pods = queryResult.pods || [];
    const result = {
      success: queryResult.success,
      input: queryResult.inputstring,
      pods: [],
      primaryAnswer: null,
      images: [],
      data: {}
    };

    pods.forEach(pod => {
      const podData = {
        title: pod.title,
        subpod: pod.subpods ? pod.subpods.map(subpod => ({
          title: subpod.title,
          plaintext: subpod.plaintext,
          img: subpod.img ? subpod.img.map(img => ({
            src: img.src,
            alt: img.alt,
            width: img.width,
            height: img.height
          })) : []
        })) : []
      };

      result.pods.push(podData);

      // Extract primary answer
      if (pod.primary === true && pod.subpods && pod.subpods[0]) {
        result.primaryAnswer = pod.subpods[0].plaintext;
      }

      // Extract images
      if (pod.subpods) {
        pod.subpods.forEach(subpod => {
          if (subpod.img) {
            result.images.push(...subpod.img);
          }
        });
      }

      // Extract structured data
      result.data[pod.title] = podData;
    });

    return result;
  }
}
```

## 2. Question Generation Enhancement

### **Mathematical Question Generation**

```javascript
// src/services/math-question-generator.service.js
class MathQuestionGeneratorService {
  constructor() {
    this.wolframService = new WolframAlphaService();
    this.templates = this.loadQuestionTemplates();
  }

  async generateMathQuestion(parameters) {
    const { topic, difficulty, questionType, subtopic } = parameters;
    
    switch (questionType) {
      case 'equation_solving':
        return this.generateEquationQuestion(topic, difficulty, subtopic);
      case 'word_problem':
        return this.generateWordProblem(topic, difficulty, subtopic);
      case 'graph_analysis':
        return this.generateGraphQuestion(topic, difficulty, subtopic);
      case 'calculation':
        return this.generateCalculationQuestion(topic, difficulty, subtopic);
      default:
        throw new Error(`Unsupported question type: ${questionType}`);
    }
  }

  async generateEquationQuestion(topic, difficulty, subtopic) {
    // Generate equation based on topic and difficulty
    let equation;
    let solution;
    
    switch (subtopic) {
      case 'quadratic':
        equation = this.generateQuadraticEquation(difficulty);
        break;
      case 'linear':
        equation = this.generateLinearEquation(difficulty);
        break;
      case 'simultaneous':
        equation = this.generateSimultaneousEquations(difficulty);
        break;
      default:
        throw new Error(`Unsupported equation type: ${subtopic}`);
    }

    // Get solution from Wolfram Alpha
    const wolframResult = await this.wolframService.queryWolframAlpha(
      `solve ${equation}`
    );

    // Extract solution steps
    const steps = await this.extractSolutionSteps(wolframResult);
    
    // Generate question text
    const questionText = this.formatEquationQuestion(equation, difficulty);
    
    // Generate options for MCQ
    const options = await this.generateMCQOptions(wolframResult.primaryAnswer, equation);

    return {
      type: 'mcq',
      questionText: questionText,
      equation: equation,
      options: options,
      correctAnswer: wolframResult.primaryAnswer,
      solution: {
        steps: steps,
        explanation: wolframResult.data['Solution']?.subpod[0]?.plaintext || '',
        verification: wolframResult.primaryAnswer
      },
      difficulty: difficulty,
      topic: topic,
      subtopic: subtopic,
      metadata: {
        cognitiveLevel: 'application',
        timeEstimate: this.estimateTime(difficulty, 'equation'),
        wolframQuery: `solve ${equation}`
      }
    };
  }

  generateQuadraticEquation(difficulty) {
    const coefficients = this.getQuadraticCoefficients(difficulty);
    const a = coefficients.a;
    const b = coefficients.b;
    const c = coefficients.c;
    
    // Format equation
    let equation = `${a}x²`;
    if (b >= 0) equation += ` + ${b}x`;
    else equation += ` - ${Math.abs(b)}x`;
    if (c >= 0) equation += ` + ${c}`;
    else equation += ` - ${Math.abs(c)}`;
    equation += ` = 0`;
    
    return equation;
  }

  getQuadraticCoefficients(difficulty) {
    switch (difficulty) {
      case 'easy':
        return {
          a: 1,
          b: Math.floor(Math.random() * 10) + 1,
          c: Math.floor(Math.random() * 20) + 1
        };
      case 'medium':
        return {
          a: Math.floor(Math.random() * 5) + 1,
          b: Math.floor(Math.random() * 20) - 10,
          c: Math.floor(Math.random() * 30) - 15
        };
      case 'hard':
        return {
          a: Math.floor(Math.random() * 10) + 1,
          b: Math.floor(Math.random() * 40) - 20,
          c: Math.floor(Math.random() * 50) - 25
        };
    }
  }

  async generateMCQOptions(correctAnswer, equation) {
    const options = [correctAnswer];
    
    // Generate plausible distractors
    const distractors = await this.generateDistractors(correctAnswer, equation);
    options.push(...distractors);
    
    // Shuffle options
    return this.shuffleOptions(options);
  }

  async generateDistractors(correctAnswer, equation) {
    const distractors = [];
    const numericAnswer = parseFloat(correctAnswer);
    
    if (!isNaN(numericAnswer)) {
      // Generate close numerical incorrect answers
      distractors.push((numericAnswer + 1).toString());
      distractors.push((numericAnswer - 1).toString());
      
      // Generate common mistakes
      if (equation.includes('x²')) {
        distractors.push(`-${correctAnswer}`); // Sign error
        distractors.push((numericAnswer / 2).toString()); // Division error
      }
    } else {
      // For symbolic answers, generate common algebraic mistakes
      const symbolicDistractors = this.generateSymbolicDistractors(correctAnswer);
      distractors.push(...symbolicDistractors);
    }
    
    return distractors.slice(0, 3); // Return 3 distractors
  }
}
```

### **Word Problem Generation**

```javascript
async generateWordProblem(topic, difficulty, subtopic) {
  // Generate context and scenario
  const scenario = this.generateScenario(topic, subtopic, difficulty);
  
  // Create mathematical model
  const mathematicalModel = await this.createMathematicalModel(scenario);
  
  // Solve using Wolfram Alpha
  const wolframResult = await this.wolframService.queryWolframAlpha(
    mathematicalModel.query
  );
  
  // Format word problem
  const problemText = this.formatWordProblem(scenario, difficulty);
  
  return {
    type: 'descriptive',
    questionText: problemText,
    scenario: scenario,
    mathematicalModel: mathematicalModel,
    solution: {
      answer: wolframResult.primaryAnswer,
      steps: await this.extractSolutionSteps(wolframResult),
      explanation: this.generateExplanation(scenario, wolframResult)
    },
    rubric: this.generateRubric(topic, difficulty),
    difficulty: difficulty,
    metadata: {
      cognitiveLevel: 'analysis',
      timeEstimate: this.estimateTime(difficulty, 'word_problem'),
      wolframQuery: mathematicalModel.query
    }
  };
}

generateScenario(topic, subtopic, difficulty) {
  const scenarios = {
    'algebra': {
      'linear_equations': [
        {
          context: 'shopping',
          description: 'A student buys notebooks and pens',
          variables: ['notebooks', 'pens'],
          constraints: ['total cost', 'quantity relationship']
        },
        {
          context: 'travel',
          description: 'Distance and speed problems',
          variables: ['distance', 'speed', 'time'],
          constraints: ['time relationship', 'speed limits']
        }
      ],
      'quadratic_equations': [
        {
          context: 'area',
          description: 'Rectangle and square area problems',
          variables: ['length', 'width', 'area'],
          constraints: ['perimeter', 'area relationship']
        }
      ]
    },
    'geometry': {
      'triangles': [
        {
          context: 'construction',
          description: 'Building and measurement problems',
          variables: ['sides', 'angles', 'height'],
          constraints: ['triangle properties', 'Pythagorean theorem']
        }
      ]
    }
  };

  const topicScenarios = scenarios[topic]?.[subtopic] || [];
  return topicScenarios[Math.floor(Math.random() * topicScenarios.length)];
}
```

## 3. Answer Validation System

### **Mathematical Answer Checking**

```javascript
// src/services/answer-validation.service.js
class AnswerValidationService {
  constructor() {
    this.wolframService = new WolframAlphaService();
  }

  async validateAnswer(question, studentAnswer) {
    switch (question.type) {
      case 'mcq':
        return this.validateMCQAnswer(question, studentAnswer);
      case 'fill_blank':
        return this.validateFillBlankAnswer(question, studentAnswer);
      case 'descriptive':
        return this.validateDescriptiveAnswer(question, studentAnswer);
      case 'calculation':
        return this.validateCalculationAnswer(question, studentAnswer);
      default:
        throw new Error(`Unsupported question type: ${question.type}`);
    }
  }

  async validateCalculationAnswer(question, studentAnswer) {
    // Create verification query
    const verificationQuery = this.createVerificationQuery(question, studentAnswer);
    
    // Query Wolfram Alpha
    const wolframResult = await this.wolframService.queryWolframAlpha(verificationQuery);
    
    // Analyze result
    const validation = {
      isCorrect: false,
      confidence: 0,
      feedback: '',
      correctAnswer: question.correctAnswer,
      studentAnswer: studentAnswer,
      steps: [],
      explanation: ''
    };

    // Check if answer matches
    if (this.answersMatch(wolframResult.primaryAnswer, question.correctAnswer)) {
      validation.isCorrect = true;
      validation.confidence = 0.95;
      validation.feedback = 'Correct! Your answer is mathematically sound.';
    } else {
      validation.isCorrect = false;
      validation.confidence = 0.90;
      validation.feedback = `Incorrect. The correct answer is ${question.correctAnswer}.`;
      
      // Provide hint
      validation.hint = await this.generateHint(question, studentAnswer);
    }

    // Extract solution steps
    validation.steps = await this.extractSolutionSteps(wolframResult);
    validation.explanation = wolframResult.data['Solution']?.subpod[0]?.plaintext || '';

    return validation;
  }

  createVerificationQuery(question, studentAnswer) {
    // Create a query that verifies the student's answer
    if (question.equation) {
      return `verify ${studentAnswer} is solution of ${question.equation}`;
    } else if (question.questionText.includes('calculate')) {
      return `calculate ${this.extractCalculation(question.questionText)}`;
    } else {
      return `${question.questionText} answer ${studentAnswer}`;
    }
  }

  answersMatch(wolframAnswer, correctAnswer) {
    // Normalize both answers for comparison
    const normalizedWolfram = this.normalizeAnswer(wolframAnswer);
    const normalizedCorrect = this.normalizeAnswer(correctAnswer);
    
    return normalizedWolfram === normalizedCorrect;
  }

  normalizeAnswer(answer) {
    // Remove whitespace and convert to lowercase
    let normalized = answer.toString().trim().toLowerCase();
    
    // Remove common formatting differences
    normalized = normalized.replace(/\s+/g, '');
    normalized = normalized.replace(/([+-])\s*([+-])/g, '$1$2'); // Fix double signs
    
    // Handle mathematical notation
    normalized = normalized.replace(/²/g, '^2');
    normalized = normalized.replace(/³/g, '^3');
    normalized = normalized.replace(/π/g, 'pi');
    
    return normalized;
  }

  async generateHint(question, studentAnswer) {
    // Analyze student's answer to provide specific hint
    const analysisQuery = `why is ${studentAnswer} wrong for ${question.questionText}`;
    
    try {
      const wolframResult = await this.wolframService.queryWolframAlpha(analysisQuery);
      
      if (wolframResult.data['Error analysis']) {
        return wolframResult.data['Error analysis'].subpod[0].plaintext;
      } else {
        // Generic hint based on common mistakes
        return this.generateGenericHint(question, studentAnswer);
      }
    } catch (error) {
      return this.generateGenericHint(question, studentAnswer);
    }
  }
}
```

## 4. Step-by-Step Solution Generation

### **Solution Builder**

```javascript
// src/services/solution-builder.service.js
class SolutionBuilderService {
  constructor() {
    this.wolframService = new WolframAlphaService();
  }

  async generateSolution(question) {
    const solution = {
      questionId: question.id,
      questionText: question.questionText,
      steps: [],
      finalAnswer: question.correctAnswer,
      explanation: '',
      visualizations: []
    };

    // Get detailed solution from Wolfram Alpha
    const wolframQuery = this.buildSolutionQuery(question);
    const wolframResult = await this.wolframService.queryWolframAlpha(wolframQuery);

    // Extract solution steps
    solution.steps = await this.extractSolutionSteps(wolframResult);
    
    // Generate explanation
    solution.explanation = this.generateExplanation(wolframResult, question);
    
    // Extract visualizations
    solution.visualizations = this.extractVisualizations(wolframResult);

    return solution;
  }

  buildSolutionQuery(question) {
    switch (question.type) {
      case 'mcq':
        return `show steps to solve ${question.equation || question.questionText}`;
      case 'calculation':
        return `show steps for ${question.questionText}`;
      case 'descriptive':
        return `solve ${question.scenario?.mathematicalModel?.query || question.questionText}`;
      default:
        return `show solution for ${question.questionText}`;
    }
  }

  async extractSolutionSteps(wolframResult) {
    const steps = [];
    
    // Look for solution-related pods
    const solutionPods = wolframResult.pods.filter(pod => 
      pod.title.toLowerCase().includes('step') ||
      pod.title.toLowerCase().includes('solution') ||
      pod.title.toLowerCase().includes('result')
    );

    for (const pod of solutionPods) {
      if (pod.subpod && pod.subpod[0]) {
        const step = {
          title: pod.title,
          content: pod.subpod[0].plaintext,
          images: pod.subpod[0].img || []
        };
        steps.push(step);
      }
    }

    // If no explicit steps found, create generic steps
    if (steps.length === 0) {
      return this.createGenericSteps(wolframResult);
    }

    return steps;
  }

  createGenericSteps(wolframResult) {
    const steps = [];
    
    // Step 1: Problem identification
    steps.push({
      title: 'Step 1: Identify the Problem',
      content: 'Analyze what the question is asking for.',
      images: []
    });

    // Step 2: Setup
    if (wolframResult.data['Input interpretation']) {
      steps.push({
        title: 'Step 2: Setup the Equation',
        content: wolframResult.data['Input interpretation'].subpod[0].plaintext,
        images: wolframResult.data['Input interpretation'].subpod[0].img || []
      });
    }

    // Step 3: Solution
    if (wolframResult.primaryAnswer) {
      steps.push({
        title: 'Step 3: Solve',
        content: `Solution: ${wolframResult.primaryAnswer}`,
        images: []
      });
    }

    // Step 4: Verification
    steps.push({
      title: 'Step 4: Verify the Answer',
      content: 'Check if the solution satisfies the original problem.',
      images: []
    });

    return steps;
  }

  extractVisualizations(wolframResult) {
    const visualizations = [];
    
    // Look for plot/graph pods
    const plotPods = wolframResult.pods.filter(pod => 
      pod.title.toLowerCase().includes('plot') ||
      pod.title.toLowerCase().includes('graph') ||
      pod.title.toLowerCase().includes('visual')
    );

    for (const pod of plotPods) {
      if (pod.subpod && pod.subpod[0] && pod.subpod[0].img) {
        visualizations.push({
          type: 'plot',
          title: pod.title,
          images: pod.subpod[0].img,
          description: pod.subpod[0].plaintext || ''
        });
      }
    }

    return visualizations;
  }
}
```

## 5. Graph and Formula Generation

### **Graph Generation Service**

```javascript
// src/services/graph-generation.service.js
class GraphGenerationService {
  constructor() {
    this.wolframService = new WolframAlphaService();
  }

  async generateGraph(parameters) {
    const { equation, graphType, range, labels } = parameters;
    
    // Build Wolfram Alpha query
    const query = this.buildGraphQuery(equation, graphType, range);
    
    // Get graph from Wolfram Alpha
    const wolframResult = await this.wolframService.queryWolframAlpha(query);
    
    // Extract graph data
    const graphData = this.extractGraphData(wolframResult);
    
    // Generate question based on graph
    const question = await this.generateGraphQuestion(graphData, parameters);
    
    return {
      graph: graphData,
      question: question,
      visualization: graphData.images[0] || null
    };
  }

  buildGraphQuery(equation, graphType, range) {
    let query = `plot ${equation}`;
    
    if (graphType) {
      query += ` as ${graphType}`;
    }
    
    if (range) {
      query += ` from ${range.xMin} to ${range.xMax}`;
    }
    
    return query;
  }

  extractGraphData(wolframResult) {
    const graphPod = wolframResult.pods.find(pod => 
      pod.title.toLowerCase().includes('plot')
    );

    if (!graphPod || !graphPod.subpod || !graphPod.subpod[0]) {
      throw new Error('No graph data found in Wolfram Alpha response');
    }

    return {
      title: graphPod.title,
      description: graphPod.subpod[0].plaintext || '',
      images: graphPod.subpod[0].img || [],
      data: this.parseGraphData(graphPod.subpod[0].plaintext)
    };
  }

  async generateGraphQuestion(graphData, parameters) {
    const questionTypes = [
      'identify_points',
      'find_intercepts',
      'analyze_behavior',
      'compare_functions'
    ];

    const selectedType = questionTypes[Math.floor(Math.random() * questionTypes.length)];
    
    switch (selectedType) {
      case 'identify_points':
        return this.generatePointIdentificationQuestion(graphData);
      case 'find_intercepts':
        return this.generateInterceptQuestion(graphData);
      case 'analyze_behavior':
        return this.generateBehaviorQuestion(graphData);
      case 'compare_functions':
        return this.generateComparisonQuestion(graphData);
      default:
        return this.generatePointIdentificationQuestion(graphData);
    }
  }

  generatePointIdentificationQuestion(graphData) {
    return {
      type: 'mcq',
      questionText: `Based on the graph shown, what is the y-coordinate when x = 2?`,
      graphImage: graphData.images[0],
      options: this.generatePointOptions(graphData),
      correctAnswer: this.calculateYAtX(graphData, 2),
      solution: {
        explanation: 'To find the y-coordinate, locate x=2 on the x-axis and find the corresponding point on the graph.',
        steps: [
          'Locate x=2 on the horizontal axis',
          'Move vertically to intersect the graph',
          'Read the y-coordinate at this point'
        ]
      }
    };
  }
}
```

## 6. Configuration and Setup

### **Environment Configuration**

```javascript
// config/wolfram-alpha.config.js
module.exports = {
  wolframAlpha: {
    appId: process.env.WOLFRAM_ALPHA_APP_ID,
    baseUrl: 'https://api.wolframalpha.com/v2/query',
    timeout: 30000, // 30 seconds timeout
    maxRetries: 3,
    rateLimit: {
      requestsPerMinute: 100,
      requestsPerHour: 2000,
      requestsPerDay: 10000
    },
    cache: {
      enabled: true,
      ttl: 3600, // 1 hour cache
      maxSize: 1000 // max cached responses
    }
  }
};
```

### **Rate Limiting and Caching**

```javascript
// src/middleware/wolfram-alpha.middleware.js
const Redis = require('ioredis');
const redis = new Redis();

class WolframAlphaMiddleware {
  constructor() {
    this.rateLimitStore = new Map();
    this.cacheStore = new Map();
  }

  async rateLimit(req, res, next) {
    const clientIP = req.ip;
    const key = `wolfram_rate_limit:${clientIP}`;
    
    try {
      const currentRequests = await redis.incr(key);
      
      if (currentRequests === 1) {
        await redis.expire(key, 60); // Reset after 1 minute
      }
      
      if (currentRequests > config.wolframAlpha.rateLimit.requestsPerMinute) {
        return res.status(429).json({
          error: 'Rate limit exceeded for Wolfram Alpha API',
          retryAfter: 60
        });
      }
      
      next();
    } catch (error) {
      console.error('Rate limiting error:', error);
      next(); // Continue if rate limiting fails
    }
  }

  async cache(req, res, next) {
    if (req.method !== 'GET') {
      return next();
    }

    const cacheKey = this.generateCacheKey(req);
    
    try {
      const cachedResponse = await redis.get(cacheKey);
      
      if (cachedResponse) {
        return res.json(JSON.parse(cachedResponse));
      }
      
      // Override res.json to cache the response
      const originalJson = res.json;
      res.json = function(data) {
        redis.setex(cacheKey, config.wolframAlpha.cache.ttl, JSON.stringify(data));
        return originalJson.call(this, data);
      };
      
      next();
    } catch (error) {
      console.error('Cache error:', error);
      next();
    }
  }

  generateCacheKey(req) {
    const query = req.query.input || '';
    return `wolfram_cache:${Buffer.from(query).toString('base64')}`;
  }
}
```

## 7. Implementation Benefits

### **Enhanced Question Quality**
- **Mathematical Accuracy**: Verified by Wolfram Alpha's computational engine
- **Step-by-Step Solutions**: Detailed explanations for learning
- **Visual Learning**: Graphs and visual representations
- **Real-World Applications**: Contextual word problems

### **Automated Validation**
- **Answer Checking**: Instant mathematical verification
- **Error Analysis**: Identify common mistakes
- **Personalized Hints**: Targeted feedback based on errors
- **Confidence Scoring**: Reliability metrics for answers

### **Educational Value**
- **Learning Support**: Detailed solutions and explanations
- **Visual Aids**: Graphs and plots for better understanding
- **Multiple Representations**: Different ways to present concepts
- **Interactive Learning**: Dynamic problem generation

### **System Integration**
- **API Integration**: Seamless integration with existing architecture
- **Caching**: Performance optimization through response caching
- **Rate Limiting**: Controlled API usage to prevent overages
- **Error Handling**: Robust error management and fallbacks

## 8. Usage Examples

### **Math Question Generation**
```javascript
// Generate a quadratic equation question
const question = await mathGenerator.generateMathQuestion({
  topic: 'algebra',
  subtopic: 'quadratic_equations',
  difficulty: 'medium',
  questionType: 'equation_solving'
});

// Result: Complete question with options, solution, and steps
```

### **Answer Validation**
```javascript
// Validate student's answer
const validation = await answerValidator.validateAnswer(question, studentAnswer);

// Result: Detailed validation with feedback and hints
```

### **Solution Generation**
```javascript
// Generate step-by-step solution
const solution = await solutionBuilder.generateSolution(question);

// Result: Complete solution with steps and visualizations
```

This comprehensive Wolfram Alpha integration enhances the assessment engine with powerful mathematical capabilities, automated validation, and rich learning support features.
