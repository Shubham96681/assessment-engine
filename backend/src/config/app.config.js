const path = require('path');
const dotenv = require('dotenv');

// Always load backend/.env (same path as database.js), not cwd — avoids missing vars when NODE starts from repo root.
dotenv.config({ path: path.join(__dirname, '..', '..', '.env') });

const config = {
  app: {
    name: process.env.APP_NAME || 'Assessment Engine',
    port: parseInt(process.env.PORT, 10) || 3000,
    env: process.env.NODE_ENV || 'development',
    url: process.env.APP_URL || 'http://localhost:3000',
  },

  database: {
    url: process.env.DATABASE_URL,
    ssl: process.env.NODE_ENV === 'production',
  },

  redis: {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT, 10) || 6379,
    password: process.env.REDIS_PASSWORD || undefined,
    db: parseInt(process.env.REDIS_DB, 10) || 0,
    url: process.env.REDIS_URL,
  },

  jwt: {
    secret: process.env.JWT_SECRET,
    expiresIn: process.env.JWT_EXPIRES_IN || '15m',
    refreshSecret: process.env.JWT_REFRESH_SECRET,
    refreshExpiresIn: process.env.JWT_REFRESH_EXPIRES_IN || '7d',
  },

  aws: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
    region: process.env.AWS_REGION || 'us-east-1',
    s3Bucket: process.env.AWS_S3_BUCKET,
    endpoint: process.env.AWS_S3_ENDPOINT || undefined,
    forcePathStyle: process.env.AWS_S3_FORCE_PATH_STYLE === 'true',
  },

  email: {
    host: process.env.EMAIL_HOST,
    port: parseInt(process.env.EMAIL_PORT, 10) || 587,
    user: process.env.EMAIL_USER,
    pass: process.env.EMAIL_PASS,
    from: process.env.EMAIL_FROM,
  },

  /** Absolute path to local CBSE PDF tree; optional. */
  localCbseLibraryRoot: (process.env.LOCAL_CBSE_LIBRARY_ROOT || '').trim() || null,

  /** Email of user to impersonate when AUTH_DISABLED (must exist in DB). */
  authDisabledAsUserEmail: (process.env.AUTH_DISABLED_AS_USER || 'teacher@demo-school.test').trim().toLowerCase(),
};

/** Dev-only: skip JWT + roles. Evaluated at request time so env is always current. */
function isAuthDisabled() {
  const raw = process.env.AUTH_DISABLED;
  if (raw == null || String(raw).trim() === '') return false;
  const v = String(raw).trim().toLowerCase();
  return v === 'true' || v === '1' || v === 'yes';
}

module.exports = { ...config, isAuthDisabled };
