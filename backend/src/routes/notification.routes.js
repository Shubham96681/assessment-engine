const express = require('express');
const notificationController = require('../controllers/notification.controller');
const { protect, restrictTo } = require('../middleware/auth.middleware');

const router = express.Router();

router.use(protect);

router.get('/', notificationController.list);
router.post('/:id/read', notificationController.markRead);
router.post('/email/:userId', restrictTo('admin', 'school_admin'), notificationController.sendTest);

module.exports = router;
