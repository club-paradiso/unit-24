# Learning experience foundation — first UX reliability PR

This PR is scoped to a source-backed first learning journey; it does **not** claim human source adjudication, operational code currency, real-voice verification, or completion of account/speech services.

## User path

1. New learner arrives at Home and sees the original first-lesson CTA before optional tools. The existing `unit24.progress` record and resume/next/due priorities are preserved.
2. Learner can visit Radio Lab from the secondary home section or CHP hub; the code/word reading and the English meaning now have individually labelled playback actions. For spelling-word items only the word playback is rendered to avoid duplicating the same audio.
3. Radio Lab presents existing item-backed status badges (automatic source comparison, human verification, currency) and direct source-record navigation. These values are not promoted by this PR.
4. The learner may choose a **one-item quiz** using the existing practice engine, which records an answer through the existing storage/SRS system. If another session is active, the CTA instead resumes it, so it is not overwritten.
5. Existing lessons, cards, source detail, recording, STT, optional Azure scoring, Firebase gate and PWA remain untouched.

## Regression checks

- Home's primary lesson CTA occurs before the optional speaking callout.
- `10-1` plays “ten one” for code reading and “Reception poor” for meaning. Listening alone must not create a progress record.
- One-item check generates a one-question practice session and persists the response through the normal system.
- An existing ten-question practice session is not overwritten from Radio Lab.
- At 320px, audio and practice controls are visible without horizontal overflow.
- Full typecheck, unit tests, Playwright browser matrix, content integrity and production/Preview smoke are required before merging.

## Explicit non-goals and follow-ups

- No person has adjudicated the research-only CHP content (currently 0 of 50); no current on-air use is asserted.
- TTS is device-generated, not agency-sourced audio. Spoken number reading remains a learner convention, not official procedure.
- A speaking-only interaction is **not** graded and does not automatically mark a card as mastered.
- Future UX work: expert content review, broader task-flow usability testing, more comprehensive learner journey, real-phone microphone tests and optional account activation.
