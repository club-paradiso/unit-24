import { content, getItem, getLesson } from '../content';
import type { ProgressState } from './progress';
import type { Question } from './quiz';

/** Structural validity cannot prove that a restored answer came from the card. */
export function questionMatchesContent(q: Question): boolean {
  const items = q.itemIds.map(getItem);
  if (items.some(i => !i)) return false;
  if (q.type === 'spell') {
    return items.every(i => i!.kind === 'letter')
      && q.subject === items.map(i => i!.term).join(' ')
      && q.answer === items.map(i => i!.answer).join(' ')
      && q.answerWords.every((word, n) => word === items[n]!.answer);
  }
  const item = items[0]!;
  if ((q.type === 'letter-to-word') !== (item.kind === 'letter')) return false;
  const reverse = q.type === 'meaning-to-code';
  const pool = content.items.filter(i => i.kind === item.kind);
  return q.subject === (reverse ? item.answer : item.term)
    && q.answer === (reverse ? item.term : item.answer)
    && q.options.every(option => pool.some(i => (reverse ? i.term : i.answer) === option));
}

export function lessonDraftMatchesContent(id: string, state: ProgressState): boolean {
  const draft = state.lessonDrafts[id];
  const lesson = getLesson(id);
  return !!draft && !!lesson && draft.contentVersion === content.content_version
    && draft.questions.every(q => questionMatchesContent(q) && q.itemIds.every(itemId => lesson.item_ids.includes(itemId)))
    && (draft.phase !== 'study' || draft.index < lesson.item_ids.length);
}

export function assertImportContent(state: ProgressState): void {
  const questions = state.activeSession?.questions ?? [];
  if (!questions.every(questionMatchesContent)
    || Object.keys(state.lessonDrafts).some(id => !lessonDraftMatchesContent(id, state))) {
    throw new Error('Saved questions do not match the current source-backed content. Progress was not changed.');
  }
}
