const Bull = require('bull');
const redisConfig = require('../config/redis.config');
const logger = require('../utils/logger');
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

let analyticsQueue;

function getAnalyticsQueue() {
  if (!isRedisAvailable()) return null;
  if (!analyticsQueue) {
    analyticsQueue = new Bull('analytics-calculation', { redis: connection });
    analyticsQueue.process(async (job) => {
      const AnalyticsService = require('../services/analytics.service');
      logger.info('Analytics job', job.data);
      if (job.data.testId) {
        await AnalyticsService.refreshTestMetrics(job.data.testId);
      }
    });
  }
  return analyticsQueue;
}

module.exports = { getAnalyticsQueue };
