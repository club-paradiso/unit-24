# ADR 0012 — optional accounts, sync and anonymous statistics on Firebase (Spark plan)

**Status:** accepted (2026-10-13)

## Context

Learners will mostly use Unit-24 on phones and want to continue on another device. The owner
asked for a database that is free and stable, with sign-in by email link and Google, and
anonymous learning statistics. ADR 0010 keeps the app static and device-first.

Options considered in the Club Paradiso / lucanomics accounts:

* **Supabase.** The organisation is on the Free plan with its two active-project slots in use;
  a new project means pausing another service or paying. Free projects pause after a week
  without traffic, and the built-in mailer sends only a handful of emails an hour, so magic
  links would need separate SMTP.
* **Neon Postgres via Vercel.** Free and stable, but sign-in would need our own server
  functions, and email links need a mail provider with a verified sending domain — which
  `unit-24.vercel.app` cannot provide.
* **Firebase (Spark, no cost).** Firebase Auth sends sign-in links itself and supports Google
  sign-in without a custom domain; Firestore does not pause; both work from a static app with
  security rules, so no server code is needed.

## Decision

* Use Firebase Auth (Google, email link) and Cloud Firestore on the free Spark plan.
* Progress stays **device-first**: the local store remains the source of truth during use, and a
  sync engine pulls/merges/pushes one document per learner (`users/{uid}`, the progress as a
  validated JSON string). Signing in is optional; nothing is lost by not signing in.
* Anonymous statistics are per-session right/wrong counts per entry, written create-only to
  `session_stats` with a plain HTTPS request (no SDK, no identifiers), and can be switched off.
* The Firebase SDK is loaded lazily and kept out of the offline precache.
* `web/firestore.rules` is the security boundary and is tested on the emulator in CI.
* The web config lives in `web/src/sync/config.ts`. Its values are public identifiers, not
  secrets; until it is filled in the app behaves exactly as before.

## Consequences

* Spark-plan quotas apply (daily Firestore reads/writes, authentication email sends). At the
  expected scale they are far above need; if they are reached, sync and statistics pause while
  learning continues offline.
* The rules must be published to the Firebase project whenever `firestore.rules` changes
  (console or `firebase deploy --only firestore:rules`).
* Reading the statistics needs project-owner access (console, or a service-account script);
  they are deliberately unreadable from the app.
* Sign-in and sync have been verified against fakes and the Firestore emulator; they need a
  check on real phones once the project exists.
