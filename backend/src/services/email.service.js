const { sendMail } = require('../utils/email');
const logger = require('../utils/logger');

class EmailService {
  async sendWelcomeEmail(to, firstName) {
    try {
      await sendMail({
        to,
        subject: 'Welcome to Assessment Engine',
        text: `Hi ${firstName}, your account is ready.`,
      });
    } catch (e) {
      logger.warn('sendWelcomeEmail failed', e.message);
    }
  }

  async sendPasswordReset(to, resetUrl) {
    try {
      await sendMail({
        to,
        subject: 'Password reset',
        text: `Reset your password: ${resetUrl}`,
      });
    } catch (e) {
      logger.warn('sendPasswordReset failed', e.message);
    }
  }
}

module.exports = new EmailService();
