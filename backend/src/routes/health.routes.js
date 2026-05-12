const express = require('express');
const database = require('../utils/database');
const redis = require('../utils/redis');

const router = express.Router();

router.get('/', async (req, res) => {
  const health = {
    status: 'ok',
    timestamp: new Date().toISOString(),
    services: {
      database: await database.healthCheck(),
      redis: await redis.healthCheck(),
    },
  };

  const dbOk = health.services.database.status === 'healthy';
  const redisOk =
    health.services.redis.status === 'healthy' ||
    health.services.redis.status === 'skipped';
  health.status = dbOk && redisOk ? 'ok' : 'error';

  res.status(health.status === 'ok' ? 200 : 503).json(health);
});

module.exports = router;
