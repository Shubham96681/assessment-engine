const userService = require('../services/user.service');

exports.getMe = async (req, res, next) => {
  try {
    const { passwordHash, mfaSecret, ...user } = req.user;
    res.json({ status: 'success', data: user });
  } catch (e) {
    next(e);
  }
};

exports.updateProfile = async (req, res, next) => {
  try {
    const data = await userService.createProfile(req.user.id, req.body);
    res.json({ status: 'success', data });
  } catch (e) {
    next(e);
  }
};

exports.list = async (req, res, next) => {
  try {
    const result = await userService.getUsers(req.query, req.user);
    res.json({ status: 'success', ...result });
  } catch (e) {
    next(e);
  }
};

exports.updateUser = async (req, res, next) => {
  try {
    const data = await userService.updateUser(req.params.id, req.body, req.user);
    res.json({ status: 'success', data });
  } catch (e) {
    next(e);
  }
};

exports.assignRole = async (req, res, next) => {
  try {
    const data = await userService.assignRole(req.params.id, req.body.role, req.user);
    res.json({ status: 'success', data });
  } catch (e) {
    next(e);
  }
};

exports.bulkImport = async (req, res, next) => {
  try {
    const report = await userService.bulkImportUsers(req.body.users, req.body.schoolId, req.user);
    res.status(201).json({ status: 'success', report });
  } catch (e) {
    next(e);
  }
};
