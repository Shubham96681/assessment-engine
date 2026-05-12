const db = require('../utils/database');
const { queueEmail } = require('../jobs/email-notification.job');

function emitToUser(userId, event, payload) {
  const io = global.io;
  if (io) {
    io.to(`user:${userId}`).emit(event, payload);
  }
}

class NotificationService {
  async sendEmailNotification(userId, template, data) {
    const user = await db.prisma.user.findUnique({ where: { id: userId } });
    if (!user) return;
    const subject = template === 'welcome' ? 'Welcome' : 'Notification';
    const text = typeof data === 'object' ? JSON.stringify(data) : String(data);
    await queueEmail({ to: user.email, subject, text });
  }

  async createInAppNotification(userId, notificationData) {
    const n = await db.prisma.notification.create({
      data: {
        userId,
        type: notificationData.type || 'info',
        title: notificationData.title,
        message: notificationData.message,
        data: notificationData.data || {},
      },
    });
    emitToUser(userId, 'notification', n);
    return n;
  }

  async sendSMSNotification(phoneNumber, message) {
    return { skipped: true, reason: 'SMS provider not configured', phoneNumber, message };
  }

  async scheduleNotification(notificationData, scheduleTime) {
    const { getEmailQueue } = require('../jobs/email-notification.job');
    const delay = Math.max(0, new Date(scheduleTime).getTime() - Date.now());
    try {
      const q = getEmailQueue();
      if (q) await q.add(notificationData, { delay, removeOnComplete: true });
    } catch {
      /* optional queue */
    }
    return { scheduled: true, scheduleTime };
  }

  async listForUser(userId, query) {
    const take = Math.min(100, parseInt(query.limit, 10) || 20);
    return db.prisma.notification.findMany({
      where: { userId },
      orderBy: { createdAt: 'desc' },
      take,
    });
  }

  async markRead(userId, id) {
    return db.prisma.notification.updateMany({
      where: { id, userId },
      data: { isRead: true, readAt: new Date() },
    });
  }

  async notifyClassSchedule(testId, classId, actorUserId) {
    const enrollments = await db.prisma.studentEnrollment.findMany({
      where: { classId },
      select: { studentId: true },
    });
    const test = await db.prisma.test.findUnique({ where: { id: testId }, select: { title: true } });
    for (const e of enrollments) {
      await this.createInAppNotification(e.studentId, {
        type: 'schedule',
        title: 'New test schedule',
        message: `Test "${test?.title || testId}" scheduled for your class.`,
        data: { testId, classId, actorUserId },
      });
    }
  }
}

module.exports = new NotificationService();
