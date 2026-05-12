const resourceService = require('../services/resource.service');

const { AppError } = require('../middleware/error.middleware');

function parseMetadata(raw) {
  if (!raw) return {};
  try {
    return typeof raw === 'string' ? JSON.parse(raw) : raw;
  } catch {
    return {};
  }
}

exports.uploadBook = async (req, res, next) => {
  try {
    if (!req.file) {
      return next(new AppError('File required', 400));
    }
    const parsed = parseMetadata(req.body.metadata);
    const metadata = {
      ...parsed,
      title: req.body.title ?? parsed.title,
      author: req.body.author ?? parsed.author,
      classId: req.body.classId ?? parsed.classId,
      subjectId: req.body.subjectId ?? parsed.subjectId,
      tags: Array.isArray(req.body.tags) ? req.body.tags : parsed.tags || [],
    };
    const book = await resourceService.uploadResource(
      {
        buffer: req.file.buffer,
        originalname: req.file.originalname,
        mimetype: req.file.mimetype,
        resourceType: 'book',
      },
      metadata,
      req.user.id
    );
    res.status(201).json({ status: 'success', data: book });
  } catch (e) {
    next(e);
  }
};

exports.registerBookFromUrl = async (req, res, next) => {
  try {
    const book = await resourceService.registerBookFromPublicUrl(req.body, req.user.id);
    res.status(201).json({ status: 'success', data: book });
  } catch (e) {
    next(e);
  }
};

exports.importLocalCbseLibrary = async (req, res, next) => {
  try {
    const { dryRun, limit } = req.body;
    const result = await resourceService.importCbseLibraryFromDisk(req.user.id, {
      dryRun,
      limit: limit != null ? limit : null,
    });
    res.status(200).json({ status: 'success', data: result });
  } catch (e) {
    next(e);
  }
};

exports.uploadPaper = async (req, res, next) => {
  try {
    if (!req.file) {
      return next(new AppError('File required', 400));
    }
    const parsed = parseMetadata(req.body.metadata);
    const meta = {
      ...parsed,
      title: req.body.title ?? parsed.title,
      examName: req.body.examName ?? parsed.examName,
      year: req.body.year ?? parsed.year,
      classId: req.body.classId ?? parsed.classId,
      subjectId: req.body.subjectId ?? parsed.subjectId,
      tags: Array.isArray(req.body.tags) ? req.body.tags : parsed.tags || [],
    };
    const paper = await resourceService.uploadResource(
      {
        buffer: req.file.buffer,
        originalname: req.file.originalname,
        mimetype: req.file.mimetype,
        resourceType: 'question_paper',
      },
      meta,
      req.user.id
    );
    res.status(201).json({ status: 'success', data: paper });
  } catch (e) {
    next(e);
  }
};

exports.cbseCurriculumTree = async (req, res, next) => {
  try {
    if (!req.user.schoolId) {
      return res.json({
        status: 'success',
        data: {
          diskRootConfigured: false,
          diskPdfCount: 0,
          importedBooksWithPath: 0,
          classes: [],
        },
      });
    }
    const data = await resourceService.getCbseCurriculumTree(req.user.schoolId);
    res.json({ status: 'success', data });
  } catch (e) {
    next(e);
  }
};

exports.list = async (req, res, next) => {
  try {
    if (!req.user.schoolId) {
      return res.json({ status: 'success', data: [], meta: { total: 0, page: 1, limit: 20, totalPages: 1 } });
    }
    const result = await resourceService.getResources(req.query, req.user.schoolId);
    res.json({ status: 'success', ...result });
  } catch (e) {
    next(e);
  }
};

exports.verify = async (req, res, next) => {
  try {
    const { resourceType } = req.params;
    await resourceService.verifyExtractedQuestions(
      req.params.id,
      resourceType,
      req.body.updates,
      req.user.id
    );
    res.json({ status: 'success' });
  } catch (e) {
    next(e);
  }
};

exports.extractFromDocument = async (req, res, next) => {
  try {
    const body = req.body && typeof req.body === 'object' ? req.body : {};
    const extractOptions = {};
    if (['numbered_first', 'non_ai_only', 'combined'].includes(body.strategy)) {
      extractOptions.strategy = body.strategy;
    }
    if (body.maxMcq != null && body.maxMcq !== '') extractOptions.maxMcq = Number(body.maxMcq);
    if (body.maxFillBlank != null && body.maxFillBlank !== '') extractOptions.maxFillBlank = Number(body.maxFillBlank);
    if (body.maxTrueFalse != null && body.maxTrueFalse !== '') extractOptions.maxTrueFalse = Number(body.maxTrueFalse);

    const result = await resourceService.extractQuestionsFromDocument(
      req.params.id,
      req.params.resourceType,
      req.user.id,
      extractOptions
    );
    res.status(201).json({ status: 'success', data: result });
  } catch (e) {
    next(e);
  }
};

exports.importQuestions = async (req, res, next) => {
  try {
    const result = await resourceService.importQuestionsForResource(
      req.params.id,
      req.params.resourceType,
      req.body.questions,
      req.user.id
    );
    res.status(201).json({ status: 'success', data: result });
  } catch (e) {
    next(e);
  }
};
