const db = require('../utils/database');

async function findTest(id) {
  return db.prisma.test.findFirst({
    where: { id, deletedAt: null },
    include: { testQuestions: { include: { question: true } }, subject: true },
  });
}

module.exports = { findTest };
