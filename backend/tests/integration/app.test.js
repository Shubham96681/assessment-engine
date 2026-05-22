const request = require('supertest');
const database = require('../../src/utils/database');
const redis = require('../../src/utils/redis');

jest.spyOn(database, 'healthCheck').mockResolvedValue({
  status: 'healthy',
  timestamp: new Date().toISOString(),
});
jest.spyOn(redis, 'healthCheck').mockResolvedValue({
  status: 'healthy',
  timestamp: new Date().toISOString(),
});

const app = require('../../src/app');

describe('Health', () => {
  it('GET /health returns 200 when dependencies are healthy', async () => {
    const res = await request(app).get('/health').expect(200);
    expect(res.body.status).toBe('ok');
    expect(res.body.services.database.status).toBe('healthy');
  });
});

describe('404', () => {
  it('returns JSON 404 for unknown routes', async () => {
    const res = await request(app).get('/api/v1/unknown-route-xyz').expect(404);
    expect(res.body.status).toBe('fail');
  });
});
