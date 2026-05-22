const express = require('express');
const subjectController = require('../controllers/subject.controller');
const { protect } = require('../middleware/auth.middleware');

const router = express.Router();

router.use(protect);

router.get('/', subjectController.listForMySchool);

module.exports = router;
