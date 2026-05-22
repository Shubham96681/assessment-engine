const Redis = require('ioredis');
const redisConfig = require('../config/redis.config');
const logger = require('./logger');

let client;

/** Shared Redis client is only created after a successful {@link connectRedis}. */
function getRedis() {
  return client || null;
}

function isRedisAvailable() {
  return !!client && client.status === 'ready';
}

function buildClientOptions() {
  return {
    ...redisConfig,
    lazyConnect: true,
    connectTimeout: 5000,
    maxRetriesPerRequest: null,
    enableReadyCheck: false,
    enableOfflineQueue: false,
    // Stop endless reconnect + log spam when Redis is not running (default caps at 2000ms).
    retryStrategy() {
      return null;
    },
  };
}

async function connectRedis() {
  if (process.env.REDIS_DISABLED === 'true') {
    logger.info('Redis disabled (REDIS_DISABLED=true); using in-memory rate limits and direct email sends.');
    return null;
  }

  let redis;
  try {
    redis = process.env.REDIS_URL
      ? new Redis(process.env.REDIS_URL, buildClientOptions())
      : new Redis(buildClientOptions());
  } catch (e) {
    logger.warn('Redis client init failed', e.message);
    return null;
  }

  redis.on('error', (err) => {
    logger.error('Redis error', err);
  });

  try {
    await redis.connect();
    client = redis;
    logger.info('Redis connected');
    return client;
  } catch (e) {
    logger.warn('Redis unavailable (optional in dev)', e.message);
    try {
      redis.removeAllListeners('error');
      redis.disconnect();
    } catch {
      /* ignore */
    }
    return null;
  }
}

async function healthCheck() {
  const r = getRedis();
  if (!r) return { status: 'skipped', message: 'Redis not connected' };
  try {
    const pong = await r.ping();
    return { status: pong === 'PONG' ? 'healthy' : 'unhealthy', timestamp: new Date().toISOString() };
  } catch (error) {
    return { status: 'unhealthy', error: error.message };
  }
}

async function disconnectRedis() {
  if (!client) return;
  try {
    client.removeAllListeners();
    await client.quit();
  } catch {
    try {
      client.disconnect();
    } catch {
      /* ignore */
    }
  }
  client = null;
}

module.exports = {
  getRedis,
  isRedisAvailable,
  connectRedis,
  disconnectRedis,
  healthCheck,
};
