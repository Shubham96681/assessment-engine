const db = require('../utils/database');
const { AppError } = require('../middleware/error.middleware');
const { asStringArray } = require('../utils/json-array');

function setsEqual(a, b) {
  if (!a || !b || a.length !== b.length) return false;
  const sa = [...new Set(a)].sort();
  const sb = [...new Set(b)].sort();
  return sa.every((v, i) => v === sb[i]);
}

class GradingService {
  async autoGradeObjectiveQuestions(attemptId) {
    const attempt = await db.prisma.testAttempt.findUnique({
      where: { id: attemptId },
      include: {
        test: { include: { testQuestions: { include: { question: { include: { options: true } } } } } },
      },
    });
    if (!attempt) throw new AppError('Attempt not found', 404);

    const answers = await db.prisma.studentAnswer.findMany({ where: { attemptId } });
    const byQuestion = new Map(answers.map((a) => [a.questionId, a]));

    let total = 0;
    const subjective = [];

    for (const tq of attempt.test.testQuestions) {
      const q = tq.question;
      const sa = byQuestion.get(q.id);
      const allocated = Number(tq.marks);
      if (!sa) continue;

      if (['mcq', 'true_false'].includes(q.questionType)) {
        const correctIds = q.options.filter((o) => o.isCorrect).map((o) => o.id);
        const correct = setsEqual(asStringArray(sa.selectedOptions), correctIds);
        const marks = correct ? allocated : 0;
        total += marks;
        await db.prisma.studentAnswer.update({
          where: { id: sa.id },
          data: {
            isCorrect: correct,
            marksObtained: marks,
            marksAllocated: allocated,
          },
        });
      } else if (q.questionType === 'fill_blank') {
        const expected = (q.questionData && q.questionData.expected) || '';
        const given = (sa.answer || '').trim().toLowerCase();
        const ok = expected && given === String(expected).trim().toLowerCase();
        const marks = ok ? allocated : 0;
        total += marks;
        await db.prisma.studentAnswer.update({
          where: { id: sa.id },
          data: {
            isCorrect: ok,
            marksObtained: marks,
            marksAllocated: allocated,
          },
        });
      } else {
        subjective.push(q.id);
        await db.prisma.studentAnswer.update({
          where: { id: sa.id },
          data: { marksAllocated: allocated },
        });
      }
    }

    if (subjective.length) {
      const exists = await db.prisma.gradingQueue.findFirst({
        where: { attemptId, status: { in: ['pending', 'processing'] } },
      });
      if (!exists) {
        await db.prisma.gradingQueue.create({
          data: { attemptId, status: 'pending', priority: 0 },
        });
      }
    }

    const final = await this.calculateFinalScore(attemptId);
    return final;
  }

  async getGradingQueue(teacherId) {
    const user = await db.prisma.user.findUnique({ where: { id: teacherId } });
    const items = await db.prisma.gradingQueue.findMany({
      where: { status: 'pending' },
      include: {
        attempt: {
          include: {
            test: { include: { subject: true } },
            student: { select: { id: true, firstName: true, lastName: true, email: true } },
          },
        },
      },
      orderBy: [{ priority: 'desc' }, { createdAt: 'asc' }],
      take: 50,
    });
    if (user?.role === 'teacher' && user.schoolId) {
      return items.filter((i) => i.attempt.test.subjectId && i.attempt.student?.schoolId === user.schoolId);
    }
    return items;
  }

  async gradeSubjectiveQuestion(attemptId, questionId, gradeData, graderId) {
    const sa = await db.prisma.studentAnswer.findFirst({
      where: { attemptId, questionId },
    });
    if (!sa) throw new AppError('Answer not found', 404);

    await db.prisma.studentAnswer.update({
      where: { id: sa.id },
      data: {
        marksObtained: gradeData.marksObtained,
        feedback: gradeData.feedback,
        gradedBy: graderId,
        gradedAt: new Date(),
      },
    });

    return this.calculateFinalScore(attemptId);
  }

  async calculateFinalScore(attemptId) {
    const attempt = await db.prisma.testAttempt.findUnique({
      where: { id: attemptId },
      include: {
        test: true,
        studentAnswers: true,
      },
    });

    const pending = attempt.studentAnswers.filter((a) => a.marksObtained == null && a.marksAllocated != null);
    const hasSubjectivePending = pending.length > 0;

    let total = 0;
    for (const a of attempt.studentAnswers) {
      if (a.marksObtained != null) total += Number(a.marksObtained);
    }

    const percentage = attempt.test.totalMarks
      ? Math.round((total / attempt.test.totalMarks) * 10000) / 100
      : 0;
    const passed =
      attempt.test.passingMarks != null ? total >= attempt.test.passingMarks : percentage >= 40;

    const status = hasSubjectivePending ? 'submitted' : 'graded';

    return db.prisma.testAttempt.update({
      where: { id: attemptId },
      data: {
        totalScore: total,
        percentage,
        passed,
        status,
      },
    });
  }
}

module.exports = new GradingService();
