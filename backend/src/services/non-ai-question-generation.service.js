/**
 * Pattern-based question drafting from plain chapter text (no ML).
 * Aligns with NON_AI_QUESTION_GENERATION.md: definitions, fill-in-blank, true/false,
 * exercise-style lines, light validation.
 */

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function cleanText(text) {
  return String(text || '')
    .replace(/\r\n/g, '\n')
    .replace(/[\t ]+/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

/** @typedef {{ term: string, explanation: string }} Definition */

function extractDefinitions(text) {
  const defs = [];
  const re =
    /\b([A-Z][A-Za-z]+(?:\s+[A-Za-z][a-z]*){0,5})\s+(?:is|are|refers to|means)\s+([^.!?\n\r]{10,350})/gi;
  let m;
  while ((m = re.exec(text)) !== null) {
    const term = m[1].replace(/\s+/g, ' ').trim();
    let explanation = (m[2] || '').replace(/\s+/g, ' ').trim();
    if (term.length < 3 || term.length > 90) continue;
    if (explanation.length < 12 || explanation.length > 400) continue;
    if (/^(is|are|the|a|an|of)$/i.test(term)) continue;
    defs.push({ term, explanation });
  }
  const seen = new Set();
  const out = [];
  for (const d of defs) {
    const k = d.term.toLowerCase();
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(d);
  }
  return out;
}

function extractExerciseSingleLines(text) {
  const lines = text.split('\n');
  const re = /^\s*(?:Q(?:uestion)?\.?\s*)?(\d{1,3})[\.\)]\s+(\S.{15,600})$/i;
  const out = [];
  for (const line of lines) {
    const m = line.match(re);
    if (!m) continue;
    const body = m[2].trim();
    if (body.length < 20) continue;
    if (/^(True|False|Yes|No)\s*[\.\?]/i.test(body)) continue;
    out.push(body);
  }
  return [...new Set(out)];
}

function splitIntoSentences(text) {
  const parts = text.split(/(?<=[.!?])\s+/);
  return parts.map((s) => s.trim()).filter((s) => s.length >= 35 && s.length <= 320);
}

function pickKeywordForBlank(sentence) {
  const patterns = [
    /\b[A-Z][a-z]{3,}(?:\s+[A-Z][a-z]+){0,2}\b/,
    /\b\d+(?:\.\d+)?\s*(?:kg|g|mg|m|cm|mm|km|L|ml|°C|°F)\b/i,
    /\b[a-z]{5,}(?:tion|ment|ness|ity|ism|ance|ence)\b/i,
  ];
  for (const p of patterns) {
    const m = sentence.match(p);
    if (m && m[0].length > 3 && m[0].length < 55) return m[0];
  }
  const words = sentence.split(/\s+/).filter((w) => /^[A-Za-z]+$/.test(w) && w.length > 7);
  return words[0] || null;
}

function statementLooksDeclarative(s) {
  if (s.length < 25 || s.length > 400) return false;
  if (/\?/.test(s)) return false;
  if (/^\d+[\.\)]/.test(s)) return false;
  return /\b(is|are|was|were|has|have|means|includes|consists|contains|defined)\b/i.test(s);
}

function inferTrueFalse(statement) {
  const lower = statement.toLowerCase();
  const strongNeg =
    /\b(never|not\s|no\s|none\b|false\b|incorrect|impossible|cannot|can't|isn't|aren't|wasn't|weren't|doesn't|don't|didn't)\b/.test(
      lower
    );
  return !strongNeg;
}

function buildMcqFromDefinition(def, otherDefs) {
  const correctText =
    def.explanation.length > 140 ? `${def.explanation.slice(0, 137).trim()}…` : def.explanation.trim();
  const distractors = [];
  for (const o of otherDefs) {
    if (distractors.length >= 3) break;
    if (o.term === def.term) continue;
    const t =
      o.explanation.length > 110 ? `${o.explanation.slice(0, 107).trim()}…` : o.explanation.trim();
    if (t && t !== correctText) distractors.push(t);
  }
  while (distractors.length < 3) {
    distractors.push('None of the statements above apply.');
  }
  const raw = [
    { text: correctText, isCorrect: true },
    ...distractors.slice(0, 3).map((text) => ({ text, isCorrect: false })),
  ];
  shuffle(raw);
  return {
    questionType: 'mcq',
    questionText: `Which statement best describes “${def.term}”?`,
    questionData: { generatedBy: 'non_ai', pattern: 'definition_mcq' },
    options: raw.map((o, i) => ({
      optionText: o.text,
      isCorrect: o.isCorrect,
      optionOrder: i,
    })),
  };
}

function buildFillBlank(sentence, keyword) {
  const blanked = sentence.replace(keyword, '_____');
  return {
    questionType: 'fill_blank',
    questionText: `Fill in the blank: ${blanked}`,
    questionData: {
      generatedBy: 'non_ai',
      pattern: 'keyword_blank',
      expected: keyword.trim(),
    },
    options: [],
  };
}

function buildTrueFalse(statement) {
  const isTrue = inferTrueFalse(statement);
  const stem = `True or False: ${statement}`;
  const opts = shuffle([
    { optionText: 'True', isCorrect: isTrue },
    { optionText: 'False', isCorrect: !isTrue },
  ]);
  return {
    questionType: 'true_false',
    questionText: stem,
    questionData: { generatedBy: 'non_ai', pattern: 'statement_tf' },
    options: opts.map((o, i) => ({
      optionText: o.optionText,
      isCorrect: o.isCorrect,
      optionOrder: i,
    })),
  };
}

const UNCLEAR = [
  /\b(?:etc\.?|approximately|about|roughly)\b/i,
  /\?\s*\?/,
  /\.{4,}/,
  /\b(?:maybe|perhaps|possibly)\b/i,
];

function isClearQuestionText(q) {
  return !UNCLEAR.some((p) => p.test(q));
}

function validateDraft(q) {
  if (!q || !q.questionText || String(q.questionText).trim().length < 15) return false;
  if (!isClearQuestionText(q.questionText)) return false;
  if (q.questionType === 'mcq') {
    const opts = Array.isArray(q.options) ? q.options : [];
    if (opts.length < 2) return false;
    const correct = opts.filter((o) => o.isCorrect);
    if (correct.length !== 1) return false;
    if (opts.some((o) => !String(o.optionText || '').trim())) return false;
  }
  if (q.questionType === 'true_false') {
    const opts = Array.isArray(q.options) ? q.options : [];
    if (opts.length !== 2) return false;
    if (opts.filter((o) => o.isCorrect).length !== 1) return false;
  }
  if (q.questionType === 'fill_blank') {
    const exp = q.questionData && q.questionData.expected;
    if (!exp || String(exp).trim().length < 2) return false;
    if (!String(q.questionText).includes('_____')) return false;
  }
  return true;
}

/**
 * @param {string} text raw chapter / book text
 * @param {{ maxMcq?: number, maxFillBlank?: number, maxTrueFalse?: number }} caps
 * @returns {Array<object>} payloads compatible with questionService.createQuestion (minus school fields)
 */
function generateFromChapterText(text, caps = {}) {
  const maxMcq = Math.min(20, Math.max(0, Number(caps.maxMcq) || 12));
  const maxFillBlank = Math.min(20, Math.max(0, Number(caps.maxFillBlank) || 10));
  const maxTrueFalse = Math.min(20, Math.max(0, Number(caps.maxTrueFalse) || 10));

  const clean = cleanText(text);
  if (clean.length < 80) return [];

  const definitions = extractDefinitions(clean);
  const exerciseLines = extractExerciseSingleLines(clean);
  const sentences = splitIntoSentences(clean);

  const drafts = [];

  for (let i = 0; i < definitions.length && drafts.filter((d) => d.questionType === 'mcq').length < maxMcq; i += 1) {
    const others = definitions.filter((_, j) => j !== i);
    drafts.push(buildMcqFromDefinition(definitions[i], others));
  }

  let fb = 0;
  for (const s of sentences) {
    if (fb >= maxFillBlank) break;
    const kw = pickKeywordForBlank(s);
    if (!kw || !s.includes(kw)) continue;
    if (s.indexOf(kw) === 0) continue;
    drafts.push(buildFillBlank(s, kw));
    fb += 1;
  }

  let tf = 0;
  const tfSeen = new Set();
  const tfSources = [...exerciseLines, ...sentences.filter(statementLooksDeclarative)];
  for (const stmt of tfSources) {
    if (tf >= maxTrueFalse) break;
    if (!statementLooksDeclarative(stmt) && !exerciseLines.includes(stmt)) continue;
    const key = stmt.slice(0, 120).toLowerCase().replace(/\s+/g, ' ');
    if (tfSeen.has(key)) continue;
    tfSeen.add(key);
    drafts.push(buildTrueFalse(stmt));
    tf += 1;
  }

  return drafts.filter(validateDraft);
}

module.exports = {
  cleanText,
  extractDefinitions,
  extractExerciseSingleLines,
  generateFromChapterText,
  validateDraft,
};
