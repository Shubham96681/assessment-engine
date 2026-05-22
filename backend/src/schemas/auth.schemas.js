const Joi = require('joi');
const { emailString } = require('./email.schema');

const passwordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/;

const authSchemas = {
  register: Joi.object({
    email: emailString().required(),
    password: Joi.string().min(8).pattern(passwordPattern).required(),
    firstName: Joi.string().min(2).max(50).required(),
    lastName: Joi.string().min(2).max(50).required(),
    role: Joi.string()
      .valid(
        'admin',
        'school_admin',
        'teacher',
        'student',
        'department_head',
        'librarian',
        'content_manager'
      )
      .required(),
    schoolCode: Joi.string().required(),
    phone: Joi.string().pattern(/^[+]?[\d\s\-()]+$/).optional(),
    dateOfBirth: Joi.date().optional(),
  }),

  login: Joi.object({
    email: emailString().required(),
    password: Joi.string().allow('', null).optional(),
    rememberMe: Joi.boolean().default(false),
  }),

  forgotPassword: Joi.object({
    email: emailString().required(),
  }),

  resetPassword: Joi.object({
    token: Joi.string().required(),
    password: Joi.string().min(8).pattern(passwordPattern).required(),
  }),

  refresh: Joi.object({
    refreshToken: Joi.string().required(),
  }),
};

module.exports = { authSchemas };
