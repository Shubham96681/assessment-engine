const db = require('../utils/database');

async function findQuestion(id) {
  return db.prisma.question.findFirst({
    where: { id, deletedAt: null },
    include: { options: true, answers: true, rubrics: true },
  });
}

module.exports = { findQuestion };
