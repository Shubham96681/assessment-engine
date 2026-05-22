const { AppError } = require('./error.middleware');

const validateRequest = (schema, property = 'body') => (req, res, next) => {
  const { error, value } = schema.validate(req[property], {
    abortEarly: true,
    stripUnknown: true,
    convert: true,
  });
  if (error) {
    return next(new AppError(error.details[0].message, 400));
  }
  req[property] = value;
  next();
};

module.exports = validateRequest;
