# UNIT-24 AI Speech Assessment Engine · gated beta

## Scope & integration

- Front-end audio stays local until learner explicitly records **and** agrees to transmit a recording for scoring.
- Recorded browser audio (WebM/MP4/etc., where supported by AudioContext) is decoded locally, resampled to 16 kHz mono PCM WAV, maximum ~21 seconds.
- Same-origin POST `/api/speech-assess` forwards an **allow-listed lesson reference** and WAV to Azure short-audio scripted pronunciation assessment, en-US, hundred-mark, phoneme granularity, comprehensive scores, miscue and prosody.
- Full-text accuracy, fluency, completeness, prosody (when available), total score, recognized phrase, words and phoneme results shown with explicit caveats. Unavailable values are not invented.
- No audio/result persistence in the app. UNIT-24 never logs or stores the body. Audio is processed transiently by Vercel and Azure under Azure's own processing policies.
- Existing TTS, browser recognition and standalone recording still work without Azure.

## Configuration (Vercel only, never in GitHub or the browser)

The endpoint reports `enabled: true` only when **every** step below is in place.
Setting the Azure key and the feature flag alone is not enough: without the
distributed limiter the gate stays closed by design, and the status endpoint
will keep returning `enabled: false`.

1. Create an Azure AI Speech resource (F0 is enough to start) in a region supporting pronunciation assessment for `en-US`. Confirm usage quota, billing limit and service terms, and set an Azure billing alert.
2. Set Vercel **server-only** variables: `AZURE_SPEECH_REGION` (the resource region, e.g. `eastus`), `AZURE_SPEECH_KEY` (a resource key).
3. Create a free Upstash Redis database and set its REST credentials as Vercel server-only variables: `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`. The URL must be the bare REST endpoint (`https://<name>.upstash.io`, no credentials, path, query or trailing content) or the limiter check rejects it.
4. Set `UNIT24_SPEECH_IP_HASH_SECRET` to a random value of at least 32 characters (e.g. the output of `openssl rand -hex 32`). It only HMAC-hashes caller IPs for quota buckets; it is never sent anywhere.
5. Set `UNIT24_SPEECH_ASSESSMENT_ENABLED=true` **only after** steps 2–4 are in place and allowed origins are confirmed. Add durable quota/rate controls at the ingress edge (e.g. WAF rules) as a second layer. Otherwise leave OFF (default).
6. Redeploy, then verify activation in this order: `GET /api/speech-assess` returns `{"enabled": true, ...}`; a voluntary sample recording returns real Azure scores in a Preview deployment; only then enable Production separately.

**Security**: API keys are never sent to the device or exposed via status endpoint. POST requires matching Origin, allows only actual lesson phrases, checks WAV format (RIFF / signed PCM16 mono 16k / bounded duration and payload), and requires atomic distributed quota reservations. A missing/down quota service denies all paid calls. Strict feature flag defaults to OFF. No CORS.
**Privacy**: Sending the audio for AI processing is opt-in; browser transcription is separate and may use the browser's provider. Results are not saved locally or in cloud. Consult Microsoft data-processing terms before production onboarding.
**Validity**: Azure estimates phoneme accuracy relative to a reference recording/utterance, not correctness of police response or real-life safety. Two-word codes yield limited reliable fluency/prosody scores. Real on-air code conventions can vary and remain pending expert review.
**Limits**: REST short-audio max 30 sec for pronunciation assessment; implemented UI cap 20 sec. Browser decoders vary on Safari. If a format cannot be decoded, show fallback and keep the original local recording available.

## Acceptance
- [x] GET /api/speech-assess returns JSON `enabled:false` when secret or flag absent. (Unit tests + production probe, 2026-11-04: `{"enabled":false,"provider":"azure-pronunciation-assessment","maxSeconds":20}`.)
- [x] Disabled POST returns 503 with no external call. (Unit tests + production probe, 2026-11-04: 503 `ASSESSMENT_UNAVAILABLE`.)
- [x] Validate same-origin restrictions, reference allowlist, WAV format, request size, per-instance limits. (Proxy unit tests; allowlist coverage of every teachable phrase is guarded by `src/lib/assessmentAllowlist.test.ts`.)
- [x] UI renders when disabled (no pretend scores), normal/slow listening, local record/replay unaffected. (`AssessmentPanel`/`SpeechCoach` component tests; Playwright journey suites.)
- [x] Azure mock response parser tests including missing prosody and phoneme results.
- [x] Typecheck + Vitest + production build pass locally and in CI.
- [ ] Vercel Preview with real secrets: GET flips to `enabled:true` and a sample recording returns real Azure scores.
- [ ] iPad Safari: recording, WAV decode, explicit consent, real Azure responses, permission denial and interrupted connection.
- [ ] Confirm no API key is present in Vite JS bundles, PWA cache or any GitHub commit. (Re-check on the first enabled Preview build.)

## Status

PR #16 (this engine) merged to `main` on 2026-10-23 (merge commit `66e4453`);
it is not a draft. Production serves the app with assessment disabled
(`enabled: false`, verified 2026-11-04) until the Configuration steps above
are completed by the project owner.

Docs: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-speech-to-text-short
