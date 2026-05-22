const {
  S3Client,
  PutObjectCommand,
  GetObjectCommand,
} = require('@aws-sdk/client-s3');
const { getSignedUrl } = require('@aws-sdk/s3-request-presigner');
const { v4: uuidv4 } = require('uuid');
const s3Config = require('../config/s3.config');
const logger = require('./logger');

let s3Client;

function getS3() {
  if (s3Client) return s3Client;
  if (!s3Config.bucket) {
    return null;
  }
  s3Client = new S3Client({
    region: s3Config.region,
    credentials: s3Config.credentials,
    endpoint: s3Config.endpoint,
    forcePathStyle: s3Config.forcePathStyle,
  });
  return s3Client;
}

async function uploadBuffer({ key, body, contentType }) {
  const client = getS3();
  if (!client) {
    logger.warn('S3 not configured; skipping upload');
    return { url: null, key: key || uuidv4(), skipped: true };
  }
  const objectKey = key || `uploads/${uuidv4()}`;
  await client.send(
    new PutObjectCommand({
      Bucket: s3Config.bucket,
      Key: objectKey,
      Body: body,
      ContentType: contentType || 'application/octet-stream',
    })
  );
  const base = s3Config.endpoint || `https://${s3Config.bucket}.s3.${s3Config.region}.amazonaws.com`;
  const url = s3Config.endpoint ? `${s3Config.endpoint}/${s3Config.bucket}/${objectKey}` : `${base}/${objectKey}`;
  return { url, key: objectKey };
}

async function getSignedGetUrl(key, expiresIn = 3600) {
  const client = getS3();
  if (!client) return null;
  const cmd = new GetObjectCommand({ Bucket: s3Config.bucket, Key: key });
  return getSignedUrl(client, cmd, { expiresIn });
}

async function getObjectBuffer(key) {
  const client = getS3();
  if (!client || !s3Config.bucket || !key) {
    throw new Error('S3 is not configured or object key is missing');
  }
  const out = await client.send(
    new GetObjectCommand({
      Bucket: s3Config.bucket,
      Key: key,
    })
  );
  const chunks = [];
  for await (const chunk of out.Body) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks);
}

module.exports = {
  getS3,
  uploadBuffer,
  getSignedGetUrl,
  getObjectBuffer,
};
