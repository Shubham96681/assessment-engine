const Bull = require('bull');
const redisConfig = require('../config/redis.config');
const { isRedisAvailable } = require('../utils/redis');

const connection = {
  host: redisConfig.host,
  port: redisConfig.port,
  password: redisConfig.password || undefined,
  db: redisConfig.db,
  maxRetriesPerRequest: null,
  enableReadyCheck: false,
  enableOfflineQueue: false,
  retryStrategy() {
    return null;
  },
};

let emailQueue;

function getEmailQueue() {
  if (!isRedisAvailable()) return null;
  if (!emailQueue) {
    emailQueue = new Bull('email-notification', { redis: connection });
    emailQueue.process(async (job) => {
      const { to, subject, text } = job.data;
      const { sendMail } = require('../utils/email');
      await sendMail({ to, subject, text });
    });
  }
  return emailQueue;
}

async function queueEmail(payload) {
  const q = getEmailQueue();
  if (!q) {
    const { sendMail } = require('../utils/email');
    await sendMail(payload).catch(() => {});
    return;
  }
  try {
    await q.add(payload, { removeOnComplete: true });
  } catch {
    const { sendMail } = require('../utils/email');
    await sendMail(payload).catch(() => {});
  }
}

module.exports = { getEmailQueue, queueEmail };
