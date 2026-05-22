const { PrismaClient } = require('@prisma/client');
const bcrypt = require('bcryptjs');

const prisma = new PrismaClient();

async function main() {
  const school = await prisma.school.upsert({
    where: { code: 'TEST001' },
    update: {},
    create: {
      name: 'Demo School',
      code: 'TEST001',
      contactEmail: 'admin@demo-school.test',
    },
  });

  const passwordHash = await bcrypt.hash('Password123!', 12);

  await prisma.user.upsert({
    where: { email: 'admin@demo-school.test' },
    update: { passwordHash, schoolId: school.id },
    create: {
      email: 'admin@demo-school.test',
      passwordHash,
      firstName: 'School',
      lastName: 'Admin',
      role: 'school_admin',
      schoolId: school.id,
      emailVerified: true,
    },
  });

  await prisma.user.upsert({
    where: { email: 'teacher@demo-school.test' },
    update: { passwordHash, schoolId: school.id },
    create: {
      email: 'teacher@demo-school.test',
      passwordHash,
      firstName: 'Demo',
      lastName: 'Teacher',
      role: 'teacher',
      schoolId: school.id,
      emailVerified: true,
    },
  });

  await prisma.user.upsert({
    where: { email: 'student@demo-school.test' },
    update: { passwordHash, schoolId: school.id },
    create: {
      email: 'student@demo-school.test',
      passwordHash,
      firstName: 'Demo',
      lastName: 'Student',
      role: 'student',
      schoolId: school.id,
      emailVerified: true,
    },
  });

  const demoSubjects = [
    { name: 'Mathematics', code: 'MATH' },
    { name: 'Science', code: 'SCI' },
    { name: 'English', code: 'ENG' },
  ];
  for (const s of demoSubjects) {
    const existing = await prisma.subject.findFirst({
      where: { schoolId: school.id, name: s.name, deletedAt: null },
    });
    if (!existing) {
      await prisma.subject.create({
        data: { schoolId: school.id, name: s.name, code: s.code },
      });
    }
  }

  // eslint-disable-next-line no-console
  console.log('Seed complete. School TEST001, users: admin@ / teacher@ / student@ demo-school.test / Password123!');
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
