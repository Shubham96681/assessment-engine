const db = require('../utils/database');

async function findBook(id) {
  return db.prisma.book.findFirst({ where: { id, deletedAt: null } });
}

async function findQuestionPaper(id) {
  return db.prisma.questionPaper.findFirst({ where: { id, deletedAt: null } });
}

module.exports = { findBook, findQuestionPaper };
