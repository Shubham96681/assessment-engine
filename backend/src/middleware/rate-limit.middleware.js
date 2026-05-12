const rateLimit = require('express-rate-limit');
const RedisStore = require('rate-limit-redis').default || require('rate-limit-redis');
const { getRedis } = require('../utils/redis');
const logger = require('../utils/logger');

function buildStore(prefix) {
  if (process.env.NODE_ENV === 'test') return undefined;
  const redis = getRedis();
  if (!redis) return undefined;
  try {
    return new RedisStore({
      sendCommand: (...args) => redis.call(args[0], ...args.slice(1)),
      prefix: prefix || 'rl:',
    });
  } catch (e) {
    logger.warn('Redis rate limit store unavailable', e.message);
    return undefined;
  }
}

const createRateLimiter = (windowMs, max, message) =>
  rateLimit({
    store: buildStore('rl:'),
    windowMs,
    max,
    message: { status: 'error', message },
    standardHeaders: true,
    legacyHeaders: false,
    skip: () => process.env.NODE_ENV === 'test',
  });

const authLimiter = createRateLimiter(15 * 60 * 1000, 50, 'Too many auth attempts');
const generalLimiter = createRateLimiter(15 * 60 * 1000, 500, 'Too many requests');
const uploadLimiter = createRateLimiter(60 * 60 * 1000, 30, 'Too many upload attempts');

module.exports = { authLimiter, generalLimiter, uploadLimiter, createRateLimiter };
