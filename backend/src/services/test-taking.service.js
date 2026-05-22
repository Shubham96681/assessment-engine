const db = require('../utils/database');
const { AppError } = require('../middleware/error.middleware');

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

class TestTakingService {
  async startTest(testId, studentId) {
    const test = await db.prisma.test.findFirst({
      where: { id: testId, deletedAt: null },
      include: { testQuestions: { include: { question: { include: { options: true } } } } },
    });
    if (!test) throw new AppError('Test not found', 404);
    if (test.status !== 'published') {
      throw new AppError('Test is not available', 400);
    }
    const now = new Date();
    if (now < test.startTime || now > test.endTime) {
      throw new AppError('Test is outside the allowed window', 400);
    }

    const attemptCount = await db.prisma.testAttempt.count({
      where: { testId, studentId, status: { in: ['submitted', 'auto_submitted', 'graded'] } },
    });
    if (attemptCount >= test.maxAttempts) {
      throw new AppError('Maximum attempts reached', 400);
    }

    const open = await db.prisma.testAttempt.findFirst({
      where: { testId, studentId, status: 'in_progress' },
    });
    if (open) {
      throw new AppError('You already have an attempt in progress', 400);
    }

    let questions = test.testQuestions.map((tq) => ({
      testQuestionId: tq.id,
      questionId: tq.questionId,
      marks: tq.marks,
      question: tq.question,
    }));
    if (test.shuffleQuestions) {
      questions = shuffle(questions);
    }
    if (test.shuffleOptions) {
      questions = questions.map((q) => ({
        ...q,
        question: {
          ...q.question,
          options: shuffle(q.question.options || []),
        },
      }));
    }

    const attempt = await db.prisma.testAttempt.create({
      data: {
        testId,
        studentId,
        status: 'in_progress',
        answers: {},
      },
    });

    return { attempt, questions };
  }

  async submitAnswer(attemptId, questionId, payload, studentId) {
    const attempt = await db.prisma.testAttempt.findFirst({
      where: { id: attemptId, studentId },
      include: { test: true },
    });
    if (!attempt) throw new AppError('Attempt not found', 404);
    if (attempt.status !== 'in_progress') {
      throw new AppError('Attempt is closed', 400);
    }

    const end = attempt.test.endTime;
    if (new Date() > end) {
      throw new AppError('Time expired', 400);
    }

    const data = {
      attemptId,
      questionId,
      answer: payload.answer ?? null,
      selectedOptions: payload.selectedOptions || [],
      answerFileUrl: payload.answerFileUrl || null,
      timeSpentSeconds: payload.timeSpentSeconds,
    };

    const existing = await db.prisma.studentAnswer.findFirst({
      where: { attemptId, questionId },
    });
    const base = {
      answer: data.answer,
      selectedOptions: data.selectedOptions,
      answerFileUrl: data.answerFileUrl,
      timeSpentSeconds: data.timeSpentSeconds,
    };
    if (existing) {
      await db.prisma.studentAnswer.update({
        where: { id: existing.id },
        data: base,
      });
    } else {
      await db.prisma.studentAnswer.create({
        data: { ...data },
      });
    }

    const answers = { ...(attempt.answers || {}) };
    answers[questionId] = payload;
    await db.prisma.testAttempt.update({
      where: { id: attemptId },
      data: { answers },
    });

    return { saved: true };
  }

  async submitTest(attemptId, studentId) {
    const attempt = await db.prisma.testAttempt.findFirst({
      where: { id: attemptId, studentId },
      include: { test: { include: { testQuestions: { include: { question: { include: { options: true } } } } } } },
    });
    if (!attempt) throw new AppError('Attempt not found', 404);
    if (attempt.status !== 'in_progress') {
      throw new AppError('Attempt is already closed', 400);
    }

    await db.prisma.testAttempt.update({
      where: { id: attemptId },
      data: {
        status: 'submitted',
        endTime: new Date(),
      },
    });

    const GradingService = require('./grading.service');
    await GradingService.autoGradeObjectiveQuestions(attemptId);

    return db.prisma.testAttempt.findUnique({ where: { id: attemptId } });
  }

  async autoSubmitTest(attemptId) {
    await db.prisma.testAttempt.update({
      where: { id: attemptId },
      data: { status: 'auto_submitted', endTime: new Date() },
    });
    const GradingService = require('./grading.service');
    await GradingService.autoGradeObjectiveQuestions(attemptId);
    return db.prisma.testAttempt.findUnique({ where: { id: attemptId } });
  }
}

module.exports = new TestTakingService();
