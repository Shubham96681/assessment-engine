/** Normalize Prisma Json columns that store string arrays (SQLite). */
function asStringArray(value) {
  if (Array.isArray(value)) return value.filter((x) => typeof x === 'string');
  return [];
}

module.exports = { asStringArray };
