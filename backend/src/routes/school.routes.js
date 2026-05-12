const express = require('express');
const schoolController = require('../controllers/school.controller');
const { protect, restrictTo } = require('../middleware/auth.middleware');
const validateRequest = require('../middleware/validation.middleware');
const { schoolSchemas } = require('../schemas/school.schemas');

const router = express.Router();

router.use(protect);

router.post('/', restrictTo('admin'), validateRequest(schoolSchemas.create), schoolController.create);
router.get('/', schoolController.list);
router.get('/:id', schoolController.getById);
router.patch('/:id', restrictTo('admin', 'school_admin'), validateRequest(schoolSchemas.update), schoolController.update);
router.get('/:id/users', restrictTo('admin', 'school_admin'), schoolController.users);

module.exports = router;
