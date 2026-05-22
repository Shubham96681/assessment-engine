const Joi = require('joi');
const { emailString } = require('./email.schema');

const schoolSchemas = {
  create: Joi.object({
    name: Joi.string().min(2).max(255).required(),
    code: Joi.string().min(2).max(50).required(),
    domain: Joi.string().allow('', null),
    contactEmail: Joi.alternatives().try(Joi.string().valid(''), Joi.valid(null), emailString()).optional(),
    contactPhone: Joi.string().allow('', null),    address: Joi.string().allow('', null),
  }),

  update: Joi.object({
    name: Joi.string().min(2).max(255),
    domain: Joi.string().allow('', null),
    logoUrl: Joi.string().uri().allow('', null),
    contactEmail: Joi.alternatives().try(Joi.string().valid(''), Joi.valid(null), emailString()).optional(),
    contactPhone: Joi.string().allow('', null),
    address: Joi.string().allow('', null),
    subscriptionPlan: Joi.string(),
    subscriptionStatus: Joi.string(),
    settings: Joi.object(),
  }),
};

module.exports = { schoolSchemas };
