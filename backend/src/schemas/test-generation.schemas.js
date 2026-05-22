const Joi = require('joi');

const questionTypesShape = Joi.object({
  mcq: Joi.boolean().default(true),
  true_false: Joi.boolean().default(true),
  fill_blank: Joi.boolean().default(true),
  descriptive: Joi.boolean().default(true),
});

const testGenerationSchemas = {
  generatePreview: Joi.object({
    numberOfQuestions: Joi.number().integer().min(1).max(100).default(20),
    questionTypes: questionTypesShape.default(),
    questionTypeMix: Joi.object({
      mcq: Joi.number().min(0).max(100).default(40),
      true_false: Joi.number().min(0).max(100).default(20),
      fill_blank: Joi.number().min(0).max(100).default(20),
      descriptive: Joi.number().min(0).max(100).default(20),
    }).default(),
    difficultyDistribution: Joi.object({
      easy: Joi.number().min(0).max(100).default(30),
      medium: Joi.number().min(0).max(100).default(50),
      hard: Joi.number().min(0).max(100).default(20),
    }).default(),
    marksByType: Joi.object({
      mcq: Joi.number().positive().default(1),
      true_false: Joi.number().positive().default(1),
      fill_blank: Joi.number().positive().default(2),
      descriptive: Joi.number().positive().default(4),
    }).default(),
    subjectId: Joi.string().trim().max(40).allow('', null).optional(),
    classId: Joi.string().trim().max(40).allow('', null).optional(),
    board: Joi.string().allow('', null).max(50),
    chapterLabel: Joi.string().allow('', null).max(200),
    // Exact book path key — narrows pool to questions from that imported PDF.
    localLibraryRel: Joi.string().allow('', null).max(512),
    topics: Joi.array().items(Joi.string().max(200)).default([]),
    includeHeritage: Joi.boolean().default(false),
    excludeTags: Joi.array().items(Joi.string().max(100)).default([]),
    resourcePriority: Joi.object({
      preferExtracted: Joi.boolean().default(true),
    }).default(),
  }),

  createFromGeneration: Joi.object({
    generationParameters: Joi.object().unknown(true).allow(null),
    test: Joi.object({
      title: Joi.string().min(1).max(500).required(),
      description: Joi.string().allow('', null),
      subjectId: Joi.string().trim().max(40).allow('', null).optional(),
      classIds: Joi.array().items(Joi.string().trim().max(40)).default([]),
      durationMinutes: Joi.number().integer().min(1).required(),
      totalMarks: Joi.number().integer().min(1).default(1),
      passingMarks: Joi.number().integer().min(0).max(100).allow(null),
      instructions: Joi.string().allow('', null),
      questionSelectionMode: Joi.string().valid('manual', 'random', 'mixed').default('mixed'),
      shuffleQuestions: Joi.boolean().default(false),
      shuffleOptions: Joi.boolean().default(false),
      showResultsImmediately: Joi.boolean().default(false),
      allowReview: Joi.boolean().default(true),
      maxAttempts: Joi.number().integer().min(1).default(1),
      showAnswersAfterTest: Joi.boolean().default(false),
      negativeMarking: Joi.boolean().default(false),
      negativeMarkingValue: Joi.number().min(0).max(1).default(0.25),
      startTime: Joi.date().iso().required(),
      endTime: Joi.date().iso().greater(Joi.ref('startTime')).required(),
      status: Joi.string().valid('draft', 'published', 'scheduled', 'completed', 'archived').default('draft'),
      settings: Joi.object().default({}),
    }),
    approvedQuestions: Joi.array()
      .items(
        Joi.object({
          questionId: Joi.string().uuid().required(),
          marks: Joi.number().positive().required(),
          sectionName: Joi.string().allow('', null),
        })
      )
      .min(1)
      .required(),
  }),
};

module.exports = { testGenerationSchemas };
