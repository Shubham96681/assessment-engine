/**
 * Convert exam stems to LaTeX segments — prose stays plain (spaces preserved);
 * only short math spans go to KaTeX.
 */

export type TextSegment = { kind: "text"; value: string };
export type MathSegment = { kind: "math"; latex: string; display: boolean };
export type Segment = TextSegment | MathSegment;

const TRIG = "sin|cos|tan|sec|cosec|cot";
const MAX_SEGMENT_INPUT = 4000;
const MAX_MATH_SPAN = 72;

const MATH_WORDS = new Set([
  "sin", "cos", "tan", "sec", "cosec", "cot", "theta", "pi", "prove", "hence",
  "given", "find", "value", "show", "if", "or", "and", "cm", "the", "of", "in",
  "to", "for", "use", "lies", "quadrant", "terms", "surds",
]);

/** Bounded patterns only — avoids OOM from greedy [^,;.]+ on long answers */
const INLINE_MATH_PATTERNS: RegExp[] = [
  new RegExp(
    `\\b(?:${TRIG})\\s*\\^\\{-1\\}\\s*\\(\\s*\\d+\\s*/\\s*\\d+\\s*\\)(?:\\s*\\+\\s*(?:${TRIG})\\s*\\^\\{-1\\}\\s*\\(\\s*\\d+\\s*/\\s*\\d+\\s*\\))*`,
    "gi",
  ),
  new RegExp(`\\b(?:${TRIG})\\s*θ\\s*=\\s*[\\d.]+(?:\\s*/\\s*[\\d.]+)?`, "gi"),
  new RegExp(`\\b(?:${TRIG})\\s*θ(?:\\s*cos\\s*θ)?`, "gi"),
  new RegExp(
    `\\b(?:${TRIG})\\s*\\(\\s*[A-Za-z]\\s*\\+\\s*[A-Za-z]\\s*\\)\\s*=\\s*\\([^)]{1,${MAX_MATH_SPAN}}\\)\\s*/\\s*\\([^)]{1,${MAX_MATH_SPAN}}\\)`,
    "gi",
  ),
  new RegExp(
    `\\b(?:${TRIG})\\s*\\(\\s*\\d*\\s*θ\\s*\\)\\s*=\\s*\\([^)]{1,${MAX_MATH_SPAN}}\\)\\s*/\\s*\\([^)]{1,${MAX_MATH_SPAN}}\\)`,
    "gi",
  ),
  new RegExp(`∠\\s*[A-Z]{1,4}\\s*=\\s*[^,;.\\n]{1,${MAX_MATH_SPAN}}`, "gi"),
  new RegExp(`π\\s*/\\s*\\d+`, "gi"),
  new RegExp(`√\\s*\\d+\\s*/\\s*\\d+`, "gi"),
  new RegExp(
    `\\b(?:cos|sin)\\s*\\(\\s*[A-Za-z]\\s*\\+\\s*[A-Za-z]\\s*\\)\\s*=\\s*-?√?\\s*\\d+\\s*/\\s*\\d+`,
    "gi",
  ),
  new RegExp(`\\bsin\\s*θ\\s*cos\\s*θ\\s*=\\s*√\\s*\\d+\\s*/\\s*\\d+`, "gi"),
  new RegExp(
    `(?:\\b(?:${TRIG})\\s+){1,2}[A-Z](?:\\s+[A-Z])?\\s*=\\s*\\([^)]{1,${MAX_MATH_SPAN}}\\)\\s*/\\s*\\([^)]{1,${MAX_MATH_SPAN}}\\)`,
    "gi",
  ),
  new RegExp(`√\\s*\\([^)]{1,40}\\)`, "gi"),
  new RegExp(`(?:[xyz]\\s*)?√\\s*\\(\\s*1\\s*-\\s*[xyz](?:\\^2|²)\\s*\\)`, "gi"),
  new RegExp(`\\d+\\s*°\\s*≤\\s*θ\\s*≤\\s*\\d+\\s*°?`, "gi"),
  new RegExp(
    `(?:\\d+\\s*)?x[²2]\\s*[+\\-−]\\s*(?:\\d+|[a-z]+)\\s*x\\s*[+\\-−]\\s*(?:\\d+|[a-z]+)\\s*=\\s*0`,
    "gi",
  ),
  new RegExp(`x[²2]\\s*[+\\-−]\\s*[a-z]\\s*x\\s*[+\\-−]\\s*[a-z]\\s*=\\s*0`, "gi"),
  new RegExp(
    `p_\\{n\\}\\s*=\\s*[sstαβγ]\\s*[·]?\\s*p_\\{n-1\\}\\s*[-−]\\s*[sstαβγ]\\s*[·]?\\s*p_\\{n-2\\}`,
    "gi",
  ),
  new RegExp(`\\b\\d+\\s*/\\s*\\d+\\b`, "gi"),
  new RegExp(`\\([A-Za-zαβγ]+\\s*\\+\\s*[A-Za-zαβγ]+\\)\\s*[²2]`, "gi"),
];

const SUBSCRIPT_UNICODE: Record<string, string> = {
  "\u2080": "0",
  "\u2081": "1",
  "\u2082": "2",
  "\u2083": "3",
  "\u2084": "4",
  "\u2085": "5",
  "\u2086": "6",
  "\u2087": "7",
  "\u2088": "8",
  "\u2089": "9",
  "\u208a": "+",
  "\u208b": "-",
  "\u208c": "=",
  "\u208d": "(",
  "\u208e": ")",
  "\u2090": "a",
  "\u2091": "e",
  "\u2093": "x",
  "\u2095": "h",
  "\u2096": "k",
  "\u2097": "l",
  "\u2098": "m",
  "\u2099": "n",
  "\u209a": "o",
  "\u209b": "p",
  "\u209c": "t",
};

const SUBSCRIPT_RUN = /[\u2080-\u208e\u2090-\u209c]+/g;

export type StandardMathSpan =
  | { kind: "text"; value: string }
  | { kind: "sup"; value: string }
  | { kind: "sub"; value: string };

const SUPERSCRIPT_MAP: Record<string, string> = {
  "\u00b2": "2",
  "\u00b3": "3",
  "\u00b9": "1",
  "\u2070": "0",
  "\u2074": "4",
  "\u2075": "5",
  "\u2076": "6",
  "\u2077": "7",
  "\u2078": "8",
  "\u2079": "9",
  "\u207f": "n",
};

const STANDARD_MATH_TOKEN =
  /(\^\{[^{}]+\}|_\{[^{}]+\}|\^[0-9A-Za-z+\-]+|(?<=[A-Za-zαβγδεζηθικλμνξοπρστυφχψω0-9\)\]])_[0-9A-Za-z+\-]+|[\u2080-\u208e\u2090-\u209c]+|[\u00b2\u00b3\u00b9\u2070-\u207f]+)/g;

const EXP_TO_UNICODE: Record<string, string> = {
  "0": "\u2070",
  "1": "\u00b9",
  "2": "\u00b2",
  "3": "\u00b3",
  "4": "\u2074",
  "5": "\u2075",
  "6": "\u2076",
  "7": "\u2077",
  "8": "\u2078",
  "9": "\u2079",
  n: "\u207f",
  "+": "\u207a",
  "-": "\u207b",
};

function expToUnicodeSuperscript(exp: string): string | null {
  if (!/^[0-9n+\-]+$/.test(exp)) return null;
  return [...exp].map((c) => EXP_TO_UNICODE[c] ?? c).join("");
}

const SEQ_ASCII_SUB = /\b([a-z])_(?!\{)([a-z0-9+\-]+)\b/g;

export function normalizePaperSequenceSubscripts(text: string): string {
  if (!text || !text.includes("_")) return text;
  return text.replace(SEQ_ASCII_SUB, "$1_{$2}");
}

/** Board-style subscripts + superscripts before UI/PDF split. */
export function normalizePaperMathNotation(text: string): string {
  if (!text) return text;
  return normalizePaperSuperscripts(normalizePaperSequenceSubscripts(text));
}

/** Board-style exponents (x^2 → x²; p_{n} unchanged). */
export function normalizePaperSuperscripts(text: string): string {
  if (!text || !text.includes("^")) return text;
  return text
    .replace(
      /([A-Za-zαβγδεζηθικλμνξοπρστυφχψω0-9)\]])\^\{([^{}]+)\}/g,
      (full, base: string, exp: string) => {
        const uni = expToUnicodeSuperscript(exp);
        return uni ? `${base}${uni}` : full;
      },
    )
    .replace(
      /([A-Za-zαβγδεζηθικλμνξοπρστυφχψω0-9)\]])\^([0-9n+\-]+)/g,
      (full, base: string, exp: string) => {
        const uni = expToUnicodeSuperscript(exp);
        return uni ? `${base}${uni}` : full;
      },
    );
}

/** Split prose into text / standard super- and sub-script spans for UI. */
export function splitStandardMathSpans(value: string): StandardMathSpan[] {
  if (!value) return [{ kind: "text", value: "" }];
  value = normalizePaperMathNotation(value);
  const spans: StandardMathSpan[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  STANDARD_MATH_TOKEN.lastIndex = 0;
  while ((m = STANDARD_MATH_TOKEN.exec(value)) !== null) {
    if (m.index > last) {
      spans.push({ kind: "text", value: value.slice(last, m.index) });
    }
    const tok = m[0];
    if (tok.startsWith("^{")) {
      spans.push({ kind: "sup", value: tok.slice(2, -1) });
    } else if (tok.startsWith("^")) {
      spans.push({ kind: "sup", value: tok.slice(1) });
    } else if (tok.startsWith("_{")) {
      spans.push({ kind: "sub", value: tok.slice(2, -1) });
    } else if (tok.startsWith("_")) {
      spans.push({ kind: "sub", value: tok.slice(1) });
    } else if (/[\u00b2\u00b3\u00b9\u2070-\u207f]/.test(tok)) {
      spans.push({ kind: "text", value: tok });
    } else {
      spans.push({
        kind: "sub",
        value: [...tok].map((c) => SUBSCRIPT_UNICODE[c] ?? c).join(""),
      });
    }
    last = m.index + tok.length;
  }
  if (last < value.length) {
    spans.push({ kind: "text", value: value.slice(last) });
  }
  return spans.length ? spans : [{ kind: "text", value }];
}

/** Unicode sub/superscripts → plain p_n, α^n (legacy). */
export function unicodeMathIndicesToPlain(text: string): string {
  if (!text || !SUBSCRIPT_RUN.test(text)) {
    SUBSCRIPT_RUN.lastIndex = 0;
    const sup = /[\u00b2\u00b3\u2070-\u207f]/;
    if (!sup.test(text)) return text;
  }
  SUBSCRIPT_RUN.lastIndex = 0;
  let out = text.replace(SUBSCRIPT_RUN, (run) => {
    const ascii = [...run].map((c) => SUBSCRIPT_UNICODE[c] ?? c).join("");
    return `_${ascii}`;
  });
  out = out.replace(/[\u00b2\u00b3\u2070-\u207f]+/g, (run) => {
    const map: Record<string, string> = {
      "\u00b2": "2",
      "\u00b3": "3",
      "\u2074": "4",
      "\u207f": "n",
    };
    const ascii = [...run].map((c) => map[c] ?? c).join("");
    return `^${ascii}`;
  });
  return out;
}

/** Unicode subscripts (pₙ₋₁) → LaTeX p_{n-1} for KaTeX; avoids □ in browsers/PDF. */
export function unicodeSubscriptsToLatex(text: string): string {
  if (!text || !SUBSCRIPT_RUN.test(text)) {
    SUBSCRIPT_RUN.lastIndex = 0;
    return text;
  }
  SUBSCRIPT_RUN.lastIndex = 0;
  return text.replace(SUBSCRIPT_RUN, (run) => {
    const ascii = [...run].map((c) => SUBSCRIPT_UNICODE[c] ?? c).join("");
    return `_{${ascii}}`;
  });
}

/** Restore spaces in English prose (PDF/UI parity with backend). */
export function normalizeProseGlued(text: string): string {
  if (!text || text.length > 800) return text;
  let out = text;
  const fixes: [RegExp, string, string?][] = [
    [/([a-z])([A-Z])/g, "$1 $2"],
    [/\bIf(?=tan|sin|cos|sec|cot|find|the|angle|prove)/gi, "If "],
    [/\band(?=tan|sin|cos|find|the)/gi, "and "],
    [/(\d+)and(?=tan|sin|cos)/gi, "$1 and "],
    [/\bfind(?=the)/gi, "find "],
    [/\bthe(?=values)/gi, "the "],
    [/\bvaluesof/gi, "values of "],
    [/\buseit\b/gi, "use it "],
    [/\bprove(?=that)/gi, "prove "],
    [/\bintriangle\b/gi, "in triangle "],
    [/\binterms\b/gi, "in terms "],
    [/\bliesin\b/gi, "lies in "],
    [/\bquadrant([IVX]+)/gi, "quadrant $1"],
  ];
  for (const [re, rep] of fixes) {
    out = out.replace(re, rep);
  }
  return out.replace(/ +/g, " ");
}

function normalizePlain(s: string): string {
  if (!s) return "";
  return s
    .replace(/\bsin\s*inverse\b/gi, "sin^{-1}")
    .replace(/\bcos\s*inverse\b/gi, "cos^{-1}")
    .replace(/\btan\s*inverse\b/gi, "tan^{-1}")
    .replace(/\b(sin|cos|tan|sec|cosec|cot)\s*⁻¹/gi, "$1^{-1}")
    .replace(/\b(sin|cos|tan|sec|cosec|cot)\s*−\s*1\b/gi, "$1^{-1}")
    .replace(/−/g, "-")
    .replace(/×/g, "\\times ")
    .replace(/·/g, "");
}

export function examPlainToLatex(plain: string): string {
  let s = unicodeSubscriptsToLatex(normalizePlain(plain.trim()));
  if (!s || s.length > MAX_MATH_SPAN * 2) return s.slice(0, MAX_MATH_SPAN * 2);

  s = s.replace(/θ/g, "\\theta ");
  s = s.replace(/π/g, "\\pi ");
  s = s.replace(/∠\s*/g, "\\angle ");
  s = s.replace(/√\s*\(([^)]+)\)/g, "\\sqrt{$1}");
  s = s.replace(/√\s*([0-9a-zA-Z]+)/g, "\\sqrt{$1}");
  s = s.replace(/²/g, "^{2}");
  s = s.replace(/³/g, "^{3}");
  s = s.replace(/≤/g, "\\leq ");
  s = s.replace(/≥/g, "\\geq ");
  s = s.replace(/≠/g, "\\neq ");
  s = s.replace(/±/g, "\\pm ");

  s = s.replace(
    new RegExp(`\\b(${TRIG})\\s*\\^\\{-1\\}\\s+([a-zA-Z])\\b`, "gi"),
    (_, f: string, v: string) => `\\${f.toLowerCase()}^{-1} ${v}`,
  );
  s = s.replace(
    new RegExp(`\\b(${TRIG})\\s*\\^\\{-1\\}`, "gi"),
    (_, f: string) => `\\${f.toLowerCase()}^{-1}`,
  );
  s = s.replace(/([a-zA-Z])\^2/g, "$1^{2}");
  s = s.replace(/([a-zA-Z])\^3/g, "$1^{3}");
  s = s.replace(/√\s*(\d+)\s*\/\s*(\d+)/g, "\\frac{\\sqrt{$1}}{$2}");
  s = s.replace(/\(([^()]+)\)\s*\/\s*\(([^()]+)\)/g, "\\frac{$1}{$2}");
  s = s.replace(new RegExp(`\\b(${TRIG})\\b`, "gi"), (_, f: string) => `\\${f.toLowerCase()}`);
  s = s.replace(/\((\d+)\s*\/\s*(\d+)\)/g, "\\left(\\frac{$1}{$2}\\right)");
  s = s.replace(/(\d+)\s*\/\s*(\d+)/g, "\\frac{$1}{$2}");
  s = s.replace(/(\w+)\s*\*\s*(\d+)/g, "$1 \\cdot $2");
  return s.replace(/\s+/g, " ").trim();
}

function proseRatio(chunk: string): number {
  const words = chunk.match(/[a-zA-Z]{3,}/g) || [];
  if (!words.length) return 0;
  const nonMath = words.filter((w) => !MATH_WORDS.has(w.toLowerCase())).length;
  return nonMath / words.length;
}

function shouldDisplayMath(latex: string, plain: string): boolean {
  if (plain.includes("\n")) return true;
  if (plain.length > 48 && /\\frac|\\sqrt/.test(latex)) return true;
  if ((plain.match(/[=+]/g) || []).length >= 2 && /\\frac|\\sqrt|\\sin|\\tan/.test(latex)) {
    return true;
  }
  return false;
}

function latexRenderable(latex: string): boolean {
  if (!latex || latex.length > 160) return false;
  if (/^\s*\[|'\s*,\s*'/.test(latex)) return false;
  if (/^\s*=\s*\\frac/.test(latex)) return false;
  return true;
}

type Span = { start: number; end: number; text: string };

function findMathSpans(clause: string): Span[] {
  const spans: Span[] = [];
  for (const re of INLINE_MATH_PATTERNS) {
    re.lastIndex = 0;
    let m: RegExpExecArray | null;
    let guard = 0;
    while ((m = re.exec(clause)) !== null && guard++ < 64) {
      const text = m[0];
      if (!text.length) {
        re.lastIndex = m.index + 1;
        continue;
      }
      spans.push({ start: m.index, end: m.index + text.length, text });
    }
  }
  if (!spans.length) return [];
  spans.sort((a, b) => a.start - b.start || b.end - a.end);
  const merged: Span[] = [];
  for (const sp of spans) {
    const prev = merged[merged.length - 1];
    if (!prev || sp.start >= prev.end) {
      merged.push(sp);
    } else if (sp.end > prev.end && sp.start >= prev.start) {
      merged[merged.length - 1] = sp;
    }
  }
  return merged;
}

function splitMixedClause(clause: string): Segment[] {
  const spans = findMathSpans(clause);
  if (!spans.length) {
    return [{ kind: "text", value: normalizeProseGlued(clause) }];
  }
  const out: Segment[] = [];
  let last = 0;
  for (const sp of spans) {
    if (sp.start > last) {
      out.push({ kind: "text", value: normalizeProseGlued(clause.slice(last, sp.start)) });
    }
    const latex = examPlainToLatex(sp.text);
    if (latex && latexRenderable(latex)) {
      out.push({
        kind: "math",
        latex,
        display: shouldDisplayMath(latex, sp.text),
      });
    } else {
      out.push({ kind: "text", value: sp.text });
    }
    last = sp.end;
  }
  if (last < clause.length) {
    out.push({ kind: "text", value: normalizeProseGlued(clause.slice(last)) });
  }
  return out;
}

function mergeTextSegments(segments: Segment[]): Segment[] {
  const merged: Segment[] = [];
  for (const seg of segments) {
    const prev = merged[merged.length - 1];
    if (seg.kind === "text" && prev?.kind === "text") {
      merged[merged.length - 1] = { kind: "text", value: prev.value + seg.value };
    } else {
      merged.push(seg);
    }
  }
  return merged;
}

function parsePreDelimited(text: string): Segment[] {
  const segments: Segment[] = [];
  let last = 0;
  const combined = /\$\$([^$]+)\$\$|\$([^$\n]+)\$/g;
  let m: RegExpExecArray | null;
  let guard = 0;
  while ((m = combined.exec(text)) !== null && guard++ < 128) {
    if (m.index > last) {
      segments.push({ kind: "text", value: text.slice(last, m.index) });
    }
    const display = m[0].startsWith("$$");
    const latex = (display ? m[1] : m[2] || "").trim();
    if (latexRenderable(latex)) {
      segments.push({ kind: "math", latex, display });
    } else {
      segments.push({ kind: "text", value: m[0] });
    }
    last = m.index + m[0].length;
    if (!m[0].length) last += 1;
  }
  if (last < text.length) {
    segments.push({ kind: "text", value: text.slice(last) });
  }
  return segments.length ? segments : [{ kind: "text", value: text }];
}

function splitIntoClauses(text: string): string[] {
  const parts: string[] = [];
  const re =
    /(\bprove\s+that\s*:?\s*|\bHence\s*,?\s*|\bOR\s+(?:\(|prove\b)|\.\s+(?=[A-Z(]))/gi;
  let last = 0;
  let m: RegExpExecArray | null;
  let guard = 0;
  while ((m = re.exec(text)) !== null && guard++ < 256) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    parts.push(m[0]);
    last = m.index + m[0].length;
    if (!m[0].length) last += 1;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts.length ? parts : [text];
}

/** Split exam stem into prose + KaTeX segments. */
export function segmentExamMath(text: string): Segment[] {
  if (!text) return [];
  text = normalizeProseGlued(text);
  if (text.length > MAX_SEGMENT_INPUT) {
    return [{ kind: "text", value: formatListLikeAnswer(text) }];
  }
  if (/^\s*\[/.test(text) && /'/.test(text)) {
    return [{ kind: "text", value: formatListLikeAnswer(text) }];
  }
  if (/\$[^$]+\$/.test(text) || /\$\$[^$]+\$\$/.test(text)) {
    return parsePreDelimited(text);
  }

  const out: Segment[] = [];
  const blocks = text.split(/\n(?=\([ivx]+\)\s)/i);
  for (const block of blocks) {
    for (const clause of splitIntoClauses(block)) {
      out.push(...splitMixedClause(clause));
    }
  }
  return mergeTextSegments(out.length ? out : [{ kind: "text", value: text }]);
}

const ROMAN = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"] as const;

const SUBPART_PREFIX = /^\s*\(\s*(?:i{1,3}|iv|v|vi{0,3}|ix|x|[a-z])\s*\)\s*/i;

const DICT_ENTRY =
  /['"]?(prove|hence|part\s*\d+|answer|solution)['"]?\s*:\s*['"]([\s\S]+?)['"](?=\s*[,})\]]|\s*$)/gi;

const GIBBERISH = /cos\||A---|\\2\/|mathsf\s*\{/i;

function romanLabel(index: number): string {
  return `(${ROMAN[index] ?? index + 1})`;
}

function stripSubpartPrefixes(text: string): string {
  let out = text.trim();
  for (let n = 0; n < 6; n++) {
    const m = SUBPART_PREFIX.exec(out);
    if (!m) break;
    out = out.slice(m[0].length).trim();
  }
  return out.replace(/([0-9°θπ√)\]]+)\s*,\s*$/u, "$1").trim();
}

function isGibberish(item: string): boolean {
  const t = item.trim();
  if (t.length < 4) return true;
  if (GIBBERISH.test(t)) return true;
  const alnum = [...t].filter((c) => /[a-z0-9]/i.test(c)).length;
  return alnum < Math.max(6, t.length / 8);
}

function parseQuotedList(text: string): string[] | null {
  const t = text.trim();
  if (!t.startsWith("[") || !t.includes("'")) return null;
  const items = [...t.matchAll(/'((?:\\'|[^'])*)'/g)].map((m) =>
    m[1].replace(/\\'/g, "'"),
  );
  return items.length ? items : null;
}

function parseDictBlob(text: string): string[] | null {
  const items = [...text.matchAll(DICT_ENTRY)].map((m) => m[2].trim());
  return items.length ? items : null;
}

/** Insert newline before (ii) glued to math e.g. √10/3(ii). */
export function unglueSubparts(text: string): string {
  let out = text;
  const glued =
    /([0-9°√²³π)\w/])\s*\(\s*(i{1,3}|iv|v|vi{0,3}|vii|viii|ix|x)\s*\)/gi;
  out = out.replace(glued, "$1\n($2) ");
  return out.replace(/\n{3,}/g, "\n\n");
}

export type AnswerSubpart = { label: string; body: string };

const SUBPART_LINE =
  /^\s*\(\s*(i{1,3}|iv|v|vi{0,3}|vii|viii|ix|x)\s*\)\s*(.*)$/i;

/** Split formatted answer into labeled blocks for UI/PDF. */
export function splitAnswerSubparts(text: string): AnswerSubpart[] {
  const formatted = unglueSubparts(formatListLikeAnswer(text || ""));
  if (!formatted) return [];
  const rows: AnswerSubpart[] = [];
  for (const line of formatted.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const m = SUBPART_LINE.exec(trimmed);
    if (m) {
      rows.push({
        label: `(${m[1].toLowerCase()})`,
        body: (m[2] || "").trim(),
      });
    } else if (rows.length) {
      const last = rows[rows.length - 1];
      last.body = `${last.body} ${trimmed}`.trim();
    } else {
      rows.push({ label: "", body: trimmed });
    }
  }
  const labeled = rows.filter((r) => r.body);
  return labeled.length >= 2 ? labeled : [];
}

/** Format Python-list / dict answers; fix duplicate (i)(i) labels. */
export function formatListLikeAnswer(text: string): string {
  const t = unglueSubparts(text.trim());
  if (!t) return t;

  let items = parseQuotedList(t) ?? parseDictBlob(t);
  if (items) {
    const cleaned = items
      .map((item) => stripSubpartPrefixes(item))
      .filter((body) => body && !isGibberish(body));
    if (!cleaned.length) {
      return "[Answer incomplete — regenerate this question]";
    }
    return cleaned.map((body, i) => `${romanLabel(i)} ${body}`).join("\n");
  }

  if (/\(\s*i{1,3}\s*\)/i.test(t) || t.includes("\n")) {
    const chunks = t.split(/\n|(?=\(\s*(?:i{1,3}|iv|v)\s*\))/i).filter(Boolean);
    if (chunks.length >= 2) {
      const cleaned = chunks
        .map((ch) => stripSubpartPrefixes(ch))
        .filter((body) => body && !isGibberish(body));
      if (cleaned.length) {
        return cleaned.map((body, i) => `${romanLabel(i)} ${body}`).join("\n");
      }
    }
  }

  return stripSubpartPrefixes(t)
    .replace(/\bs\s+solve\b/gi, "Solve")
    .replace(/\(\s*[m-z]\s*\)\s*,\s*/gi, "");
}

/** Split on **bold** markers first (handled by QuestionContent). */
export function segmentWithBoldParts(
  text: string,
): { bold: boolean; segments: Segment[] }[] {
  const normalized = formatListLikeAnswer(text);
  if (normalized.length > MAX_SEGMENT_INPUT) {
    return [{ bold: false, segments: [{ kind: "text", value: normalized }] }];
  }
  const BOLD = /\*\*([^*]+)\*\*/g;
  const parts: { bold: boolean; segments: Segment[] }[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  let guard = 0;
  while ((m = BOLD.exec(normalized)) !== null && guard++ < 64) {
    const idx = m.index;
    if (idx > last) {
      parts.push({ bold: false, segments: segmentExamMath(normalized.slice(last, idx)) });
    }
    parts.push({ bold: true, segments: [{ kind: "text", value: m[1] }] });
    last = idx + m[0].length;
  }
  if (last < normalized.length) {
    parts.push({ bold: false, segments: segmentExamMath(normalized.slice(last)) });
  }
  return parts.length ? parts : [{ bold: false, segments: segmentExamMath(normalized) }];
}
