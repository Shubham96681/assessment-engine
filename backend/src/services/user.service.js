const bcrypt = require('bcryptjs');
const { v4: uuidv4 } = require('uuid');
const db = require('../utils/database');
const { AppError } = require('../middleware/error.middleware');
const { parsePagination, buildMeta } = require('../utils/helpers');
const emailService = require('./email.service');

const SALT_ROUNDS = 12;

function sanitizeUser(user) {
  if (!user) return null;
  const { passwordHash, mfaSecret, ...rest } = user;
  return rest;
}

class UserService {
  async createProfile(userId, profileData) {
    const user = await db.prisma.user.update({
      where: { id: userId },
      data: {
        firstName: profileData.firstName,
        lastName: profileData.lastName,
        phone: profileData.phone,
        profilePictureUrl: profileData.profilePictureUrl,
        settings: profileData.settings,
      },
    });
    return sanitizeUser(user);
  }

  async getUsers(filters, requester) {
    const { page, limit, skip } = parsePagination(filters);
    const where = { deletedAt: null };
    if (filters.role) where.role = filters.role;
    if (filters.schoolId) {
      if (requester.role !== 'admin' && requester.schoolId !== filters.schoolId) {
        throw new AppError('Cannot list users for another school', 403);
      }
      where.schoolId = filters.schoolId;
    } else if (requester.role !== 'admin') {
      where.schoolId = requester.schoolId;
    }
    if (filters.search) {
      where.OR = [
        { email: { contains: filters.search, mode: 'insensitive' } },
        { firstName: { contains: filters.search, mode: 'insensitive' } },
        { lastName: { contains: filters.search, mode: 'insensitive' } },
      ];
    }

    const [total, rows] = await Promise.all([
      db.prisma.user.count({ where }),
      db.prisma.user.findMany({
        where,
        skip,
        take: limit,
        orderBy: { createdAt: 'desc' },
        select: {
          id: true,
          email: true,
          firstName: true,
          lastName: true,
          role: true,
          schoolId: true,
          isActive: true,
          emailVerified: true,
          profilePictureUrl: true,
          createdAt: true,
        },
      }),
    ]);

    return { data: rows, meta: buildMeta(total, page, limit) };
  }

  async updateUser(userId, updateData, requester) {
    if (requester.id !== userId && !['admin', 'school_admin'].includes(requester.role)) {
      throw new AppError('Forbidden', 403);
    }
    const user = await db.prisma.user.update({
      where: { id: userId },
      data: {
        firstName: updateData.firstName,
        lastName: updateData.lastName,
        phone: updateData.phone,
        isActive: updateData.isActive,
        settings: updateData.settings,
      },
    });
    return sanitizeUser(user);
  }

  async assignRole(userId, role, requester) {
    if (!['admin', 'school_admin'].includes(requester.role)) {
      throw new AppError('Forbidden', 403);
    }
    const user = await db.prisma.user.update({
      where: { id: userId },
      data: { role },
    });
    return sanitizeUser(user);
  }

  async bulkImportUsers(rows, schoolId, requester) {
    if (!['admin', 'school_admin'].includes(requester.role)) {
      throw new AppError('Forbidden', 403);
    }
    if (requester.role !== 'admin' && requester.schoolId !== schoolId) {
      throw new AppError('Forbidden', 403);
    }

    const report = { created: 0, errors: [] };

    for (let i = 0; i < rows.length; i += 1) {
      const row = rows[i];
      try {
        const password = row.password || `Temp${uuidv4().slice(0, 8)}!`;
        const passwordHash = await bcrypt.hash(password, SALT_ROUNDS);
        await db.prisma.user.create({
          data: {
            email: row.email.toLowerCase(),
            passwordHash,
            firstName: row.firstName,
            lastName: row.lastName,
            role: row.role,
            schoolId,
          },
        });
        report.created += 1;
        await emailService.sendWelcomeEmail(row.email, row.firstName).catch(() => {});
      } catch (e) {
        report.errors.push({ row: i + 1, message: e.message });
      }
    }

    return report;
  }
}

module.exports = new UserService();
