const appConfig = require('./app.config');

module.exports = {
  host: appConfig.redis.host,
  port: appConfig.redis.port,
  password: appConfig.redis.password,
  db: appConfig.redis.db,
  maxRetriesPerRequest: null,
  enableReadyCheck: false,
};
