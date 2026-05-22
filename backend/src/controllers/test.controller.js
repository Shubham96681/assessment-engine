const testService = require('../services/test.service');
const testTakingService = require('../services/test-taking.service');
const automatedTestGenerationService = require('../services/automated-test-generation.service');

exports.create = async (req, res, next) => {
  try {
    const test = await testService.createTest(req.body, req.user.id);
    res.status(201).json({ status: 'success', data: test });
  } catch (e) {
    next(e);
  }
};

exports.generatePreview = async (req, res, next) => {
  try {
    const data = await automatedTestGenerationService.generatePreview(req.body, req.user.id);
    res.json({ status: 'success', data });
  } catch (e) {
    next(e);
  }
};

exports.createFromGeneration = async (req, res, next) => {
  try {
    const { test, approvedQuestions, generationParameters } = req.body;
    const data = await automatedTestGenerationService.createTestFromApproved(
      { test, approvedQuestions, generationParameters },
      req.user.id
    );
    res.status(201).json({ status: 'success', data });
  } catch (e) {
    next(e);
  }
};

exports.list = async (req, res, next) => {
  try {
    if (!req.user.schoolId) {
      return res.json({ status: 'success', data: [], meta: { total: 0, page: 1, limit: 20, totalPages: 1 } });
    }
    const result = await testService.list(req.query, req.user.schoolId);
    res.json({ status: 'success', ...result });
  } catch (e) {
    next(e);
  }
};

exports.getById = async (req, res, next) => {
  try {
    const test = await testService.getById(req.params.id);
    res.json({ status: 'success', data: test });
  } catch (e) {
    next(e);
  }
};

exports.addQuestions = async (req, res, next) => {
  try {
    const test = await testService.addQuestionsToTest(req.params.id, req.body.questions, req.user);
    res.json({ status: 'success', data: test });
  } catch (e) {
    next(e);
  }
};

exports.schedule = async (req, res, next) => {
  try {
    const schedule = await testService.scheduleTest(req.params.id, req.body, req.user);
    res.status(201).json({ status: 'success', data: schedule });
  } catch (e) {
    next(e);
  }
};

exports.publish = async (req, res, next) => {
  try {
    const test = await testService.publishTest(req.params.id, req.user);
    res.json({ status: 'success', data: test });
  } catch (e) {
    next(e);
  }
};

exports.duplicate = async (req, res, next) => {
  try {
    const test = await testService.duplicateTest(req.params.id, req.body, req.user);
    res.status(201).json({ status: 'success', data: test });
  } catch (e) {
    next(e);
  }
};

exports.start = async (req, res, next) => {
  try {
    const result = await testTakingService.startTest(req.params.id, req.user.id);
    res.status(201).json({ status: 'success', data: result });
  } catch (e) {
    next(e);
  }
};

exports.submitAnswer = async (req, res, next) => {
  try {
    const result = await testTakingService.submitAnswer(
      req.params.attemptId,
      req.params.questionId,
      req.body,
      req.user.id
    );
    res.json({ status: 'success', data: result });
  } catch (e) {
    next(e);
  }
};

exports.submitTest = async (req, res, next) => {
  try {
    const result = await testTakingService.submitTest(req.params.attemptId, req.user.id);
    res.json({ status: 'success', data: result });
  } catch (e) {
    next(e);
  }
};
