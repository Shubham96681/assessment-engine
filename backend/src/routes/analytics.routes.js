const express = require('express');
const analyticsController = require('../controllers/analytics.controller');
const { protect, restrictTo } = require('../middleware/auth.middleware');

const router = express.Router();

router.use(protect);

router.get('/tests/:testId', restrictTo('admin', 'school_admin', 'teacher', 'department_head'), analyticsController.testAnalytics);
router.get('/students/:studentId', analyticsController.studentPerformance);
router.get('/classes/:classId', restrictTo('admin', 'school_admin', 'teacher', 'department_head'), analyticsController.classPerformance);
router.get('/reports', restrictTo('admin', 'school_admin', 'teacher'), analyticsController.report);

module.exports = router;
