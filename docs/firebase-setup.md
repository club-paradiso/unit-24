# Firebase setup (accounts and sync)

About five minutes in the Firebase console, then one small commit. Until this is done the app
works device-only and says so in Settings.

## 1. Create the project (owner, in the browser)

1. https://console.firebase.google.com → **Add project** → name `unit-24`. Google Analytics is not needed.
2. **Build → Authentication → Get started → Sign-in method**
   * **Google** → Enable → choose a support email → Save.
   * **Email/Password** → Enable, and also enable **Email link (passwordless sign-in)** → Save.
3. **Authentication → Settings → Authorized domains** → Add `unit-24.vercel.app`
   (`localhost` is there by default).
4. **Build → Firestore Database → Create database** → location `asia-northeast3 (Seoul)` →
   start in **production mode**.
5. **Firestore → Rules** → replace the contents with `web/firestore.rules` from this repository
   → **Publish**.
6. **Project settings (gear) → General → Your apps → Web (`</>`)** → register `unit-24-web`
   (no Hosting). Copy the `firebaseConfig` object it shows.

The values in `firebaseConfig` (apiKey, authDomain, projectId, …) identify the web app; they are
not secrets. Access is enforced by Authentication and the rules.

## 2. Plug it in (repository)

Put the object into `web/src/sync/config.ts`:

```ts
export const firebaseConfig: FirebaseOptions | null = {
  apiKey: "…",
  authDomain: "unit-24-xxxx.firebaseapp.com",
  projectId: "unit-24-xxxx",
  storageBucket: "…",
  messagingSenderId: "…",
  appId: "…",
};
```

Open a pull request. CI runs the unit, end-to-end and rules tests; after merge Vercel deploys and
Settings → "계정과 동기화" offers Google and email-link sign-in.

## 3. Check on a phone

* Sign in with Google on the phone, answer a few questions, then sign in on a laptop: the same
  progress appears.
* Request an email link, open it on the same phone: you land on `/auth/finish`, signed in.
* Settings → "계정에 저장된 학습 기록 삭제" removes the account copy.

## Notes

* **Rules changes** must be published again (step 5), or with the CLI:
  `cd web && npx firebase-tools deploy --only firestore:rules --project <projectId>`.
* **Statistics** are in Firestore → `session_stats` (console only; the app cannot read them).
* **Quotas** on the free plan are generous for this app; if a limit is hit, sync and statistics
  pause and learning continues offline.
* **Popups on phones.** Google sign-in uses a popup and falls back to a full-page redirect when the
  popup is blocked.
