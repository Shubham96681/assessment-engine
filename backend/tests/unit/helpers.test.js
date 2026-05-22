const { parsePagination, buildMeta } = require('../../src/utils/helpers');

describe('helpers', () => {
  it('parsePagination uses defaults', () => {
    expect(parsePagination({})).toEqual({ page: 1, limit: 20, skip: 0 });
  });

  it('buildMeta computes pages', () => {
    expect(buildMeta(45, 2, 20)).toEqual({ total: 45, page: 2, limit: 20, totalPages: 3 });
  });
});
