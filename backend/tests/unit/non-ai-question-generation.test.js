const nonAi = require('../../src/services/non-ai-question-generation.service');

describe('non-ai-question-generation.service', () => {
  const sampleChapter = `
Photosynthesis is the process by which plants convert light energy into chemical energy.
Cellular respiration is the process cells use to break down glucose and produce ATP.

Exercise 1
1. The mitochondrion is the powerhouse of the cell.
2. DNA contains genetic information for the organism.

3. Water boils at 100 degrees Celsius at sea level.
`;

  it('extracts definitions and generates validated drafts', () => {
    const defs = nonAi.extractDefinitions(sampleChapter);
    expect(defs.length).toBeGreaterThanOrEqual(1);
    expect(defs.some((d) => /photosynthesis/i.test(d.term))).toBe(true);

    const drafts = nonAi.generateFromChapterText(sampleChapter, {
      maxMcq: 4,
      maxFillBlank: 4,
      maxTrueFalse: 4,
    });
    expect(drafts.length).toBeGreaterThan(0);
    for (const d of drafts) {
      expect(nonAi.validateDraft(d)).toBe(true);
    }
    const types = new Set(drafts.map((d) => d.questionType));
    expect(types.has('mcq') || types.has('fill_blank') || types.has('true_false')).toBe(true);
  });

  it('extracts numbered exercise-style lines', () => {
    const lines = nonAi.extractExerciseSingleLines(sampleChapter);
    expect(lines.some((l) => /mitochondrion/i.test(l))).toBe(true);
  });
});
