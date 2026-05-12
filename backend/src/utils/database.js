const path = require('path');
const dotenv = require('dotenv');

// Load backend/.env explicitly (not only cwd) so Prisma sees variables before PrismaClient is constructed.
dotenv.config({ path: path.join(__dirname, '..', '..', '.env') });

if (!process.env.DATABASE_URL) {
  if (process.env.NODE_ENV === 'production') {
    // eslint-disable-next-line no-console
    console.error('DATABASE_URL is required in production. Set it in backend/.env');
    process.exit(1);
  }
  process.env.DATABASE_URL = 'file:./dev.db';
}

const { PrismaClient } = require('@prisma/client');
const { execSync } = require('child_process');
const logger = require('./logger');

class Database {
  constructor() {
    this.prisma = new PrismaClient({
      log:
        process.env.NODE_ENV === 'development'
          ? ['warn', 'error']
          : ['error'],
      errorFormat: 'pretty',
    });
  }

  async connect() {
    try {
      await this.prisma.$connect();
      logger.info('Database connected successfully');

      if (process.env.NODE_ENV === 'production' && process.env.RUN_MIGRATIONS_ON_BOOT === 'true') {
        await this.runMigrations();
      }
    } catch (error) {
      logger.error('Database connection failed:', error);
      process.exit(1);
    }
  }

  async disconnect() {
    await this.prisma.$disconnect();
  }

  async runMigrations() {
    try {
      execSync('npx prisma migrate deploy', { stdio: 'inherit', env: process.env });
      logger.info('Database migrations applied');
    } catch (e) {
      logger.error('Migration deploy failed', e);
      throw e;
    }
  }

  async healthCheck() {
    try {
      await this.prisma.$queryRaw`SELECT 1`;
      return { status: 'healthy', timestamp: new Date().toISOString() };
    } catch (error) {
      return { status: 'unhealthy', error: error.message };
    }
  }
}

module.exports = new Database();
