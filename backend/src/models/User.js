const db = require('../utils/database');

async function findById(id) {
  return db.prisma.user.findFirst({
    where: { id, deletedAt: null },
    include: { school: true },
  });
}

async function findByEmail(email) {
  return db.prisma.user.findFirst({
    where: { email: email.toLowerCase(), deletedAt: null },
    include: { school: true },
  });
}

module.exports = { findById, findByEmail };
