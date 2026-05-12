const notificationService = require('../services/notification.service');

exports.list = async (req, res, next) => {
  try {
    const rows = await notificationService.listForUser(req.user.id, req.query);
    res.json({ status: 'success', data: rows });
  } catch (e) {
    next(e);
  }
};

exports.markRead = async (req, res, next) => {
  try {
    await notificationService.markRead(req.user.id, req.params.id);
    res.json({ status: 'success' });
  } catch (e) {
    next(e);
  }
};

exports.sendTest = async (req, res, next) => {
  try {
    await notificationService.sendEmailNotification(req.params.userId, req.body.template || 'generic', req.body.data);
    res.json({ status: 'success' });
  } catch (e) {
    next(e);
  }
};
