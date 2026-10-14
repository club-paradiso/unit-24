import { content } from '../content';
import { assertImportContent, questionMatchesContent } from './content-progress';
import { emptyState } from './progress';
import { choiceQuestion, buildQuestions } from './quiz';
import { seeded } from './random';

it('accepts generated questions in every practice mode', () => {
  for (const mode of ['mixed', 'codes', 'alphabet', 'due', 'mistakes'] as const) {
    for (const q of buildQuestions({ mode, items: content.items, progress: {}, now: 1, rng: seeded(7) })) {
      expect(questionMatchesContent(q)).toBe(true);
    }
  }
});
it('rejects invented answers, subjects and distractors even with a real item id', () => {
  const q = choiceQuestion(content.items[0]!, 'code-to-meaning', content.items, seeded(1), 'q');
  expect(questionMatchesContent({ ...q, answer: 'Invented', options: ['Invented'] })).toBe(false);
  expect(questionMatchesContent({ ...q, subject: 'Neighboring agency code' })).toBe(false);
  expect(questionMatchesContent({ ...q, options: [...q.options, 'Invented'] })).toBe(false);
});
it('refuses to import unknown source references', () => {
  const q = choiceQuestion(content.items[0]!, 'code-to-meaning', content.items, seeded(1), 'q');
  expect(() => assertImportContent({ ...emptyState(), activeSession: { id: 's', mode: 'codes', startedAt: 1, cursor: 0, answers: [], questions: [{ ...q, itemIds: ['unknown'] }] } })).toThrow(/source-backed/);
});
