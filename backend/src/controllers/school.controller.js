const schoolService = require('../services/school.service');

exports.create = async (req, res, next) => {
  try {
    const school = await schoolService.create(req.body);
    res.status(201).json({ status: 'success', data: school });
  } catch (e) {
    next(e);
  }
};

exports.list = async (req, res, next) => {
  try {
    const rows = await schoolService.list(req.user);
    res.json({ status: 'success', data: rows });
  } catch (e) {
    next(e);
  }
};

exports.getById = async (req, res, next) => {
  try {
    const school = await schoolService.getById(req.params.id);
    res.json({ status: 'success', data: school });
  } catch (e) {
    next(e);
  }
};

exports.update = async (req, res, next) => {
  try {
    const school = await schoolService.update(req.params.id, req.body);
    res.json({ status: 'success', data: school });
  } catch (e) {
    next(e);
  }
};

exports.users = async (req, res, next) => {
  try {
    const result = await schoolService.users(req.params.id, req.query);
    res.json({ status: 'success', ...result });
  } catch (e) {
    next(e);
  }
};
