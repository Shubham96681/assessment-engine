const { splitNumberedQuestionBlocks, inferOptionsFromBlock } = require('../../src/services/resource-document-extraction.service');

describe('resource-document-extraction (non-AI heuristics)', () => {
  it('splits numbered blocks and drops preamble before first number', () => {
    const text = `Intro line not a question\n1. First question here?\nMore detail for one.\n2. Second question.`;
    const blocks = splitNumberedQuestionBlocks(text);
    expect(blocks.length).toBeGreaterThanOrEqual(2);
    expect(blocks[0]).toContain('First question');
    expect(blocks[1]).toContain('Second question');
  });

  it('detects parenthesized options', () => {
    const block = 'What is 2+2?\n(a) 3\n(b) 4\n(c) 5';
    const { questionText, options } = inferOptionsFromBlock(block);
    expect(questionText).toContain('2+2');
    expect(options.length).toBe(3);
    expect(options.every((o) => o.isCorrect === false)).toBe(true);
  });
});
