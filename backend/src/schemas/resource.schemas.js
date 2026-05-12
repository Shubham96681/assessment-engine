const Joi = require('joi');
const { questionSchemas } = require('./question.schemas');

const resourceSchemas = {
  bookMeta: Joi.object({
    title: Joi.string().required(),
    author: Joi.string().allow('', null),
    classId: Joi.string().uuid().allow(null),
    subjectId: Joi.string().uuid().allow(null),
    tags: Joi.array().items(Joi.string()).default([]),
    metadata: Joi.alternatives(Joi.string(), Joi.object()).optional(),
  }),

  bookFromUrl: Joi.object({
    title: Joi.string().trim().min(1).max(500).required(),
    author: Joi.string().trim().allow('', null).max(300),
    fileUrl: Joi.string()
      .trim()
      .max(2048)
      .pattern(/^https:\/\/.+/i)
      .required()
      .messages({ 'string.pattern.base': '"fileUrl" must be an https URL' }),
    fileName: Joi.string().trim().allow('', null).max(500),
    fileType: Joi.string().trim().allow('', null).max(200),
  }),

  paperMeta: Joi.object({
    title: Joi.string().required(),
    examName: Joi.string().allow('', null),
    year: Joi.number().integer().required(),
    classId: Joi.string().uuid().allow(null),
    subjectId: Joi.string().uuid().allow(null),
    tags: Joi.array().items(Joi.string()).default([]),
    metadata: Joi.alternatives(Joi.string(), Joi.object()).optional(),
  }),

  verifyExtracted: Joi.object({
    updates: Joi.array()
      .items(
        Joi.object({
          extractedQuestionId: Joi.string().uuid().required(),
          questionPatch: Joi.object().unknown(true),
          markVerified: Joi.boolean().default(true),
        })
      )
      .required(),
  }),

  importQuestions: Joi.object({
    questions: Joi.array()
      .min(1)
      .items(questionSchemas.create.keys({ isVerified: Joi.boolean().optional() }))
      .required(),
  }),

  importLocalCbse: Joi.object({
    dryRun: Joi.boolean().default(false),
    limit: Joi.number().integer().min(1).max(50000).allow(null),
  }).default({}),
};

module.exports = { resourceSchemas };
