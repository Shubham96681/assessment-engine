const analyticsService = require('../services/analytics.service');

exports.testAnalytics = async (req, res, next) => {
  try {
    const data = await analyticsService.getTestAnalytics(req.params.testId);
    res.json({ status: 'success', data });
  } catch (e) {
    next(e);
  }
};

exports.studentPerformance = async (req, res, next) => {
  try {
    const { studentId } = req.params;
    if (req.user.role === 'student' && req.user.id !== studentId) {
      const { AppError } = require('../middleware/error.middleware');
      throw new AppError('Forbidden', 403);
    }
    const data = await analyticsService.getStudentPerformance(studentId);
    res.json({ status: 'success', data });
  } catch (e) {
    next(e);
  }
};

exports.classPerformance = async (req, res, next) => {
  try {
    const data = await analyticsService.getClassPerformance(
      req.params.classId,
      req.query.subjectId,
      { from: req.query.from }
    );
    res.json({ status: 'success', data });
  } catch (e) {
    next(e);
  }
};

exports.report = async (req, res, next) => {
  try {
    const data = await analyticsService.generateReport(req.query.type, {
      testId: req.query.testId,
      studentId: req.query.studentId,
    });
    res.json({ status: 'success', data });
  } catch (e) {
    next(e);
  }
};
