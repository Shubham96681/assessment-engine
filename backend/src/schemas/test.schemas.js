const Joi = require('joi');

const testSchemas = {
  create: Joi.object({
    title: Joi.string().min(1).max(500).required(),
    description: Joi.string().allow('', null),
    subjectId: Joi.string().uuid().allow(null),
    classIds: Joi.array().items(Joi.string().uuid()).default([]),
    durationMinutes: Joi.number().integer().min(1).required(),
    totalMarks: Joi.number().integer().min(1).required(),
    passingMarks: Joi.number().integer().min(0).allow(null),
    instructions: Joi.string().allow('', null),
    questionSelectionMode: Joi.string().valid('manual', 'random', 'mixed').default('manual'),
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
    questionIds: Joi.array()
      .items(
        Joi.object({
          questionId: Joi.string().uuid().required(),
          marks: Joi.number().positive().required(),
          questionOrder: Joi.number().integer().min(0),
          sectionName: Joi.string().allow('', null),
          isMandatory: Joi.boolean().default(true),
        })
      )
      .default([]),
  }),

  schedule: Joi.object({
    classId: Joi.string().uuid().required(),
    scheduledStartTime: Joi.date().iso().required(),
    scheduledEndTime: Joi.date().iso().greater(Joi.ref('scheduledStartTime')).required(),
  }),

  list: Joi.object({
    page: Joi.number().integer().min(1),
    limit: Joi.number().integer().min(1).max(100),
    status: Joi.string(),
    subjectId: Joi.string().uuid(),
  }),

  addQuestions: Joi.object({
    questions: Joi.array()
      .items(
        Joi.object({
          questionId: Joi.string().uuid().required(),
          marks: Joi.number().positive().required(),
          questionOrder: Joi.number().integer().min(0),
          sectionName: Joi.string().allow('', null),
          isMandatory: Joi.boolean(),
        })
      )
      .min(1)
      .required(),
  }),

  duplicate: Joi.object({
    title: Joi.string().min(1).max(500),
    startTime: Joi.date().iso(),
    endTime: Joi.date().iso(),
  }),
};

module.exports = { testSchemas };
