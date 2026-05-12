const Joi = require('joi');

/** Joi email that allows reserved TLDs like `.test`, `.localhost` (seed / local dev). */
function emailString() {
  return Joi.string().email({ tlds: false });
}

module.exports = { emailString };
