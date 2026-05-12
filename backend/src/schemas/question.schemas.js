const Joi = require('joi');

const questionOption = Joi.object({
  optionText: Joi.string().required(),
  isCorrect: Joi.boolean().default(false),
  optionOrder: Joi.number().integer().min(0).required(),
  explanation: Joi.string().allow('', null),
});

const questionSchemas = {
  create: Joi.object({
    questionType: Joi.string()
      .valid('mcq', 'true_false', 'fill_blank', 'descriptive', 'coding', 'matching', 'drag_drop', 'hotspot')
      .required(),
    questionText: Joi.string().min(1).required(),
    explanation: Joi.string().allow('', null),
    questionData: Joi.object().default({}),
    difficulty: Joi.string().valid('easy', 'medium', 'hard').default('medium'),
    marks: Joi.number().positive().default(1),
    negativeMarks: Joi.number().min(0).default(0),
    subjectId: Joi.string().uuid().allow(null),
    topics: Joi.array().items(Joi.string()).default([]),
    tags: Joi.array().items(Joi.string()).default([]),
    options: Joi.array().items(questionOption).default([]),
  }),

  list: Joi.object({
    page: Joi.number().integer().min(1),
    limit: Joi.number().integer().min(1).max(500),
    questionType: Joi.string(),
    subjectId: Joi.string().uuid(),
    sourceResourceId: Joi.string().uuid().allow('', null),
    sourceResourceType: Joi.string().valid('book', 'question_paper').allow('', null),
    difficulty: Joi.string(),
    search: Joi.string().max(500),
  }),

  importJson: Joi.object({
    questions: Joi.array().items(Joi.object()).min(1).required(),
  }),
};

module.exports = { questionSchemas };
