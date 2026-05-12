require('./models/associations');
/* eslint-disable no-extend-native */
BigInt.prototype.toJSON = function bigintToJson() {
  return this.toString();
};

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const config = require('./config/app.config');
const { errorHandler, notFound } = require('./middleware/error.middleware');
const { generalLimiter } = require('./middleware/rate-limit.middleware');
const healthRoutes = require('./routes/health.routes');
const authRoutes = require('./routes/auth.routes');
const userRoutes = require('./routes/user.routes');
const schoolRoutes = require('./routes/school.routes');
const testRoutes = require('./routes/test.routes');
const questionRoutes = require('./routes/question.routes');
const resourceRoutes = require('./routes/resource.routes');
const analyticsRoutes = require('./routes/analytics.routes');
const notificationRoutes = require('./routes/notification.routes');
const gradingRoutes = require('./routes/grading.routes');
const subjectRoutes = require('./routes/subject.routes');
const swagger = require('./docs/swagger');

const app = express();

app.use(helmet());
app.use(cors({ origin: true, credentials: true }));
app.use(compression());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));
app.use(generalLimiter);

app.use('/health', healthRoutes);

const api = express.Router();
api.use('/auth', authRoutes);
api.use('/users', userRoutes);
api.use('/schools', schoolRoutes);
api.use('/tests', testRoutes);
api.use('/questions', questionRoutes);
api.use('/resources', resourceRoutes);
api.use('/analytics', analyticsRoutes);
api.use('/notifications', notificationRoutes);
api.use('/grading', gradingRoutes);
api.use('/subjects', subjectRoutes);

app.use('/api/v1', api);

app.use('/api/docs', swagger.serve, swagger.setup);

app.use(notFound);
app.use(errorHandler);

module.exports = app;
