/**
 * The only module that touches the Firebase SDK. Everything here is loaded on demand, so the
 * learning app itself never downloads Firebase unless the learner signs in.
 */
import type { User } from "firebase/auth";
import type { ProgressState } from "../lib/progress";
import { mergeProgress } from "./merge";
import { parseState } from "../lib/progress";
import { firebaseConfig } from "./config";
import type { Account } from "./context";
import type { SyncBackend } from "./engine";

export const EMAIL_KEY = "unit24.emailForSignIn";
export const FINISH_PATH = "/auth/finish";

async function load() {
  if (!firebaseConfig) throw new Error("Firebase is not configured");
  const [appMod, authMod, fsMod] = await Promise.all([import("firebase/app"), import("firebase/auth"), import("firebase/firestore")]);
  const app = appMod.getApps()[0] ?? appMod.initializeApp(firebaseConfig);
  const auth = authMod.initializeAuth(app, {
    persistence: [authMod.indexedDBLocalPersistence, authMod.browserLocalPersistence],
    popupRedirectResolver: authMod.browserPopupRedirectResolver,
  });
  const db = fsMod.getFirestore(app);
  return { auth, authMod, db, fsMod };
}

let loading: ReturnType<typeof load> | null = null;
export function firebase() {
  loading ??= load().catch(error => { loading = null; throw error; });
  return loading;
}

const toAccount = (u: User | null): Account | null => (u ? { uid: u.uid, email: u.email, provider: u.providerData[0]?.providerId ?? null } : null);

export async function watchAccount(cb: (a: Account | null) => void): Promise<() => void> {
  const { auth, authMod } = await firebase();
  return authMod.onAuthStateChanged(auth, (u) => cb(toAccount(u)));
}

export async function signInWithGoogle(lang: string): Promise<void> {
  const { auth, authMod } = await firebase();
  auth.languageCode = lang;
  const provider = new authMod.GoogleAuthProvider();
  try {
    await authMod.signInWithPopup(auth, provider);
  } catch (e) {
    const code = (e as { code?: string }).code;
    // Popups are often blocked on phones and in installed apps; fall back to a full-page redirect.
    if (code === "auth/popup-blocked" || code === "auth/operation-not-supported-in-this-environment") {
      await authMod.signInWithRedirect(auth, provider);
      return;
    }
    throw e;
  }
}

export async function sendEmailLink(email: string, lang: string): Promise<void> {
  const { auth, authMod } = await firebase();
  auth.languageCode = lang;
  await authMod.sendSignInLinkToEmail(auth, email, { url: `${window.location.origin}${FINISH_PATH}`, handleCodeInApp: true });
  window.localStorage.setItem(EMAIL_KEY, email);
}

export async function isEmailLink(href: string): Promise<boolean> {
  const { auth, authMod } = await firebase();
  return authMod.isSignInWithEmailLink(auth, href);
}

export async function finishEmailLink(email: string, href: string): Promise<void> {
  const { auth, authMod } = await firebase();
  await authMod.signInWithEmailLink(auth, email, href);
  window.localStorage.removeItem(EMAIL_KEY);
}

export async function signOutAccount(): Promise<void> {
  const { auth, authMod } = await firebase();
  await authMod.signOut(auth);
}

/** Deletes the synced copy of the learner's progress. Progress on this device is kept. */
export async function deleteCloudProgress(uid: string): Promise<void> {
  const { db, fsMod } = await firebase();
  await fsMod.deleteDoc(fsMod.doc(db, "users", uid));
}

/** users/{uid} holds the progress as one JSON string, validated on the way in and out. */
export const firestoreBackend: SyncBackend = {
  async pull(uid) {
    const { db, fsMod } = await firebase();
    const snap = await fsMod.getDoc(fsMod.doc(db, "users", uid));
    const data = snap.data();
    if (!snap.exists()) return null;
    if (!data || typeof data.progress !== "string") throw new Error("Invalid cloud progress; remote copy preserved");
    return parseState(data.progress);
  },
  async push(uid, state: ProgressState) {
    const { db, fsMod } = await firebase();
    const ref = fsMod.doc(db, "users", uid);
    return fsMod.runTransaction(db, async transaction => {
      const snap = await transaction.get(ref);
      const data = snap.data();
      if (snap.exists() && typeof data?.progress !== "string") throw new Error("Invalid cloud progress; remote copy preserved");
      const merged = snap.exists() ? mergeProgress(state, parseState(data!.progress)) : parseState(JSON.stringify(state));
      transaction.set(ref, { schema: 1, progress: JSON.stringify(merged), updatedAt: fsMod.serverTimestamp() });
      return merged;
    });
  },
};
