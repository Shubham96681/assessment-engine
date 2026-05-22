const db = require('../utils/database');
const { AppError } = require('../middleware/error.middleware');
const { parsePagination, buildMeta } = require('../utils/helpers');
const notificationService = require('./notification.service');

class TestService {
  async createTest(testData, createdBy) {
    const user = await db.prisma.user.findUnique({ where: { id: createdBy } });
    if (!user?.schoolId) throw new AppError('User must belong to a school', 400);

    const { questionIds, ...rest } = testData;

    const test = await db.prisma.$transaction(async (tx) => {
      const t = await tx.test.create({
        data: {
          ...rest,
          schoolId: user.schoolId,
          createdBy,
          classIds: testData.classIds || [],
        },
      });

      if (questionIds?.length) {
        let order = 0;
        for (const q of questionIds) {
          await tx.testQuestion.create({
            data: {
              testId: t.id,
              questionId: q.questionId,
              questionOrder: q.questionOrder ?? order,
              marks: q.marks,
              isMandatory: q.isMandatory ?? true,
              sectionName: q.sectionName || null,
            },
          });
          order += 1;
        }
      }
      return t;
    });

    return this.getById(test.id);
  }

  async getById(id) {
    const test = await db.prisma.test.findFirst({
      where: { id, deletedAt: null },
      include: {
        testQuestions: { include: { question: { include: { options: true } } }, orderBy: { questionOrder: 'asc' } },
        subject: true,
        schedules: true,
      },
    });
    if (!test) throw new AppError('Test not found', 404);
    return test;
  }

  async list(filters, schoolId) {
    const { page, limit, skip } = parsePagination(filters);
    const where = { deletedAt: null, schoolId };
    if (filters.status) where.status = filters.status;
    if (filters.subjectId) where.subjectId = filters.subjectId;

    const [total, rows] = await Promise.all([
      db.prisma.test.count({ where }),
      db.prisma.test.findMany({
        where,
        skip,
        take: limit,
        orderBy: { createdAt: 'desc' },
        include: { subject: true },
      }),
    ]);
    return { data: rows, meta: buildMeta(total, page, limit) };
  }

  async addQuestionsToTest(testId, questions, requester) {
    const test = await this.getById(testId);
    if (test.createdBy !== requester.id && !['admin', 'school_admin'].includes(requester.role)) {
      throw new AppError('Forbidden', 403);
    }

    let order = test.testQuestions.length;
    await db.prisma.$transaction(async (tx) => {
      for (const q of questions) {
        await tx.testQuestion.create({
          data: {
            testId,
            questionId: q.questionId,
            questionOrder: q.questionOrder ?? order,
            marks: q.marks,
            isMandatory: q.isMandatory ?? true,
            sectionName: q.sectionName || null,
          },
        });
        order += 1;
      }
    });
    return this.getById(testId);
  }

  async scheduleTest(testId, scheduleData, requester) {
    await this.getById(testId);
    const schedule = await db.prisma.testSchedule.create({
      data: {
        testId,
        classId: scheduleData.classId,
        scheduledStartTime: scheduleData.scheduledStartTime,
        scheduledEndTime: scheduleData.scheduledEndTime,
      },
    });
    await notificationService.notifyClassSchedule(testId, scheduleData.classId, requester.id).catch(() => {});
    return schedule;
  }

  async publishTest(testId, requester) {
    const test = await this.getById(testId);
    if (test.createdBy !== requester.id && !['admin', 'school_admin'].includes(requester.role)) {
      throw new AppError('Forbidden', 403);
    }
    if (!test.testQuestions.length) {
      throw new AppError('Add at least one question before publishing', 400);
    }
    return db.prisma.test.update({
      where: { id: testId },
      data: { status: 'published' },
    });
  }

  async duplicateTest(testId, newTestData, requester) {
    const source = await this.getById(testId);
    const copy = await db.prisma.$transaction(async (tx) => {
      const t = await tx.test.create({
        data: {
          schoolId: source.schoolId,
          createdBy: requester.id,
          title: newTestData.title || `${source.title} (copy)`,
          description: source.description,
          subjectId: source.subjectId,
          classIds: source.classIds,
          durationMinutes: source.durationMinutes,
          totalMarks: source.totalMarks,
          passingMarks: source.passingMarks,
          instructions: source.instructions,
          questionSelectionMode: source.questionSelectionMode,
          shuffleQuestions: source.shuffleQuestions,
          shuffleOptions: source.shuffleOptions,
          showResultsImmediately: source.showResultsImmediately,
          allowReview: source.allowReview,
          maxAttempts: source.maxAttempts,
          showAnswersAfterTest: source.showAnswersAfterTest,
          negativeMarking: source.negativeMarking,
          negativeMarkingValue: source.negativeMarkingValue,
          startTime: newTestData.startTime || source.startTime,
          endTime: newTestData.endTime || source.endTime,
          status: 'draft',
          templateId: source.id,
          settings: source.settings || {},
        },
      });
      for (const tq of source.testQuestions) {
        await tx.testQuestion.create({
          data: {
            testId: t.id,
            questionId: tq.questionId,
            questionOrder: tq.questionOrder,
            marks: tq.marks,
            isMandatory: tq.isMandatory,
            sectionName: tq.sectionName,
          },
        });
      }
      return t;
    });
    return this.getById(copy.id);
  }
}

module.exports = new TestService();
