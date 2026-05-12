const db = require('../utils/database');
const { AppError } = require('../middleware/error.middleware');
const { parsePagination, buildMeta } = require('../utils/helpers');

class SchoolService {
  async create(data) {
    return db.prisma.school.create({ data });
  }

  async list(requester) {
    if (requester.role === 'admin') {
      return db.prisma.school.findMany({ where: { deletedAt: null } });
    }
    return db.prisma.school.findMany({
      where: { id: requester.schoolId, deletedAt: null },
    });
  }

  async getById(id) {
    const school = await db.prisma.school.findFirst({ where: { id, deletedAt: null } });
    if (!school) throw new AppError('School not found', 404);
    return school;
  }

  async update(id, data) {
    return db.prisma.school.update({
      where: { id },
      data,
    });
  }

  async users(schoolId, query) {
    const { page, limit, skip } = parsePagination(query);
    const where = { schoolId, deletedAt: null };
    const [total, rows] = await Promise.all([
      db.prisma.user.count({ where }),
      db.prisma.user.findMany({
        where,
        skip,
        take: limit,
        select: {
          id: true,
          email: true,
          firstName: true,
          lastName: true,
          role: true,
          isActive: true,
          createdAt: true,
        },
      }),
    ]);
    return { data: rows, meta: buildMeta(total, page, limit) };
  }

  async listSubjects(schoolId) {
    if (!schoolId) return [];
    return db.prisma.subject.findMany({
      where: { schoolId, deletedAt: null },
      orderBy: { name: 'asc' },
      select: { id: true, name: true, code: true },
    });
  }
}

module.exports = new SchoolService();
