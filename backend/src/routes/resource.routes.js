const express = require('express');
const multer = require('multer');
const resourceController = require('../controllers/resource.controller');
const { protect, restrictTo } = require('../middleware/auth.middleware');
const { uploadLimiter } = require('../middleware/rate-limit.middleware');
const validateRequest = require('../middleware/validation.middleware');
const { resourceSchemas } = require('../schemas/resource.schemas');

const router = express.Router();
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 50 * 1024 * 1024 },
});

router.use(protect);

router.get('/cbse-curriculum-tree', resourceController.cbseCurriculumTree);
router.get('/', resourceController.list);
router.post(
  '/books/from-url',
  uploadLimiter,
  restrictTo('admin', 'school_admin', 'teacher', 'librarian', 'content_manager'),
  validateRequest(resourceSchemas.bookFromUrl),
  resourceController.registerBookFromUrl
);
router.post(
  '/books/import-local-cbse',
  uploadLimiter,
  restrictTo('admin', 'school_admin', 'teacher', 'librarian', 'content_manager'),
  validateRequest(resourceSchemas.importLocalCbse),
  resourceController.importLocalCbseLibrary
);
router.post(
  '/books',
  uploadLimiter,
  restrictTo('admin', 'school_admin', 'teacher', 'librarian', 'content_manager'),
  upload.single('file'),
  validateRequest(resourceSchemas.bookMeta),
  resourceController.uploadBook
);
router.post(
  '/question-papers',
  uploadLimiter,
  restrictTo('admin', 'school_admin', 'teacher', 'librarian', 'content_manager'),
  upload.single('file'),
  validateRequest(resourceSchemas.paperMeta),
  resourceController.uploadPaper
);

router.post(
  '/:resourceType/:id/extract',
  restrictTo('admin', 'school_admin', 'teacher', 'content_manager'),
  resourceController.extractFromDocument
);
router.post(
  '/:resourceType/:id/import-questions',
  restrictTo('admin', 'school_admin', 'teacher', 'content_manager'),
  validateRequest(resourceSchemas.importQuestions),
  resourceController.importQuestions
);

router.post('/:resourceType/:id/verify', restrictTo('admin', 'school_admin', 'teacher', 'content_manager'), validateRequest(resourceSchemas.verifyExtracted), resourceController.verify);

module.exports = router;
