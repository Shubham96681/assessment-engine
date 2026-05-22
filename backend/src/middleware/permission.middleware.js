const { AppError } = require('./error.middleware');

const requirePermission = (predicate) => (req, res, next) => {
  if (!req.user) {
    return next(new AppError('Not authenticated', 401));
  }
  try {
    if (!predicate(req.user, req)) {
      return next(new AppError('Insufficient permissions', 403));
    }
    next();
  } catch (e) {
    next(e);
  }
};

const sameSchoolOrAdmin = (req) => {
  const schoolId = req.params.schoolId || req.body.schoolId;
  if (req.user.role === 'admin' || req.user.role === 'school_admin') return true;
  if (!schoolId) return true;
  return req.user.schoolId === schoolId;
};

module.exports = { requirePermission, sameSchoolOrAdmin };
