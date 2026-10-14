import type { FirebaseOptions } from "firebase/app";

/** Public web identifiers only. Nothing is enabled until every required value is present. */
export function readFirebaseConfig(env: Record<string, unknown>): FirebaseOptions | null {
  const fields = { apiKey: 'VITE_FIREBASE_API_KEY', authDomain: 'VITE_FIREBASE_AUTH_DOMAIN', projectId: 'VITE_FIREBASE_PROJECT_ID', appId: 'VITE_FIREBASE_APP_ID' };
  const config: Record<string, string> = {};
  for (const [field, name] of Object.entries(fields)) {
    const value = env[name];
    if (typeof value !== 'string' || !value.trim()) return null;
    config[field] = value.trim();
  }
  return config;
}
export const firebaseConfig: FirebaseOptions | null = readFirebaseConfig(import.meta.env);
export function isSyncConfigured(): boolean { return firebaseConfig !== null; }
