const pdfParse = require('pdf-parse');

/**
 * Pull plain text from a PDF buffer (no ML — layout-aware extraction is limited).
 */
async function extractTextFromPdfBuffer(buffer) {
  const data = await pdfParse(buffer);
  return (data.text || '').replace(/\r\n/g, '\n').trim();
}

/**
 * Split exam-style plain text into candidate question blocks using numbered lines.
 * Works best when questions start with "1." / "1)" / "Q1" style markers.
 */
function splitNumberedQuestionBlocks(text) {
  if (!text) return [];
  const lines = text.split(/\n/);
  const blocks = [];
  let current = [];
  // Start of a new item: optional Q prefix, digits, . or )
  const itemStart = /^\s*(?:Q(?:uestion)?\s*)?(\d{1,3})[\.\)]\s+(\S.*)$/i;

  const flush = () => {
    const chunk = current.join('\n').trim();
    if (chunk.length >= 15) blocks.push(chunk);
    current = [];
  };

  for (const line of lines) {
    if (itemStart.test(line) && current.length > 0) {
      flush();
    }
    current.push(line);
  }
  flush();

  return blocks
    .flatMap((b) => {
      const lines = b.split(/\n/);
      const idx = lines.findIndex((l) => itemStart.test(l));
      if (idx === -1) return [];
      return [lines.slice(idx).join('\n').trim()];
    })
    .filter((b) => b.length >= 15);
}

/**
 * Very light "MCQ detector": lines starting with (a)/(b)/(A. etc.) → treat as options.
 */
function inferOptionsFromBlock(block) {
  const optionLine = /^\s*\(([a-zA-Z])\)\s*(.+)$/;
  const lines = block.split(/\n/).map((l) => l.trim()).filter(Boolean);
  const stemLines = [];
  const options = [];
  let order = 0;
  for (const line of lines) {
    const m = line.match(optionLine);
    if (m) {
      options.push({
        optionText: m[2].trim(),
        isCorrect: false,
        optionOrder: order,
      });
      order += 1;
    } else {
      stemLines.push(line);
    }
  }
  const questionText = stemLines.join('\n').trim() || block.trim();
  return { questionText, options };
}

module.exports = {
  extractTextFromPdfBuffer,
  splitNumberedQuestionBlocks,
  inferOptionsFromBlock,
};
