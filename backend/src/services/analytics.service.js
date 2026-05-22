const db = require('../utils/database');
const { AppError } = require('../middleware/error.middleware');
const { asStringArray } = require('../utils/json-array');

class AnalyticsService {
  async refreshTestMetrics(testId) {
    const attempts = await db.prisma.testAttempt.findMany({
      where: { testId, status: { in: ['graded', 'submitted', 'auto_submitted'] } },
    });
    const scores = attempts.map((a) => Number(a.totalScore || 0)).filter((n) => !Number.isNaN(n));
    const avg = scores.length ? scores.reduce((s, n) => s + n, 0) / scores.length : 0;
    const test = await db.prisma.test.findUnique({ where: { id: testId } });
    if (!test) return;
    await db.prisma.performanceMetric.create({
      data: {
        schoolId: test.schoolId,
        testId,
        metricType: 'test_avg_score',
        metricValue: avg,
        additionalData: { attempts: scores.length },
      },
    });
  }

  async getTestAnalytics(testId) {
    const test = await db.prisma.test.findFirst({ where: { id: testId, deletedAt: null } });
    if (!test) throw new AppError('Test not found', 404);

    const attempts = await db.prisma.testAttempt.findMany({
      where: { testId, status: { in: ['graded', 'submitted', 'auto_submitted'] } },
    });
    const scores = attempts.map((a) => Number(a.totalScore || 0));
    const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
    const passCount = attempts.filter((a) => a.passed).length;

    return {
      testId,
      attemptCount: attempts.length,
      averageScore: avg,
      passRate: attempts.length ? passCount / attempts.length : 0,
      distribution: {
        min: scores.length ? Math.min(...scores) : null,
        max: scores.length ? Math.max(...scores) : null,
      },
    };
  }

  async getStudentPerformance(studentId) {
    const attempts = await db.prisma.testAttempt.findMany({
      where: { studentId },
      include: { test: { select: { title: true, id: true, totalMarks: true } } },
      orderBy: { endTime: 'desc' },
      take: 50,
    });
    return { studentId, attempts };
  }

  async getClassPerformance(classId, subjectId, timeframe) {
    const whereTest = { deletedAt: null };
    if (timeframe?.from) whereTest.startTime = { gte: new Date(timeframe.from) };
    const testsAll = await db.prisma.test.findMany({
      where: {
        ...whereTest,
        subjectId: subjectId || undefined,
      },
      take: 50,
    });
    const tests = testsAll.filter((t) => asStringArray(t.classIds).includes(classId)).slice(0, 20);
    const ids = tests.map((t) => t.id);
    const attempts = await db.prisma.testAttempt.findMany({
      where: { testId: { in: ids }, status: { in: ['graded', 'submitted', 'auto_submitted'] } },
    });
    const avg =
      attempts.length > 0
        ? attempts.reduce((s, a) => s + Number(a.totalScore || 0), 0) / attempts.length
        : 0;
    return { classId, subjectId, averageScore: avg, sampleSize: attempts.length };
  }

  async generateReport(reportType, filters) {
    if (reportType === 'test_summary' && filters.testId) {
      return this.getTestAnalytics(filters.testId);
    }
    if (reportType === 'student' && filters.studentId) {
      return this.getStudentPerformance(filters.studentId);
    }
    return { reportType, message: 'Unsupported report type' };
  }
}

module.exports = new AnalyticsService();
