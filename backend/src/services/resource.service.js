const fs = require('fs').promises;
const fsSync = require('fs');
const path = require('path');

const db = require('../utils/database');
const appConfig = require('../config/app.config');
const { uploadBuffer, getObjectBuffer, getS3 } = require('../utils/s3');
const { AppError } = require('../middleware/error.middleware');
const { parsePagination, buildMeta } = require('../utils/helpers');
const questionService = require('./question.service');
const docExtraction = require('./resource-document-extraction.service');
const nonAiGeneration = require('./non-ai-question-generation.service');

function normQuestionStemForDedupe(s) {
  return String(s || '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 140);
}

function resolveSafeUnderRoot(rootEnv, relPath) {
  const root = path.resolve(rootEnv);
  const segments = String(relPath)
    .replace(/\\/g, '/')
    .split('/')
    .filter((s) => s && s !== '.');
  if (segments.some((s) => s === '..')) {
    throw new AppError('Invalid library path', 400);
  }
  const resolved = path.resolve(root, ...segments);
  const relToRoot = path.relative(root, resolved);
  if (relToRoot.startsWith('..') || path.isAbsolute(relToRoot)) {
    throw new AppError('Invalid library path', 400);
  }
  return resolved;
}

function humanizePdfBasename(basename) {
  const base = basename.replace(/\.pdf$/i, '');
  const spaced = base.replace(/_/g, ' ').replace(/\s+/g, ' ').trim();
  return spaced || 'Untitled chapter';
}

function tagsFromRelativePath(relPosix) {
  const parts = relPosix.split('/').filter(Boolean);
  const tags = ['cbse', 'local-library'];
  if (parts[0]) tags.push(parts[0]);
  if (parts[1]) tags.push(parts[1]);
  // class / subject / book-folder / … / file.pdf — include book path for finer filters
  if (parts.length >= 4) {
    for (let i = 2; i < parts.length - 1; i += 1) {
      if (parts[i]) tags.push(parts[i]);
    }
  }
  return tags;
}

const CBSE_SUBJECT_ROOT_BOOK = '__subject_root__';

function addPdfToCbseTree(rootMap, relPosix, bookId) {
  const parts = relPosix.split('/').filter(Boolean);
  if (parts.length < 2) return;
  const file = parts[parts.length - 1];
  if (!/\.pdf$/i.test(file)) return;
  const dirParts = parts.slice(0, -1);
  const [classLabel, subjectLabel, ...restDirs] = dirParts;
  if (!classLabel || !subjectLabel) return;
  const bookKey = restDirs.length ? restDirs.join('/') : CBSE_SUBJECT_ROOT_BOOK;
  const chapterTitle = humanizePdfBasename(file);

  if (!rootMap.has(classLabel)) rootMap.set(classLabel, new Map());
  const cls = rootMap.get(classLabel);
  if (!cls.has(subjectLabel)) cls.set(subjectLabel, new Map());
  const sub = cls.get(subjectLabel);
  if (!sub.has(bookKey)) sub.set(bookKey, new Map());
  const book = sub.get(bookKey);
  const prev = book.get(relPosix);
  if (prev) {
    if (!prev.bookId && bookId) book.set(relPosix, { ...prev, bookId });
  } else {
    book.set(relPosix, { title: chapterTitle, rel: relPosix, bookId: bookId || null });
  }
}

function serializeCbseTree(rootMap) {
  const bookLabel = (key) => (key === CBSE_SUBJECT_ROOT_BOOK ? '— PDFs directly under subject' : key.replace(/_/g, ' '));
  return [...rootMap.entries()]
    .sort(([a], [b]) => a.localeCompare(b, undefined, { numeric: true }))
    .map(([classLabel, subMap]) => ({
      label: classLabel,
      subjects: [...subMap.entries()]
        .sort(([a], [b]) => a.localeCompare(b, undefined, { numeric: true }))
        .map(([subjectLabel, bookMap]) => ({
          label: subjectLabel,
          books: [...bookMap.entries()]
            .sort(([a], [b]) => a.localeCompare(b, undefined, { numeric: true }))
            .map(([rawBookKey, chMap]) => ({
              label: bookLabel(rawBookKey),
              bookKey: rawBookKey,
              chapters: [...chMap.values()].sort((x, y) => x.title.localeCompare(y.title, undefined, { numeric: true })),
            })),
        })),
    }));
}

async function walkPdfFiles(dir, acc = []) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const e of entries) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) {
      await walkPdfFiles(p, acc);
    } else if (e.isFile() && e.name.toLowerCase().endsWith('.pdf')) {
      acc.push(p);
    }
  }
  return acc;
}

async function loadResourceRecord(resourceId, resourceType) {
  if (resourceType === 'book') {
    const b = await db.prisma.book.findFirst({ where: { id: resourceId, deletedAt: null } });
    if (!b) throw new AppError('Resource not found', 404);
    return { record: b, type: 'book' };
  }
  if (resourceType === 'question_paper') {
    const p = await db.prisma.questionPaper.findFirst({ where: { id: resourceId, deletedAt: null } });
    if (!p) throw new AppError('Resource not found', 404);
    return { record: p, type: 'question_paper' };
  }
  throw new AppError('resourceType must be book or question_paper', 400);
}

async function loadFileBuffer(record) {
  const meta = (record.metadata && typeof record.metadata === 'object' ? record.metadata : {}) || {};
  const key = meta.storageKey;

  if (key && getS3()) {
    return getObjectBuffer(key);
  }

  if (record.fileUrl && /^https?:\/\//i.test(record.fileUrl)) {
    const res = await fetch(record.fileUrl);
    if (!res.ok) {
      throw new AppError(`Could not download file (HTTP ${res.status})`, 502);
    }
    return Buffer.from(await res.arrayBuffer());
  }

  if (record.fileUrl && String(record.fileUrl).startsWith('local://')) {
    const parsedKey = String(record.fileUrl).replace(/^local:\/\//, '');
    if (getS3() && parsedKey) {
      return getObjectBuffer(parsedKey);
    }
  }

  const root = appConfig.localCbseLibraryRoot;
  if (root && meta.localLibraryRel) {
    const fullPath = resolveSafeUnderRoot(root, meta.localLibraryRel);
    if (!fsSync.existsSync(fullPath)) {
      throw new AppError('Local library file is missing on disk', 404);
    }
    return fs.readFile(fullPath);
  }

  throw new AppError(
    'This file cannot be read for extraction. Configure S3/MinIO (recommended) so the object key is stored, or use a public http(s) file URL.',
    400
  );
}

class ResourceService {
  async uploadResource({ buffer, originalname, mimetype, resourceType }, metadata, uploadedBy) {
    const user = await db.prisma.user.findUnique({ where: { id: uploadedBy } });
    if (!user?.schoolId) throw new AppError('User must belong to a school', 400);

    const key = `schools/${user.schoolId}/${resourceType}/${Date.now()}-${originalname}`;
    const { url, key: objectKey } = await uploadBuffer({
      key,
      body: buffer,
      contentType: mimetype,
    });

    const fileUrl = url || `local://${objectKey}`;
    const storageMeta = { storageKey: objectKey || null, uploadSkipped: !url };

    if (resourceType === 'book') {
      return db.prisma.book.create({
        data: {
          schoolId: user.schoolId,
          uploadedBy,
          title: metadata.title,
          author: metadata.author,
          classId: metadata.classId,
          subjectId: metadata.subjectId,
          fileUrl,
          fileName: originalname,
          fileType: mimetype,
          fileSize: BigInt(buffer.length),
          tags: metadata.tags || [],
          processingStatus: 'completed',
          processingProgress: 100,
          questionsExtracted: 0,
          metadata: storageMeta,
        },
      });
    }

    return db.prisma.questionPaper.create({
      data: {
        schoolId: user.schoolId,
        uploadedBy,
        title: metadata.title,
        examName: metadata.examName,
        year: metadata.year,
        classId: metadata.classId,
        subjectId: metadata.subjectId,
        fileUrl,
        fileName: originalname,
        fileType: mimetype,
        fileSize: BigInt(buffer.length),
        tags: metadata.tags || [],
        processingStatus: 'completed',
        processingProgress: 100,
        questionsExtracted: 0,
        metadata: storageMeta,
      },
    });
  }

  /**
   * Non-AI extraction: PDF/text via pdf-parse, then (1) numbered-block heuristics and/or
   * (2) pattern-based generation per NON_AI_QUESTION_GENERATION.md (definitions, fill-in-blank, true/false).
   *
   * @param {{ strategy?: 'numbered_first'|'non_ai_only'|'combined', maxMcq?: number, maxFillBlank?: number, maxTrueFalse?: number }} extractOptions
   */
  async extractQuestionsFromDocument(resourceId, resourceType, createdBy, extractOptions = {}) {
    const user = await db.prisma.user.findUnique({ where: { id: createdBy } });
    if (!user?.schoolId) throw new AppError('User must belong to a school', 400);

    const { record } = await loadResourceRecord(resourceId, resourceType);
    if (record.schoolId !== user.schoolId && user.role !== 'admin') {
      throw new AppError('Forbidden', 403);
    }

    const strategy =
      extractOptions.strategy === 'non_ai_only' || extractOptions.strategy === 'combined'
        ? extractOptions.strategy
        : 'numbered_first';

    const buffer = await loadFileBuffer(record);
    const mime = (record.fileType || '').toLowerCase();
    const name = (record.fileName || '').toLowerCase();

    let text = '';
    if (mime.includes('pdf') || name.endsWith('.pdf')) {
      text = await docExtraction.extractTextFromPdfBuffer(buffer);
    } else if (mime.includes('text/plain') || name.endsWith('.txt')) {
      text = buffer.toString('utf8');
    } else {
      throw new AppError(
        'Unsupported file type for automatic extraction. Use PDF or plain text, or POST import-questions with structured JSON.',
        400
      );
    }

    const inheritedTags =
      resourceType === 'book' && Array.isArray(record.tags)
        ? record.tags.map((t) => String(t)).filter(Boolean)
        : [];
    const tags = [...new Set(['extracted', ...inheritedTags])];

    const blocks = docExtraction.splitNumberedQuestionBlocks(text);
    const useNumbered = strategy !== 'non_ai_only' && blocks.length > 0;

    const created = [];

    if (useNumbered) {
      for (const block of blocks) {
        const inferred = docExtraction.inferOptionsFromBlock(block);
        const options =
          inferred.options.length >= 2
            ? inferred.options.map((o, i) => ({
                optionText: o.optionText,
                isCorrect: false,
                optionOrder: i,
              }))
            : [];

        const q = await questionService.createQuestion(
          {
            questionType: options.length >= 2 ? 'mcq' : 'descriptive',
            questionText: inferred.questionText,
            questionData: { extractedBy: 'heuristic_numbering' },
            difficulty: 'medium',
            marks: 1,
            topics: [],
            tags,
            options,
            sourceType: resourceType === 'book' ? 'book' : 'question_paper',
            sourceResourceId: resourceId,
            sourceResourceType: resourceType,
            extractionConfidence: null,
          },
          createdBy
        );

        await db.prisma.extractedQuestion.create({
          data: {
            resourceType,
            resourceId,
            questionId: q.id,
            extractionMethod: 'heuristic_numbering',
            isVerified: false,
          },
        });
        created.push(q);
      }
    }

    const afterNumberedCount = created.length;

    let nonAiDrafts = [];
    if (strategy === 'non_ai_only') {
      nonAiDrafts = nonAiGeneration.generateFromChapterText(text, {
        maxMcq: extractOptions.maxMcq,
        maxFillBlank: extractOptions.maxFillBlank,
        maxTrueFalse: extractOptions.maxTrueFalse,
      });
    } else if (strategy === 'combined' || !created.length) {
      nonAiDrafts = nonAiGeneration.generateFromChapterText(text, {
        maxMcq: extractOptions.maxMcq,
        maxFillBlank: extractOptions.maxFillBlank,
        maxTrueFalse: extractOptions.maxTrueFalse,
      });
    }

    if (strategy === 'combined' && created.length) {
      const seen = new Set(created.map((q) => normQuestionStemForDedupe(q.questionText)));
      nonAiDrafts = nonAiDrafts.filter((d) => !seen.has(normQuestionStemForDedupe(d.questionText)));
    }

    for (const draft of nonAiDrafts) {
      if (!nonAiGeneration.validateDraft(draft)) continue;
      const q = await questionService.createQuestion(
        {
          questionType: draft.questionType,
          questionText: draft.questionText,
          questionData: draft.questionData || {},
          difficulty: 'medium',
          marks: 1,
          topics: [],
          tags,
          options: draft.options || [],
          sourceType: resourceType === 'book' ? 'book' : 'question_paper',
          sourceResourceId: resourceId,
          sourceResourceType: resourceType,
          extractionConfidence: null,
        },
        createdBy
      );

      await db.prisma.extractedQuestion.create({
        data: {
          resourceType,
          resourceId,
          questionId: q.id,
          extractionMethod: 'non_ai_patterns',
          isVerified: false,
        },
      });
      created.push(q);
    }

    if (!created.length) {
      throw new AppError(
        'No questions could be extracted or generated. For exam-style PDFs use lines like "1." for items; for textbook chapters POST strategy "non_ai_only" or wait for richer text from the PDF. You can also use import-questions.',
        422
      );
    }

    const count = created.length;
    if (resourceType === 'book') {
      await db.prisma.book.update({
        where: { id: resourceId },
        data: {
          questionsExtracted: { increment: count },
          processingStatus: 'completed',
          processingProgress: 100,
        },
      });
    } else {
      await db.prisma.questionPaper.update({
        where: { id: resourceId },
        data: {
          questionsExtracted: { increment: count },
          processingStatus: 'completed',
          processingProgress: 100,
        },
      });
    }

    const questionsFromNonAi = count - afterNumberedCount;
    let method = 'non_ai_patterns';
    if (afterNumberedCount > 0 && questionsFromNonAi > 0) method = 'combined_numbered_and_non_ai';
    else if (afterNumberedCount > 0) method = 'heuristic_numbering';

    return {
      method,
      strategy,
      numberedBlockCount: blocks.length,
      questionsFromNumbering: afterNumberedCount,
      questionsFromNonAi,
      questionsCreated: count,
      questions: created,
      hint:
        method === 'heuristic_numbering'
          ? 'Review and correct MCQ answer keys; heuristics cannot know the correct option.'
          : 'Review non-AI items: MCQ distractors may be weak; true/false uses simple negation rules; fill-blank expects exact spelling.',
    };
  }

  /**
   * Register a book that is hosted at a public https URL (no file upload).
   * Extraction uses fetch(fileUrl); Google Drive folder links will not work — use a per-file direct link or upload instead.
   */
  async registerBookFromPublicUrl(payload, uploadedBy) {
    const user = await db.prisma.user.findUnique({ where: { id: uploadedBy } });
    if (!user?.schoolId) throw new AppError('User must belong to a school', 400);

    const fileUrl = String(payload.fileUrl).trim();
    if (!/^https:\/\//i.test(fileUrl)) {
      throw new AppError('fileUrl must be an https URL', 400);
    }

    let host;
    try {
      host = new URL(fileUrl).hostname.toLowerCase();
    } catch {
      throw new AppError('Invalid fileUrl', 400);
    }
    const blockedHosts = new Set(['localhost', '127.0.0.1', '0.0.0.0', '::1', '169.254.169.254']);
    if (blockedHosts.has(host)) {
      throw new AppError('This file URL host is not allowed', 400);
    }
    if (/^10\./.test(host) || /^192\.168\./.test(host) || /^172\.(1[6-9]|2\d|3[0-1])\./.test(host)) {
      throw new AppError('This file URL host is not allowed', 400);
    }

    let fileName = payload.fileName ? String(payload.fileName).trim() : '';
    if (!fileName) {
      try {
        const last = new URL(fileUrl).pathname.split('/').filter(Boolean).pop();
        if (last && /\.[a-z0-9]+$/i.test(last)) {
          fileName = decodeURIComponent(last);
        }
      } catch {
        /* ignore */
      }
    }
    if (!fileName) fileName = 'remote-book.pdf';

    const lower = fileName.toLowerCase();
    const fileType =
      (payload.fileType && String(payload.fileType).trim()) ||
      (lower.endsWith('.txt') ? 'text/plain' : 'application/pdf');

    return db.prisma.book.create({
      data: {
        schoolId: user.schoolId,
        uploadedBy,
        title: String(payload.title).trim(),
        author: payload.author ? String(payload.author).trim() : null,
        fileUrl,
        fileName,
        fileType,
        fileSize: null,
        tags: ['external-url'],
        processingStatus: 'completed',
        processingProgress: 100,
        questionsExtracted: 0,
        metadata: { storageKey: null, uploadSkipped: true, externalSource: true },
      },
    });
  }

  /**
   * Scan LOCAL_CBSE_LIBRARY_ROOT for PDFs (class/subject/chapter tree) and register Book rows that read from disk on extract.
   */
  async importCbseLibraryFromDisk(uploadedBy, { dryRun = false, limit = null } = {}) {
    const user = await db.prisma.user.findUnique({ where: { id: uploadedBy } });
    if (!user?.schoolId) throw new AppError('User must belong to a school', 400);

    const root = appConfig.localCbseLibraryRoot;
    if (!root) {
      throw new AppError(
        'LOCAL_CBSE_LIBRARY_ROOT is not set. Add it to backend/.env pointing at your CBSE folder (absolute path).',
        400
      );
    }

    const rootResolved = path.resolve(root);
    if (!fsSync.existsSync(rootResolved)) {
      throw new AppError('LOCAL_CBSE_LIBRARY_ROOT path does not exist on the server', 400);
    }

    const pdfs = await walkPdfFiles(rootResolved);
    let remaining = limit != null ? Number(limit) : Infinity;
    if (Number.isNaN(remaining) || remaining < 0) remaining = Infinity;

    const result = {
      scanned: pdfs.length,
      created: 0,
      skipped: 0,
      dryRun: !!dryRun,
      books: [],
    };

    const maxSamples = 80;

    // SQLite: JSON path filters on metadata are brittle; preload imported paths once.
    const booksMetaRows = await db.prisma.book.findMany({
      where: { schoolId: user.schoolId, deletedAt: null },
      select: { metadata: true },
    });
    const importedRelSet = new Set();
    for (const row of booksMetaRows) {
      const meta = row.metadata && typeof row.metadata === 'object' ? row.metadata : {};
      const lr = meta.localLibraryRel;
      if (typeof lr === 'string' && lr) importedRelSet.add(lr);
    }

    for (const full of pdfs) {
      const rel = path.relative(rootResolved, full).replace(/\\/g, '/');

      if (importedRelSet.has(rel)) {
        result.skipped += 1;
        continue;
      }

      const base = path.basename(full);
      const title = humanizePdfBasename(base);
      const tags = tagsFromRelativePath(rel);

      if (dryRun) {
        const previewCap = remaining === Infinity ? maxSamples : Math.min(remaining, maxSamples);
        if (result.books.length < previewCap) {
          result.books.push({ title, localLibraryRel: rel, tags });
        }
        if (remaining !== Infinity && result.books.length >= remaining) break;
        continue;
      }

      if (remaining !== Infinity && result.created >= remaining) break;

      const stat = await fs.stat(full);
      const book = await db.prisma.book.create({
        data: {
          schoolId: user.schoolId,
          uploadedBy,
          title,
          author: 'NCERT / CBSE',
          fileUrl: `local-library://cbse/${rel}`,
          fileName: base,
          fileType: 'application/pdf',
          fileSize: BigInt(stat.size),
          tags,
          processingStatus: 'completed',
          processingProgress: 100,
          questionsExtracted: 0,
          metadata: {
            storageKey: null,
            localLibrary: true,
            localLibraryRel: rel,
            libraryKind: 'cbse',
          },
        },
      });
      result.created += 1;
      importedRelSet.add(rel);
      if (result.books.length < maxSamples) {
        result.books.push({ id: book.id, title, localLibraryRel: rel });
      }
    }

    return result;
  }

  /**
   * Non-AI "generation": attach ready-made questions from JSON to this resource (manual / external tooling).
   */
  async importQuestionsForResource(resourceId, resourceType, questions, createdBy) {
    const user = await db.prisma.user.findUnique({ where: { id: createdBy } });
    if (!user?.schoolId) throw new AppError('User must belong to a school', 400);

    const { record } = await loadResourceRecord(resourceId, resourceType);
    if (record.schoolId !== user.schoolId && user.role !== 'admin') {
      throw new AppError('Forbidden', 403);
    }

    const created = [];
    for (const item of questions) {
      const { isVerified, ...rest } = item;
      const q = await questionService.createQuestion(
        {
          ...rest,
          sourceType: resourceType === 'book' ? 'book' : 'question_paper',
          sourceResourceId: resourceId,
          sourceResourceType: resourceType,
        },
        createdBy
      );
      await db.prisma.extractedQuestion.create({
        data: {
          resourceType,
          resourceId,
          questionId: q.id,
          extractionMethod: 'import_json',
          isVerified: isVerified === true,
        },
      });
      created.push(q);
    }

    const count = created.length;
    if (resourceType === 'book') {
      await db.prisma.book.update({
        where: { id: resourceId },
        data: { questionsExtracted: { increment: count } },
      });
    } else {
      await db.prisma.questionPaper.update({
        where: { id: resourceId },
        data: { questionsExtracted: { increment: count } },
      });
    }

    return { questionsCreated: count, questions: created };
  }

  async downloadResource(resourceId, resourceType) {
    if (resourceType === 'book') {
      const b = await db.prisma.book.findFirst({ where: { id: resourceId, deletedAt: null } });
      if (!b) throw new AppError('Resource not found', 404);
      return { url: b.fileUrl, fileName: b.fileName };
    }
    const p = await db.prisma.questionPaper.findFirst({ where: { id: resourceId, deletedAt: null } });
    if (!p) throw new AppError('Resource not found', 404);
    return { url: p.fileUrl, fileName: p.fileName };
  }

  async getResources(filters, schoolId) {
    const { page, limit, skip } = parsePagination(filters);
    const type = filters.type || 'book';

    if (type === 'question_paper') {
      const where = { schoolId, deletedAt: null };
      if (filters.processingStatus) where.processingStatus = filters.processingStatus;
      const [total, rows] = await Promise.all([
        db.prisma.questionPaper.count({ where }),
        db.prisma.questionPaper.findMany({
          where,
          skip,
          take: limit,
          orderBy: { createdAt: 'desc' },
        }),
      ]);
      return { data: rows.map((r) => ({ ...r, _type: 'question_paper' })), meta: buildMeta(total, page, limit) };
    }

    const where = { schoolId, deletedAt: null };
    if (filters.processingStatus) where.processingStatus = filters.processingStatus;
    const [total, rows] = await Promise.all([
      db.prisma.book.count({ where }),
      db.prisma.book.findMany({
        where,
        skip,
        take: limit,
        orderBy: { createdAt: 'desc' },
      }),
    ]);
    return { data: rows.map((r) => ({ ...r, _type: 'book' })), meta: buildMeta(total, page, limit) };
  }

  /**
   * Class → subject → book folder → chapter PDFs, from LOCAL_CBSE_LIBRARY_ROOT (if set) merged with
   * this school’s imported books (`metadata.localLibraryRel`). Each chapter includes `rel` for
   * automated test generation (`localLibraryRel`) when the PDF is registered as a book.
   */
  async getCbseCurriculumTree(schoolId) {
    const rootMap = new Map();
    let diskPdfCount = 0;
    const root = appConfig.localCbseLibraryRoot;
    if (root) {
      const rootResolved = path.resolve(root);
      if (fsSync.existsSync(rootResolved)) {
        const pdfs = await walkPdfFiles(rootResolved);
        diskPdfCount = pdfs.length;
        for (const full of pdfs) {
          const rel = path.relative(rootResolved, full).replace(/\\/g, '/');
          addPdfToCbseTree(rootMap, rel, null);
        }
      }
    }

    const books = await db.prisma.book.findMany({
      where: { schoolId, deletedAt: null },
      select: { id: true, metadata: true },
    });
    for (const b of books) {
      const m = b.metadata && typeof b.metadata === 'object' ? b.metadata : {};
      const lr = typeof m.localLibraryRel === 'string' && m.localLibraryRel ? m.localLibraryRel : null;
      if (!lr) continue;
      addPdfToCbseTree(rootMap, lr, b.id);
    }

    return {
      diskRootConfigured: Boolean(root),
      diskPdfCount,
      importedBooksWithPath: books.filter((b) => {
        const m = b.metadata && typeof b.metadata === 'object' ? b.metadata : {};
        return typeof m.localLibraryRel === 'string' && m.localLibraryRel;
      }).length,
      classes: serializeCbseTree(rootMap),
    };
  }

  async verifyExtractedQuestions(resourceId, resourceType, questionUpdates, verifierId) {
    for (const u of questionUpdates) {
      const questionId = u.extractedQuestionId;
      if (u.questionPatch) {
        await db.prisma.question.update({
          where: { id: questionId },
          data: u.questionPatch,
        });
      }
      await db.prisma.extractedQuestion.updateMany({
        where: {
          resourceId,
          resourceType,
          questionId,
        },
        data: {
          isVerified: u.markVerified !== false,
          verifiedBy: verifierId,
          verifiedAt: new Date(),
        },
      });
    }
    return { ok: true };
  }
}

module.exports = new ResourceService();
