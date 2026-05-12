const db = require('../utils/database');
const { AppError } = require('../middleware/error.middleware');
const testService = require('./test.service');

const DIFF_ORDER = { easy: 1, medium: 2, hard: 3 };
const TYPE_ORDER = { mcq: 1, true_false: 2, fill_blank: 3, descriptive: 4 };

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function normUuid(v) {
  if (v == null || v === '') return null;
  const s = String(v).trim();
  return UUID_RE.test(s) ? s : null;
}

function normLibRelPath(p) {
  return String(p || '')
    .replace(/\\/g, '/')
    .replace(/\/+/g, '/')
    .replace(/^\/+|\/+$/g, '')
    .trim();
}

function normText(t) {
  return String(t || '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 160);
}

function sectionTitle(type) {
  const map = {
    mcq: 'Multiple choice',
    true_false: 'True / false',
    fill_blank: 'Fill in the blanks',
    descriptive: 'Descriptive',
  };
  return map[type] || type;
}

function allocateCounts(n, enabledTypes, mix) {
  const totalMix = enabledTypes.reduce((s, t) => s + (Number(mix[t]) || 0), 0) || 100;
  const raw = {};
  let sum = 0;
  for (const t of enabledTypes) {
    const c = Math.floor((n * (Number(mix[t]) || 0)) / totalMix);
    raw[t] = c;
    sum += c;
  }
  let rem = n - sum;
  const byPool = [...enabledTypes].sort((a, b) => (Number(mix[b]) || 0) - (Number(mix[a]) || 0));
  let i = 0;
  while (rem > 0 && enabledTypes.length) {
    const t = byPool[i % byPool.length];
    raw[t] = (raw[t] || 0) + 1;
    rem -= 1;
    i += 1;
  }
  return raw;
}

function pickWithDifficulty(pool, need, diffPct, usedIds, usedNorm) {
  if (need <= 0) return [];
  const easyT = Math.round((need * (Number(diffPct.easy) || 0)) / 100);
  const hardT = Math.round((need * (Number(diffPct.hard) || 0)) / 100);
  let mediumT = need - easyT - hardT;
  if (mediumT < 0) mediumT = 0;

  const want = [
    ...Array(easyT).fill('easy'),
    ...Array(mediumT).fill('medium'),
    ...Array(hardT).fill('hard'),
  ];
  while (want.length < need) want.push('medium');
  while (want.length > need) want.pop();

  const out = [];
  const buckets = { easy: [], medium: [], hard: [], any: [] };
  for (const q of pool) {
    if (usedIds.has(q.id)) continue;
    const d = q.difficulty && ['easy', 'medium', 'hard'].includes(q.difficulty) ? q.difficulty : 'medium';
    buckets[d].push(q);
    buckets.any.push(q);
  }
  for (const k of Object.keys(buckets)) {
    buckets[k] = shuffle(buckets[k]);
  }

  const takeFrom = (list, d) => {
    for (const q of list) {
      if (usedIds.has(q.id)) continue;
      const key = normText(q.questionText);
      if (usedNorm.has(key)) continue;
      usedIds.add(q.id);
      usedNorm.add(key);
      return { ...q, _pickedDifficulty: d };
    }
    return null;
  };

  for (const d of want) {
    let row = takeFrom(buckets[d], d);
    if (!row) row = takeFrom(buckets.any, d);
    if (row) out.push(row);
  }

  return out;
}

function validatePool(questions, params) {
  const issues = [];
  let valid = 0;
  const dupGroups = [];
  const byNorm = new Map();

  questions.forEach((q, idx) => {
    let ok = true;
    const localIssues = [];
    if (!q.questionText || String(q.questionText).trim().length < 4) {
      ok = false;
      localIssues.push('Question text too short');
    }
    if (q.questionType === 'mcq') {
      const correct = (q.options || []).filter((o) => o.isCorrect);
      if (correct.length !== 1) {
        ok = false;
        localIssues.push('MCQ must have exactly one correct option');
      }
      if ((q.options || []).length < 2) {
        ok = false;
        localIssues.push('MCQ needs at least two options');
      }
    }
    if (ok) valid += 1;
    else issues.push({ questionId: q.id, issues: localIssues });

    const nk = normText(q.questionText);
    if (!byNorm.has(nk)) byNorm.set(nk, []);
    byNorm.get(nk).push(idx);
  });

  for (const [, idxs] of byNorm) {
    if (idxs.length > 1) dupGroups.push(idxs);
  }

  const diffBal = { easy: 0, medium: 0, hard: 0 };
  questions.forEach((q) => {
    const d = q.difficulty && diffBal[q.difficulty] !== undefined ? q.difficulty : 'medium';
    diffBal[d] += 1;
  });

  const topicSet = new Set();
  questions.forEach((q) => {
    const topics = Array.isArray(q.topics) ? q.topics : [];
    topics.forEach((t) => topicSet.add(String(t)));
  });
  const requested = params.topics || [];
  const topicCoveragePct =
    requested.length === 0
      ? 100
      : Math.round((requested.filter((t) => topicSet.has(t)).length / requested.length) * 100);

  const qualityScore = Math.min(
    100,
    Math.round(
      (valid / Math.max(1, questions.length)) * 70 +
        (dupGroups.length === 0 ? 20 : 5) +
        Math.min(10, topicCoveragePct / 10)
    )
  );

  return {
    totalQuestions: questions.length,
    validQuestions: valid,
    invalidCount: questions.length - valid,
    issues,
    duplicateGroups: dupGroups,
    topicCoveragePct,
    difficultyBalance: diffBal,
    qualityScore,
    difficultyBalanceLabel:
      questions.length < (params.numberOfQuestions || 0) * 0.5 ? 'Low pool — widen filters' : 'Good',
  };
}

class AutomatedTestGenerationService {
  async findBookIdByLocalLibraryRel(schoolId, libRelRaw) {
    const want = normLibRelPath(libRelRaw);
    if (!want) return null;
    const books = await db.prisma.book.findMany({
      where: { schoolId, deletedAt: null },
      select: { id: true, metadata: true },
    });
    for (const b of books) {
      const m = b.metadata && typeof b.metadata === 'object' ? b.metadata : {};
      if (typeof m.localLibraryRel === 'string' && normLibRelPath(m.localLibraryRel) === want) {
        return b.id;
      }
    }
    return null;
  }

  async fetchQuestionPool(schoolId, params) {
    const libRel = params.localLibraryRel && String(params.localLibraryRel).trim();

    let rows;
    if (libRel) {
      const bookId = await this.findBookIdByLocalLibraryRel(schoolId, libRel);
      if (!bookId) {
        return [];
      }
      rows = await db.prisma.question.findMany({
        where: {
          deletedAt: null,
          schoolId,
          sourceResourceId: bookId,
        },
        include: { options: true, subject: true },
        take: 5000,
        orderBy: { updatedAt: 'desc' },
      });
    } else {
      const where = { deletedAt: null, schoolId };
      if (params.subjectId && normUuid(params.subjectId)) {
        where.subjectId = normUuid(params.subjectId);
      }
      if (params.chapterLabel && String(params.chapterLabel).trim()) {
        where.chapter = { contains: String(params.chapterLabel).trim() };
      }

      rows = await db.prisma.question.findMany({
        where,
        include: { options: true, subject: true },
        take: 1500,
        orderBy: { updatedAt: 'desc' },
      });
    }

    let filtered = rows;

    const topics = params.topics || [];
    if (topics.length) {
      const tLower = topics.map((t) => String(t).toLowerCase());
      filtered = filtered.filter((q) => {
        const qt = Array.isArray(q.topics) ? q.topics : [];
        return tLower.some(
          (t) =>
            qt.includes(t) ||
            qt.some((x) => String(x).toLowerCase().includes(t)) ||
            String(q.questionText || '')
              .toLowerCase()
              .includes(t)
        );
      });
    }

    if (params.board && String(params.board).trim()) {
      const b = String(params.board).toLowerCase();
      const boardFiltered = filtered.filter((q) => {
        const tags = Array.isArray(q.tags) ? q.tags : [];
        return tags.some((tag) => String(tag).toLowerCase().includes(b));
      });
      if (boardFiltered.length) filtered = boardFiltered;
    }

    const exclude = params.excludeTags || [];
    if (exclude.length) {
      filtered = filtered.filter((q) => {
        const tags = Array.isArray(q.tags) ? q.tags.map(String) : [];
        return !exclude.some((ex) => tags.includes(ex));
      });
    }

    if (params.includeHeritage) {
      filtered = shuffle(filtered).sort((a, b) => {
        const ha = (Array.isArray(a.tags) ? a.tags : []).includes('heritage');
        const hb = (Array.isArray(b.tags) ? b.tags : []).includes('heritage');
        return (hb ? 1 : 0) - (ha ? 1 : 0);
      });
    } else if (params.resourcePriority?.preferExtracted !== false) {
      filtered = shuffle(filtered).sort((a, b) => {
        const ea = (Array.isArray(a.tags) ? a.tags : []).includes('extracted');
        const eb = (Array.isArray(b.tags) ? b.tags : []).includes('extracted');
        return (eb ? 1 : 0) - (ea ? 1 : 0);
      });
    } else {
      filtered = shuffle(filtered);
    }

    const hadLibraryRelFilter = Boolean(libRel);
    if (!filtered.length && (topics.length || params.chapterLabel) && !hadLibraryRelFilter) {
      return shuffle(rows);
    }
    return filtered;
  }

  selectQuestions(pool, params) {
    const n = Math.min(100, Math.max(1, Number(params.numberOfQuestions) || 20));
    const types = params.questionTypes || {};
    const enabledTypes = ['mcq', 'true_false', 'fill_blank', 'descriptive'].filter((t) => types[t] !== false);
    if (!enabledTypes.length) throw new AppError('Select at least one question type', 400);

    const mix = params.questionTypeMix || {};
    const diffPct = params.difficultyDistribution || { easy: 30, medium: 50, hard: 20 };
    const marksByType = params.marksByType || {};

    const byType = {};
    for (const t of enabledTypes) {
      byType[t] = pool.filter((q) => q.questionType === t);
    }

    const alloc = allocateCounts(n, enabledTypes, mix);
    const usedIds = new Set();
    const usedNorm = new Set();
    const picked = [];

    for (const t of enabledTypes) {
      const need = Math.min(alloc[t] || 0, byType[t].length);
      const slice = pickWithDifficulty(byType[t], need, diffPct, usedIds, usedNorm);
      for (const q of slice) {
        picked.push({
          ...q,
          suggestedMarks: Number(marksByType[t] ?? q.marks ?? 1),
        });
      }
    }

    let deficit = n - picked.length;
    if (deficit > 0) {
      const rest = shuffle(pool.filter((q) => !usedIds.has(q.id)));
      for (const q of rest) {
        if (deficit <= 0) break;
        const key = normText(q.questionText);
        if (usedNorm.has(key)) continue;
        usedIds.add(q.id);
        usedNorm.add(key);
        const t = q.questionType;
        const sm = Number(marksByType[t] ?? q.marks ?? 1);
        picked.push({ ...q, suggestedMarks: sm });
        deficit -= 1;
      }
    }

    return picked.slice(0, n);
  }

  sortForAssembly(questions) {
    return [...questions].sort((a, b) => {
      const da = DIFF_ORDER[a.difficulty] || 2;
      const db = DIFF_ORDER[b.difficulty] || 2;
      if (da !== db) return da - db;
      return (TYPE_ORDER[a.questionType] || 9) - (TYPE_ORDER[b.questionType] || 9);
    });
  }

  assignSections(sortedQuestions) {
    return sortedQuestions.map((q) => ({
      ...q,
      sectionName: sectionTitle(q.questionType),
    }))
  }

  serializeForReview(q) {
    return {
      id: q.id,
      questionType: q.questionType,
      questionText: q.questionText,
      difficulty: q.difficulty,
      marks: q.suggestedMarks != null ? q.suggestedMarks : Number(q.marks),
      suggestedMarks: q.suggestedMarks != null ? q.suggestedMarks : Number(q.marks),
      topics: Array.isArray(q.topics) ? q.topics : [],
      chapter: q.chapter,
      subject: q.subject ? { id: q.subject.id, name: q.subject.name } : null,
      options: (q.options || []).map((o) => ({
        id: o.id,
        optionText: o.optionText,
        isCorrect: o.isCorrect,
      })),
      sourceType: q.sourceType,
      sourceResourceId: q.sourceResourceId,
      tags: Array.isArray(q.tags) ? q.tags : [],
    };
  }

  async generatePreview(params, userId) {
    const user = await db.prisma.user.findUnique({ where: { id: userId } });
    if (!user?.schoolId) throw new AppError('User must belong to a school', 400);

    const libRelRaw = params.localLibraryRel && String(params.localLibraryRel).trim();
    let pool = await this.fetchQuestionPool(user.schoolId, params);
    const previewScopeNotes = [];

    if (!pool.length && libRelRaw) {
      const bookId = await this.findBookIdByLocalLibraryRel(user.schoolId, libRelRaw);
      if (bookId) {
        const rawCount = await db.prisma.question.count({
          where: { schoolId: user.schoolId, deletedAt: null, sourceResourceId: bookId },
        });
        if (rawCount === 0) {
          const relaxed = { ...params };
          delete relaxed.localLibraryRel;
          const fallbackPool = await this.fetchQuestionPool(user.schoolId, relaxed);
          if (fallbackPool.length) {
            pool = fallbackPool;
            previewScopeNotes.push(
              'This PDF is in your library but has no extracted questions yet. This preview uses your full question bank. In Resources → My books, click Extract on this book (try "Chapter patterns only" for textbooks), then generate again to limit the pool to this file.'
            );
          }
        }
      }
    }

    if (!pool.length) {
      const baseWarnings = ['Add or extract questions for this subject, or relax topic/board filters.'];
      if (libRelRaw) {
        const bookId = await this.findBookIdByLocalLibraryRel(user.schoolId, libRelRaw);
        if (!bookId) {
          baseWarnings.push(
            'No book in your library matches this PDF path. Re-import the CBSE folder (Resources → Add curriculum) so paths line up, or clear the chapter pick.'
          );
        } else {
          const rawCount = await db.prisma.question.count({
            where: { schoolId: user.schoolId, deletedAt: null, sourceResourceId: bookId },
          });
          if (rawCount > 0) {
            baseWarnings.push(
              `This book has ${rawCount} question(s), but none matched your topic, tag/board, or type filters. Clear topic picks, set tag/board to "Any", or enable more question types.`
            );
          } else {
            baseWarnings.push(
              'This PDF is registered as a book, but there are no questions linked to it yet. Open the book in Resources and run Extract, or clear the chapter pick.'
            );
          }
        }
      }
      return {
        questions: [],
        summary: {
          totalQuestions: 0,
          validQuestions: 0,
          invalidCount: 0,
          issues: [],
          duplicateGroups: [],
          topicCoveragePct: 0,
          difficultyBalance: {},
          qualityScore: 0,
          difficultyBalanceLabel: 'No questions in bank for these filters',
          warnings: baseWarnings,
        },
        generationParameters: params,
      };
    }

    const picked = this.selectQuestions(pool, params);
    const sorted = this.assignSections(this.sortForAssembly(picked));
    const summary = validatePool(sorted, params);
    const warnings = [...previewScopeNotes];
    if (picked.length < (params.numberOfQuestions || 20)) {
      warnings.push(
        `Only ${picked.length} question(s) matched. Add more items to the question bank or relax filters.`
      );
    }

    const genParams =
      previewScopeNotes.length > 0
        ? { ...params, _previewFullBankFallback: true, _requestedLocalLibraryRel: libRelRaw || null }
        : params;

    return {
      questions: sorted.map((q) => this.serializeForReview(q)),
      summary: { ...summary, warnings },
      generationParameters: genParams,
    };
  }

  async createTestFromApproved(body, userId) {
    const user = await db.prisma.user.findUnique({ where: { id: userId } });
    if (!user?.schoolId) throw new AppError('User must belong to a school', 400);

    const { test: testInput, approvedQuestions } = body;
    if (!approvedQuestions?.length) throw new AppError('approvedQuestions is required', 400);

    const ids = approvedQuestions.map((q) => q.questionId);
    const rows = await db.prisma.question.findMany({
      where: { id: { in: ids }, schoolId: user.schoolId, deletedAt: null },
      include: { options: true },
    });
    if (rows.length !== ids.length) throw new AppError('One or more questions are invalid for your school', 400);

    const marksByQ = new Map();
    const sectionOverride = new Map();
    for (const aq of approvedQuestions) {
      marksByQ.set(aq.questionId, Number(aq.marks));
      if (aq.sectionName) sectionOverride.set(aq.questionId, aq.sectionName);
    }

    let enriched = rows.map((q) => ({ ...q }));
    enriched = this.assignSections(this.sortForAssembly(enriched));

    const totalMarks = enriched.reduce((s, q) => s + Number(marksByQ.get(q.id)), 0);
    const questionIds = enriched.map((q, idx) => ({
      questionId: q.id,
      marks: Number(marksByQ.get(q.id)),
      questionOrder: idx,
      sectionName: sectionOverride.get(q.id) || q.sectionName || sectionTitle(q.questionType),
      isMandatory: true,
    }));

    const testPayload = {
      ...testInput,
      subjectId: normUuid(testInput.subjectId),
      classIds: (testInput.classIds || []).map(normUuid).filter(Boolean),
      totalMarks,
      questionIds,
      questionSelectionMode: testInput.questionSelectionMode || 'mixed',
      settings: {
        ...(testInput.settings || {}),
        autoGenerated: true,
        generationParameters: body.generationParameters || null,
      },
    };

    return testService.createTest(testPayload, userId);
  }
}

module.exports = new AutomatedTestGenerationService();
