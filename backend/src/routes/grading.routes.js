const express = require('express');
const Joi = require('joi');
const gradingController = require('../controllers/grading.controller');
const { protect, restrictTo } = require('../middleware/auth.middleware');
const validateRequest = require('../middleware/validation.middleware');

const router = express.Router();

const gradeSchema = Joi.object({
  marksObtained: Joi.number().required(),
  feedback: Joi.string().allow('', null),
});

router.use(protect);

router.get('/queue', restrictTo('admin', 'school_admin', 'teacher', 'department_head'), gradingController.queue);
router.post(
  '/attempts/:attemptId/questions/:questionId',
  restrictTo('admin', 'school_admin', 'teacher'),
  validateRequest(gradeSchema),
  gradingController.gradeSubjective
);
router.post('/attempts/:attemptId/recalculate', restrictTo('admin', 'school_admin', 'teacher'), gradingController.recalculate);

module.exports = router;
