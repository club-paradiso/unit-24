import { assertFails, assertSucceeds, initializeTestEnvironment, type RulesTestEnvironment } from "@firebase/rules-unit-testing";
import { readFileSync } from "node:fs";
import { deleteDoc, doc, getDoc, serverTimestamp, setDoc, addDoc, collection } from "firebase/firestore";
import { afterAll, beforeAll, beforeEach, describe, it } from "vitest";

let env: RulesTestEnvironment;

beforeAll(async () => {
  env = await initializeTestEnvironment({
    projectId: "demo-unit24",
    firestore: { rules: readFileSync(new URL("../firestore.rules", import.meta.url), "utf8") },
  });
});
afterAll(async () => env.cleanup());
beforeEach(async () => env.clearFirestore());

const progress = () => ({ schema: 1, progress: JSON.stringify({ version: 1 }), updatedAt: serverTimestamp() });
const stats = (over: Record<string, unknown> = {}) => ({
  schema: 1,
  contentVersion: "abc",
  mode: "mixed",
  n: 2,
  results: { fct_1: { c: 1, w: 1 } },
  at: serverTimestamp(),
  ...over,
});

describe("users/{uid}", () => {
  it("lets a learner write, read and delete only their own progress", async () => {
    const alice = env.authenticatedContext("alice").firestore();
    await assertSucceeds(setDoc(doc(alice, "users/alice"), progress()));
    await assertSucceeds(getDoc(doc(alice, "users/alice")));
    await assertSucceeds(deleteDoc(doc(alice, "users/alice")));
  });

  it("keeps everyone else out", async () => {
    await env.withSecurityRulesDisabled((ctx) => setDoc(doc(ctx.firestore(), "users/alice"), { schema: 1, progress: "{}" }));
    const bob = env.authenticatedContext("bob").firestore();
    const anon = env.unauthenticatedContext().firestore();
    await assertFails(getDoc(doc(bob, "users/alice")));
    await assertFails(setDoc(doc(bob, "users/alice"), progress()));
    await assertFails(getDoc(doc(anon, "users/alice")));
    await assertFails(setDoc(doc(anon, "users/alice"), progress()));
  });

  it("rejects unexpected fields, client clocks and oversized documents", async () => {
    const alice = env.authenticatedContext("alice").firestore();
    await assertFails(setDoc(doc(alice, "users/alice"), { ...progress(), admin: true }));
    await assertFails(setDoc(doc(alice, "users/alice"), { ...progress(), updatedAt: new Date() }));
    await assertFails(setDoc(doc(alice, "users/alice"), { ...progress(), progress: "x".repeat(400001) }));
    await assertFails(setDoc(doc(alice, "users/alice"), { ...progress(), progress: { a: 1 } }));
  });
});

describe("session_stats", () => {
  it("accepts anonymous, well-formed statistics", async () => {
    const anon = env.unauthenticatedContext().firestore();
    await assertSucceeds(addDoc(collection(anon, "session_stats"), stats()));
    await assertSucceeds(addDoc(collection(anon, "session_stats"), stats({ mode: "lesson" })));
  });

  it("rejects identifiers, bad shapes and any reading or changing", async () => {
    const anon = env.unauthenticatedContext().firestore();
    await assertFails(addDoc(collection(anon, "session_stats"), stats({ uid: "alice" })));
    await assertFails(addDoc(collection(anon, "session_stats"), stats({ mode: "hack" })));
    await assertFails(addDoc(collection(anon, "session_stats"), stats({ n: 500 })));
    await assertFails(addDoc(collection(anon, "session_stats"), stats({ results: {} })));
    await assertFails(addDoc(collection(anon, "session_stats"), stats({ at: new Date() })));
    await env.withSecurityRulesDisabled((ctx) => setDoc(doc(ctx.firestore(), "session_stats/x"), stats({ at: new Date() })));
    await assertFails(getDoc(doc(anon, "session_stats/x")));
    const alice = env.authenticatedContext("alice").firestore();
    await assertFails(getDoc(doc(alice, "session_stats/x")));
    await assertFails(setDoc(doc(alice, "session_stats/x"), stats()));
    await assertFails(deleteDoc(doc(alice, "session_stats/x")));
  });

  it("denies everything else", async () => {
    const alice = env.authenticatedContext("alice").firestore();
    await assertFails(setDoc(doc(alice, "anything/else"), { a: 1 }));
  });
});

describe("the app's anonymous statistics request", () => {
  // The exact body src/sync/stats.ts sends, posted to the emulator's REST endpoint without credentials.
  const commit = async (body: unknown) => {
    const host = process.env.FIRESTORE_EMULATOR_HOST ?? "127.0.0.1:8080";
    return fetch(`http://${host}/v1/projects/demo-unit24/databases/(default)/documents:commit`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
  };

  it("is accepted by the rules", async () => {
    const { commitBody, sessionStats } = await import("../src/sync/stats");
    const s = sessionStats("codes", [{ fct_a: true }, { fct_a: false, fct_b: true }])!;
    const res = await commit(commitBody("demo-unit24", "doc1", "v1", s));
    if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  });

  it("cannot overwrite an existing document", async () => {
    const { commitBody, sessionStats } = await import("../src/sync/stats");
    const s = sessionStats("codes", [{ fct_a: true }])!;
    await commit(commitBody("demo-unit24", "doc2", "v1", s));
    const again = await commit(commitBody("demo-unit24", "doc2", "v1", s));
    if (again.ok) throw new Error("second write to the same id succeeded");
  });
});
