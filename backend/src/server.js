const http = require('http');
const { Server } = require('socket.io');
const config = require('./config/app.config');
const database = require('./utils/database');
const { connectRedis, disconnectRedis } = require('./utils/redis');
const logger = require('./utils/logger');

async function bootstrap() {
  await database.connect();
  await connectRedis();

  const app = require('./app');

  const server = http.createServer(app);
  const io = new Server(server, {
    cors: { origin: true, credentials: true },
  });

  global.io = io;

  io.use((socket, next) => {
    const token = socket.handshake.auth?.token;
    if (!token) {
      return next();
    }
    try {
      const jwt = require('jsonwebtoken');
      const payload = jwt.verify(token, config.jwt.secret);
      socket.userId = payload.sub;
      return next();
    } catch {
      return next();
    }
  });

  io.on('connection', (socket) => {
    if (socket.userId) {
      socket.join(`user:${socket.userId}`);
    }
    socket.emit('ready', { ok: true });
  });

  const port = config.app.port;
  server.listen(port, () => {
    logger.info(`${config.app.name} listening on port ${port}`);
  });

  const shutdown = async () => {
    logger.info('Shutting down...');
    await disconnectRedis();
    await database.disconnect();
    server.close(() => process.exit(0));
  };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

bootstrap().catch((err) => {
  logger.error('Bootstrap failed', err);
  process.exit(1);
});

module.exports = { bootstrap };
