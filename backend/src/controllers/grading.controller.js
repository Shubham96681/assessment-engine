const gradingService = require('../services/grading.service');

exports.queue = async (req, res, next) => {
  try {
    const items = await gradingService.getGradingQueue(req.user.id);
    res.json({ status: 'success', data: items });
  } catch (e) {
    next(e);
  }
};

exports.gradeSubjective = async (req, res, next) => {
  try {
    const attempt = await gradingService.gradeSubjectiveQuestion(
      req.params.attemptId,
      req.params.questionId,
      req.body,
      req.user.id
    );
    res.json({ status: 'success', data: attempt });
  } catch (e) {
    next(e);
  }
};

exports.recalculate = async (req, res, next) => {
  try {
    const attempt = await gradingService.calculateFinalScore(req.params.attemptId);
    res.json({ status: 'success', data: attempt });
  } catch (e) {
    next(e);
  }
};
