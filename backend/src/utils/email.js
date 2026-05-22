const nodemailer = require('nodemailer');
const appConfig = require('../config/app.config');
const logger = require('./logger');

let transporter;

function getTransporter() {
  if (transporter) return transporter;
  if (!appConfig.email.host) {
    return null;
  }
  transporter = nodemailer.createTransport({
    host: appConfig.email.host,
    port: appConfig.email.port,
    secure: appConfig.email.port === 465,
    auth:
      appConfig.email.user && appConfig.email.pass
        ? { user: appConfig.email.user, pass: appConfig.email.pass }
        : undefined,
  });
  return transporter;
}

async function sendMail({ to, subject, text, html }) {
  const t = getTransporter();
  if (!t) {
    logger.info('Email skipped (not configured)', { to, subject });
    return { skipped: true };
  }
  return t.sendMail({
    from: appConfig.email.from,
    to,
    subject,
    text,
    html,
  });
}

module.exports = {
  sendMail,
};
