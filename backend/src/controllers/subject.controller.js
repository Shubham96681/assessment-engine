const schoolService = require('../services/school.service');

exports.listForMySchool = async (req, res, next) => {
  try {
    if (!req.user.schoolId) {
      return res.json({ status: 'success', data: [] });
    }
    const data = await schoolService.listSubjects(req.user.schoolId);
    res.json({ status: 'success', data });
  } catch (e) {
    next(e);
  }
};
