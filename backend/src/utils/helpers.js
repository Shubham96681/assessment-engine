function parsePagination(query) {
  const page = Math.max(1, parseInt(query.page, 10) || 1);
  const limit = Math.min(500, Math.max(1, parseInt(query.limit, 10) || 20));
  return { page, limit, skip: (page - 1) * limit };
}

function buildMeta(total, page, limit) {
  return {
    total,
    page,
    limit,
    totalPages: Math.ceil(total / limit) || 1,
  };
}

function omit(obj, keys) {
  const out = { ...obj };
  keys.forEach((k) => delete out[k]);
  return out;
}

module.exports = {
  parsePagination,
  buildMeta,
  omit,
};
