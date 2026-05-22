const path = require('path');
const swaggerJsdoc = require('swagger-jsdoc');
const swaggerUi = require('swagger-ui-express');

const options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'Assessment Engine API',
      version: '1.0.0',
      description: 'Assessment management system API',
    },
    servers: [
      {
        url: (process.env.API_URL || 'http://localhost:3000') + '/api/v1',
        description: 'API v1',
      },
    ],
    components: {
      securitySchemes: {
        bearerAuth: {
          type: 'http',
          scheme: 'bearer',
          bearerFormat: 'JWT',
        },
      },
    },
    security: [{ bearerAuth: [] }],
  },
  apis: [path.join(__dirname, '../routes/*.js')],
};

const specs = swaggerJsdoc(options);

module.exports = {
  serve: swaggerUi.serve,
  setup: swaggerUi.setup(specs, { explorer: true }),
  specs,
};
