/**
 * Anonymous study statistics: per finished session, how many times each entry was answered right
 * and wrong. No user id, no device id, nothing else. Sent with a plain HTTPS request to Firestore
 * (no SDK download for learners who never sign in), and only when the learner has not turned it off.
 */
import type { FirebaseOptions } from "firebase/app";

export const STATS_KEY = "unit24.stats";
export const MAX_ITEMS = 30;

export type StatsMode = "mixed" | "codes" | "alphabet" | "mistakes" | "due" | "lesson";

export interface SessionStats {
  mode: StatsMode;
  n: number;
  results: Record<string, { c: number; w: number }>;
}

export function statsEnabled(): boolean {
  try {
    return window.localStorage.getItem(STATS_KEY) !== "off";
  } catch {
    return false;
  }
}

export function setStatsEnabled(on: boolean): void {
  try {
    window.localStorage.setItem(STATS_KEY, on ? "on" : "off");
  } catch {
    /* preference not saved */
  }
}

/** Totals per entry from a session's per-answer results. */
export function sessionStats(mode: StatsMode, answers: Record<string, boolean>[]): SessionStats | null {
  const results: Record<string, { c: number; w: number }> = {};
  for (const a of answers) {
    for (const [id, ok] of Object.entries(a)) {
      const r = (results[id] ??= { c: 0, w: 0 });
      if (ok) r.c += 1;
      else r.w += 1;
    }
  }
  const ids = Object.keys(results);
  if (ids.length === 0 || ids.length > MAX_ITEMS) return null;
  return { mode, n: answers.length, results };
}

const int = (n: number) => ({ integerValue: String(n) });

/** The Firestore REST "commit" body that creates one session_stats document with a server timestamp. */
export function commitBody(projectId: string, docId: string, contentVersion: string, s: SessionStats) {
  const fields = Object.fromEntries(Object.entries(s.results).map(([id, r]) => [id, { mapValue: { fields: { c: int(r.c), w: int(r.w) } } }]));
  return {
    writes: [
      {
        update: {
          name: `projects/${projectId}/databases/(default)/documents/session_stats/${docId}`,
          fields: {
            schema: int(1),
            contentVersion: { stringValue: contentVersion },
            mode: { stringValue: s.mode },
            n: int(Math.min(s.n, MAX_ITEMS)),
            results: { mapValue: { fields } },
          },
        },
        updateTransforms: [{ fieldPath: "at", setToServerValue: "REQUEST_TIME" }],
        currentDocument: { exists: false },
      },
    ],
  };
}

export async function sendStats(
  config: FirebaseOptions | null,
  contentVersion: string,
  stats: SessionStats | null,
  fetchImpl: typeof fetch = fetch,
): Promise<boolean> {
  if (!config?.projectId || !config.apiKey || !stats || !statsEnabled()) return false;
  const docId = crypto.randomUUID().replace(/-/g, "");
  const url = `https://firestore.googleapis.com/v1/projects/${config.projectId}/databases/(default)/documents:commit?key=${encodeURIComponent(config.apiKey)}`;
  try {
    const res = await fetchImpl(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(commitBody(config.projectId, docId, contentVersion, stats)),
      keepalive: true,
    });
    return res.ok;
  } catch {
    return false; // statistics are best-effort and never interrupt learning
  }
}
