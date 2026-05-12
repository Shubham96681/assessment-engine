const express = require('express');
const userController = require('../controllers/user.controller');
const { protect, restrictTo } = require('../middleware/auth.middleware');
const validateRequest = require('../middleware/validation.middleware');
const { userSchemas } = require('../schemas/user.schemas');

const router = express.Router();

router.use(protect);

router.get('/me', userController.getMe);
router.patch('/me', validateRequest(userSchemas.updateProfile), userController.updateProfile);

router.get('/', restrictTo('admin', 'school_admin', 'department_head'), validateRequest(userSchemas.listUsers, 'query'), userController.list);
router.patch('/:id', restrictTo('admin', 'school_admin'), userController.updateUser);
router.post('/:id/role', restrictTo('admin', 'school_admin'), validateRequest(userSchemas.assignRole), userController.assignRole);
router.post('/bulk-import', restrictTo('admin', 'school_admin'), validateRequest(userSchemas.bulkImport), userController.bulkImport);

module.exports = router;
