# Firebase setup (accounts and sync)

Accounts remain disabled until configuration and real integration verification are complete.
The local learning application works without an account and says so in Settings.

## 1. Create the project (owner, in the browser)

1. https://console.firebase.google.com → **Add project** → name `unit-24`. Google Analytics is not needed.
2. **Build → Authentication → Get started → Sign-in method**
   * **Google** → Enable → choose a support email → Save.
   * **Email/Password** → Enable, and also enable **Email link (passwordless sign-in)** → Save.
3. **Authentication → Settings → Authorized domains** → Add `unit-24.vercel.app`
   (add `localhost` explicitly if needed; inspect the actual project settings).
4. **Build → Firestore Database → Create database** → location `asia-northeast3 (Seoul)` →
   start in **production mode**.
5. **Firestore → Rules** → replace the contents with `web/firestore.rules` from this repository
   → **Publish**.
6. **Project settings (gear) → General → Your apps → Web (`</>`)** → register `unit-24-web`
   (no Hosting). Copy the `firebaseConfig` object it shows.

The values in `firebaseConfig` (apiKey, authDomain, projectId, …) identify the web app; they are
not secrets. Access is enforced by Authentication and the rules.

## 2. Configure a verified Preview environment

The application reads these public build-time environment variables:

```
VITE_FIREBASE_API_KEY
VITE_FIREBASE_AUTH_DOMAIN
VITE_FIREBASE_PROJECT_ID
VITE_FIREBASE_APP_ID
```

All four must be present or accounts stay disabled. Do not edit `config.ts` with credentials.
Use a dedicated test project for Preview; do not expose production learner data to arbitrary
preview builds. Add each authorized test domain explicitly. A configuration change requires a
new build. These public identifiers are bundled in JavaScript; never put service-account or
Admin SDK credentials in VITE variables.

Before enabling Production, verify real providers, callbacks, published rules, two-device
conflicts, offline reconnection, account switching and deletion. Passing mocks/emulators is
insufficient. See `docs/recovery/REMAINING_BLOCKERS.md`; account isolation and redirect flows
remain release blockers. This recovery does not claim any Firebase console change was made.

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
