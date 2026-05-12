const authService = require('../services/auth.service');
const { AppError } = require('../middleware/error.middleware');

exports.register = async (req, res, next) => {
  try {
    const result = await authService.register(req.body);
    res.status(201).json({ status: 'success', ...result });
  } catch (e) {
    next(e);
  }
};

exports.login = async (req, res, next) => {
  try {
    const result = await authService.login(req.body);
    res.json({ status: 'success', ...result });
  } catch (e) {
    next(e);
  }
};

exports.refreshToken = async (req, res, next) => {
  try {
    const token = req.body.refreshToken;
    if (!token) return next(new AppError('refreshToken required', 400));
    const result = await authService.refreshToken(token);
    res.json({ status: 'success', ...result });
  } catch (e) {
    next(e);
  }
};

exports.logout = async (req, res, next) => {
  try {
    await authService.logout(req.body.refreshToken);
    res.json({ status: 'success', message: 'Logged out' });
  } catch (e) {
    next(e);
  }
};

exports.forgotPassword = async (req, res, next) => {
  try {
    const result = await authService.forgotPassword(req.body.email);
    res.json({ status: 'success', ...result });
  } catch (e) {
    next(e);
  }
};

exports.resetPassword = async (req, res, next) => {
  try {
    const result = await authService.resetPassword(req.body.token, req.body.password);
    res.json({ status: 'success', ...result });
  } catch (e) {
    next(e);
  }
};
