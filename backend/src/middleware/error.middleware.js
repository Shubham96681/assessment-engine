const logger = require('../utils/logger');

class AppError extends Error {
  constructor(message, statusCode, isOperational = true) {
    super(message);
    this.statusCode = statusCode;
    this.isOperational = isOperational;
    this.status = `${statusCode}`.startsWith('4') ? 'fail' : 'error';
    Error.captureStackTrace(this, this.constructor);
  }
}

const errorHandler = (err, req, res, next) => {
  let statusCode = err.statusCode || 500;
  let message = err.message || 'Internal server error';
  let status = err.status || 'error';

  logger.error(err);

  if (err.code === 'P2002') {
    statusCode = 400;
    message = 'Duplicate field value entered';
    status = 'fail';
  }
  if (err.code === 'P2025') {
    statusCode = 404;
    message = 'Record not found';
    status = 'fail';
  }

  if (err.name === 'JsonWebTokenError') {
    statusCode = 401;
    message = 'Invalid token';
    status = 'fail';
  }
  if (err.name === 'TokenExpiredError') {
    statusCode = 401;
    message = 'Token expired';
    status = 'fail';
  }

  if (err.isJoi) {
    statusCode = 400;
    message = err.details[0].message;
    status = 'fail';
  }

  res.status(statusCode).json({
    status,
    message,
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack }),
  });
};

const notFound = (req, res, next) => {
  next(new AppError(`Route ${req.originalUrl} not found`, 404));
};

module.exports = { AppError, errorHandler, notFound };
