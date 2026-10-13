import raw from "./chp.json";
import type { CodeSystem, ContentBundle, LearningItem, Lesson } from "./types";

export type * from "./types";

/** Throws if the generated bundle does not have the shape the app relies on. */
export function validateBundle(data: unknown): ContentBundle {
  const fail = (msg: string): never => {
    throw new Error(`Invalid content bundle: ${msg}`);
  };
  if (typeof data !== "object" || data === null) fail("not an object");
  const b = data as Partial<ContentBundle>;
  if (b.schema_version !== 2) fail(`unsupported schema_version ${String(b.schema_version)}`);
  if (!Array.isArray(b.items) || b.items.length === 0) fail("no items");
  if (!Array.isArray(b.lessons)) fail("no lessons");
  if (!b.source?.sha256 || !b.source.url) fail("source identity missing");
  const ids = new Set<string>();
  for (const item of b.items!) {
    if (!item.id || !item.term || !item.answer) fail(`item missing id/term/answer: ${JSON.stringify(item)}`);
    if (ids.has(item.id)) fail(`duplicate item ${item.id}`);
    if (!item.excerpt || !item.locator || item.source_id !== b.source!.source_id) fail(`item ${item.id} is not traceable`);
    ids.add(item.id);
  }
  for (const lesson of b.lessons!) {
    for (const id of lesson.item_ids) if (!ids.has(id)) fail(`lesson ${lesson.id} references unknown item ${id}`);
  }
  return b as ContentBundle;
}

export const content: ContentBundle = validateBundle(raw);

const byId = new Map(content.items.map((i) => [i.id, i]));

export function getItem(id: string): LearningItem | undefined {
  return byId.get(id);
}

export function getLesson(id: string): Lesson | undefined {
  return content.lessons.find((l) => l.id === id);
}

export function lessonItems(lesson: Lesson): LearningItem[] {
  return lesson.item_ids.map((id) => byId.get(id)).filter((i): i is LearningItem => i !== undefined);
}

export const SYSTEM_LABEL: Record<CodeSystem, string> = {
  TEN_CODE: "10-code",
  ELEVEN_CODE: "11-code",
  CHP_CARD_ALPHABET: "Card alphabet",
};
