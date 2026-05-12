const db = require('../utils/database');
const { AppError } = require('../middleware/error.middleware');
const { parsePagination, buildMeta } = require('../utils/helpers');

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function normUuid(v) {
  if (v == null || v === '') return null;
  const s = String(v).trim();
  return UUID_RE.test(s) ? s : null;
}

class QuestionService {
  async createQuestion(questionData, createdBy) {
    const user = await db.prisma.user.findUnique({ where: { id: createdBy } });
    if (!user?.schoolId) throw new AppError('User must belong to a school', 400);

    const { options, ...core } = questionData;

    return db.prisma.$transaction(async (tx) => {
      const q = await tx.question.create({
        data: {
          ...core,
          schoolId: user.schoolId,
          createdBy,
          questionMedia: core.questionMedia || [],
        },
      });
      if (options?.length) {
        for (const o of options) {
          await tx.questionOption.create({
            data: {
              questionId: q.id,
              optionText: o.optionText,
              isCorrect: o.isCorrect,
              optionOrder: o.optionOrder,
              explanation: o.explanation || null,
            },
          });
        }
      }
      return tx.question.findUnique({
        where: { id: q.id },
        include: { options: true, answers: true, rubrics: true },
      });
    });
  }

  async getQuestions(filters, schoolId) {
    const { page, limit, skip } = parsePagination(filters);
    const where = { deletedAt: null, schoolId };
    if (filters.questionType) where.questionType = filters.questionType;
    if (filters.subjectId) where.subjectId = filters.subjectId;
    const srcId = normUuid(filters.sourceResourceId);
    if (srcId) {
      where.sourceResourceId = srcId;
      if (filters.sourceResourceType && ['book', 'question_paper'].includes(String(filters.sourceResourceType))) {
        where.sourceResourceType = String(filters.sourceResourceType);
      }
    }
    if (filters.difficulty) where.difficulty = filters.difficulty;
    if (filters.search) {
      where.questionText = { contains: filters.search, mode: 'insensitive' };
    }

    const [total, rows] = await Promise.all([
      db.prisma.question.count({ where }),
      db.prisma.question.findMany({
        where,
        skip,
        take: limit,
        orderBy: { updatedAt: 'desc' },
        include: { options: true, subject: true },
      }),
    ]);
    return { data: rows, meta: buildMeta(total, page, limit) };
  }

  /**
   * Distinct topics, tags, and chapters from the school's question bank (for UI filters).
   * Limited scan for performance; suitable for dev / moderate banks.
   */
  async getBankFilterAggregates(schoolId) {
    const rows = await db.prisma.question.findMany({
      where: { schoolId, deletedAt: null },
      select: { topics: true, tags: true, chapter: true },
      take: 10000,
    });

    const topicCounts = new Map();
    const tagCounts = new Map();
    const chapterCounts = new Map();

    for (const r of rows) {
      const topicArr = Array.isArray(r.topics) ? r.topics : [];
      for (const t of topicArr) {
        const s = typeof t === 'string' ? t.trim() : String(t).trim();
        if (s && s.length <= 200) topicCounts.set(s, (topicCounts.get(s) || 0) + 1);
      }
      const tagArr = Array.isArray(r.tags) ? r.tags : [];
      for (const t of tagArr) {
        const s = typeof t === 'string' ? t.trim() : String(t).trim();
        if (s && s.length <= 120) tagCounts.set(s, (tagCounts.get(s) || 0) + 1);
      }
      if (r.chapter) {
        const c = String(r.chapter).trim();
        if (c && c.length <= 400) chapterCounts.set(c, (chapterCounts.get(c) || 0) + 1);
      }
    }

    const byCountThenName = (m) =>
      [...m.entries()]
        .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
        .map(([name]) => name);

    return {
      questionCount: rows.length,
      topics: byCountThenName(topicCounts).slice(0, 250),
      tagFilters: byCountThenName(tagCounts).slice(0, 100),
      chapters: byCountThenName(chapterCounts).slice(0, 200),
    };
  }

  async importQuestions(items, createdBy) {
    const report = { imported: 0, errors: [] };
    for (let i = 0; i < items.length; i += 1) {
      try {
        await this.createQuestion(items[i], createdBy);
        report.imported += 1;
      } catch (e) {
        report.errors.push({ index: i, message: e.message });
      }
    }
    return report;
  }

  async exportQuestions(filters, schoolId) {
    const { data } = await this.getQuestions({ ...filters, page: 1, limit: 5000 }, schoolId);
    return { format: 'json', questions: data };
  }
}

module.exports = new QuestionService();
