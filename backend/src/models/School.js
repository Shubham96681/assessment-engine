const db = require('../utils/database');

async function findById(id) {
  return db.prisma.school.findFirst({ where: { id, deletedAt: null } });
}

async function findByCode(code) {
  return db.prisma.school.findFirst({ where: { code, deletedAt: null } });
}

module.exports = { findById, findByCode };
