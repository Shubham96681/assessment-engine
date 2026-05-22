const express = require('express');
const testController = require('../controllers/test.controller');
const { protect, restrictTo } = require('../middleware/auth.middleware');
const validateRequest = require('../middleware/validation.middleware');
const { testSchemas } = require('../schemas/test.schemas');
const { testGenerationSchemas } = require('../schemas/test-generation.schemas');
const Joi = require('joi');

const router = express.Router();

const submitAnswerSchema = Joi.object({
  answer: Joi.string().allow('', null),
  selectedOptions: Joi.array().items(Joi.string().uuid()).default([]),
  answerFileUrl: Joi.string().uri().allow('', null),
  timeSpentSeconds: Joi.number().integer().min(0),
});

router.use(protect);

router.post('/attempts/:attemptId/questions/:questionId/answer', restrictTo('student', 'teacher', 'admin'), validateRequest(submitAnswerSchema), testController.submitAnswer);
router.post('/attempts/:attemptId/submit', restrictTo('student', 'teacher', 'admin'), testController.submitTest);

router.post(
  '/generate-preview',
  restrictTo('admin', 'school_admin', 'teacher', 'content_manager'),
  validateRequest(testGenerationSchemas.generatePreview),
  testController.generatePreview
);
router.post(
  '/from-generation',
  restrictTo('admin', 'school_admin', 'teacher', 'content_manager'),
  validateRequest(testGenerationSchemas.createFromGeneration),
  testController.createFromGeneration
);

router.post('/', restrictTo('admin', 'school_admin', 'teacher', 'content_manager'), validateRequest(testSchemas.create), testController.create);
router.get('/', validateRequest(testSchemas.list, 'query'), testController.list);

router.post('/:id/questions', restrictTo('admin', 'school_admin', 'teacher', 'content_manager'), validateRequest(testSchemas.addQuestions), testController.addQuestions);
router.post('/:id/schedule', restrictTo('admin', 'school_admin', 'teacher'), validateRequest(testSchemas.schedule), testController.schedule);
router.post('/:id/publish', restrictTo('admin', 'school_admin', 'teacher'), testController.publish);
router.post('/:id/duplicate', restrictTo('admin', 'school_admin', 'teacher'), validateRequest(testSchemas.duplicate), testController.duplicate);

router.post('/:id/start', restrictTo('student', 'teacher', 'admin'), testController.start);
router.get('/:id', testController.getById);

module.exports = router;
