const jwt = require('jsonwebtoken');
const { promisify } = require('util');
const { AppError } = require('./error.middleware');
const User = require('../models/User');
const db = require('../utils/database');
const logger = require('../utils/logger');
const appConfig = require('../config/app.config');

let authDisabledUserCache = null;

async function resolveAuthDisabledUser() {
  if (authDisabledUserCache) return authDisabledUserCache;

  const email = appConfig.authDisabledAsUserEmail;
  let user = email ? await User.findByEmail(email) : null;
  if (!user) {
    user = await db.prisma.user.findFirst({
      where: { deletedAt: null },
      include: { school: true },
    });
  }
  if (!user) {
    return null;
  }
  authDisabledUserCache = user;
  return user;
}

const protect = async (req, res, next) => {
  try {
    if (appConfig.isAuthDisabled()) {
      const user = await resolveAuthDisabledUser();
      if (!user) {
        return next(
          new AppError(
            'AUTH_DISABLED is set but no user exists in the database (run prisma db seed).',
            500
          )
        );
      }
      req.user = user;
      return next();
    }

    let token;
    if (req.headers.authorization && req.headers.authorization.startsWith('Bearer')) {
      token = req.headers.authorization.split(' ')[1];
    }

    if (!token) {
      return next(new AppError('Access token is required', 401));
    }

    if (!appConfig.jwt.secret) {
      return next(new AppError('JWT not configured', 500));
    }

    const decoded = await promisify(jwt.verify)(token, appConfig.jwt.secret);

    const user = await User.findById(decoded.sub);
    if (!user) {
      return next(new AppError('User not found', 401));
    }

    if (!user.isActive) {
      return next(new AppError('User account is deactivated', 401));
    }

    req.user = user;
    next();
  } catch (error) {
    logger.error('Auth middleware error:', error);
    return next(new AppError('Invalid token', 401));
  }
};

const restrictTo =
  (...roles) =>
  (req, res, next) => {
    if (appConfig.isAuthDisabled()) {
      return next();
    }
    if (!req.user) {
      return next(new AppError('Not authenticated', 401));
    }
    if (!roles.includes(req.user.role)) {
      return next(new AppError('Insufficient permissions', 403));
    }
    next();
  };

module.exports = { protect, restrictTo };
