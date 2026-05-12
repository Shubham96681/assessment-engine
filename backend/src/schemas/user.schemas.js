const Joi = require('joi');
const { emailString } = require('./email.schema');

const userSchemas = {
  updateProfile: Joi.object({
    firstName: Joi.string().min(2).max(50),
    lastName: Joi.string().min(2).max(50),
    phone: Joi.string().allow('', null),
    profilePictureUrl: Joi.string().uri().allow('', null),
    settings: Joi.object(),
  }),

  listUsers: Joi.object({
    page: Joi.number().integer().min(1),
    limit: Joi.number().integer().min(1).max(100),
    role: Joi.string(),
    schoolId: Joi.string().uuid(),
    search: Joi.string().max(200),
  }),

  assignRole: Joi.object({
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
  }),

  bulkImport: Joi.object({
    schoolId: Joi.string().uuid().required(),
    users: Joi.array().items(
      Joi.object({
        email: emailString().required(),
        firstName: Joi.string().required(),
        lastName: Joi.string().required(),
        role: Joi.string().valid('teacher', 'student').required(),
        password: Joi.string().min(8).optional(),
      })
    ).min(1).required(),
  }),
};

module.exports = { userSchemas };
