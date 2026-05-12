const appConfig = require('./app.config');

module.exports = {
  region: appConfig.aws.region,
  bucket: appConfig.aws.s3Bucket,
  credentials:
    appConfig.aws.accessKeyId && appConfig.aws.secretAccessKey
      ? {
          accessKeyId: appConfig.aws.accessKeyId,
          secretAccessKey: appConfig.aws.secretAccessKey,
        }
      : undefined,
  endpoint: appConfig.aws.endpoint,
  forcePathStyle: appConfig.aws.forcePathStyle,
};
