import type { FirebaseOptions } from "firebase/app";

/**
 * Public identifiers of the Firebase web app (Project settings → Your apps → Web). They are not
 * secrets: access is controlled by Firebase Authentication and firestore.rules. `null` until the
 * Firebase project exists; the app then works exactly as before, saving on the device only.
 */
export const firebaseConfig: FirebaseOptions | null = null;

export function isSyncConfigured(): boolean {
  return firebaseConfig !== null;
}
