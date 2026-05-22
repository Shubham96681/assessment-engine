const questionService = require('../services/question.service');

exports.create = async (req, res, next) => {
  try {
    const q = await questionService.createQuestion(req.body, req.user.id);
    res.status(201).json({ status: 'success', data: q });
  } catch (e) {
    next(e);
  }
};

exports.list = async (req, res, next) => {
  try {
    if (!req.user.schoolId) {
      return res.json({ status: 'success', data: [], meta: { total: 0, page: 1, limit: 20, totalPages: 1 } });
    }
    const result = await questionService.getQuestions(req.query, req.user.schoolId);
    res.json({ status: 'success', ...result });
  } catch (e) {
    next(e);
  }
};

exports.bankFilters = async (req, res, next) => {
  try {
    if (!req.user.schoolId) {
      return res.json({
        status: 'success',
        data: { questionCount: 0, topics: [], tagFilters: [], chapters: [] },
      });
    }
    const data = await questionService.getBankFilterAggregates(req.user.schoolId);
    res.json({ status: 'success', data });
  } catch (e) {
    next(e);
  }
};

exports.importJson = async (req, res, next) => {
  try {
    const report = await questionService.importQuestions(req.body.questions, req.user.id);
    res.status(201).json({ status: 'success', report });
  } catch (e) {
    next(e);
  }
};

exports.exportJson = async (req, res, next) => {
  try {
    const payload = await questionService.exportQuestions(req.query, req.user.schoolId);
    res.json({ status: 'success', data: payload });
  } catch (e) {
    next(e);
  }
};
