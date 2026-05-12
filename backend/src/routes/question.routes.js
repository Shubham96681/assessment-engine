const express = require('express');
const questionController = require('../controllers/question.controller');
const { protect, restrictTo } = require('../middleware/auth.middleware');
const validateRequest = require('../middleware/validation.middleware');
const { questionSchemas } = require('../schemas/question.schemas');

const router = express.Router();

router.use(protect);

router.get('/bank-filters', questionController.bankFilters);
router.post('/', restrictTo('admin', 'school_admin', 'teacher', 'content_manager'), validateRequest(questionSchemas.create), questionController.create);
router.get('/', validateRequest(questionSchemas.list, 'query'), questionController.list);
router.post('/import', restrictTo('admin', 'school_admin', 'teacher', 'content_manager'), validateRequest(questionSchemas.importJson), questionController.importJson);
router.get('/export', validateRequest(questionSchemas.list, 'query'), questionController.exportJson);

module.exports = router;
