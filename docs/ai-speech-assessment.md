# UNIT-24 AI Speech Assessment Engine · gated beta

## Scope & integration

- Front-end audio stays local until learner explicitly records **and** agrees to transmit a recording for scoring.
- Recorded browser audio (WebM/MP4/etc., where supported by AudioContext) is decoded locally, resampled to 16 kHz mono PCM WAV, maximum ~21 seconds.
- Same-origin POST `/api/speech-assess` forwards an **allow-listed lesson reference** and WAV to Azure short-audio scripted pronunciation assessment, en-US, hundred-mark, phoneme granularity, comprehensive scores, miscue and prosody.
- Full-text accuracy, fluency, completeness, prosody (when available), total score, recognized phrase, words and phoneme results shown with explicit caveats. Unavailable values are not invented.
- No audio/result persistence in the app. UNIT-24 never logs or stores the body. Audio is processed transiently by Vercel and Azure under Azure's own processing policies.
- Existing TTS, browser recognition and standalone recording still work without Azure.

## Configuration (Vercel only, never in GitHub or the browser)

1. Create an Azure AI Speech resource with pronunciation assessment in a region supporting `en-US`. Confirm usage quota, billing limit and service terms.
2. Set Vercel **server-only** variables: `AZURE_SPEECH_REGION`, `AZURE_SPEECH_KEY`.
3. Set `UNIT24_SPEECH_ASSESSMENT_ENABLED=true` **only after** adding durable quota/rate controls at the ingress edge (e.g. WAF rules or authenticated per-user distributed limiter) and confirming allowed origins. Otherwise leave OFF (default).
4. Redeploy Preview to test and run with a voluntary sample recording; verify real outputs and data-protection notices. Then consider production separately.

**Security**: API keys are never sent to the device or exposed via status endpoint. POST requires matching Origin, allows only actual lesson phrases, checks WAV format (RIFF / signed PCM16 mono 16k / bounded duration and payload), and requires atomic distributed quota reservations. A missing/down quota service denies all paid calls. Strict feature flag defaults to OFF. No CORS.
**Privacy**: Sending the audio for AI processing is opt-in; browser transcription is separate and may use the browser's provider. Results are not saved locally or in cloud. Consult Microsoft data-processing terms before production onboarding.
**Validity**: Azure estimates phoneme accuracy relative to a reference recording/utterance, not correctness of police response or real-life safety. Two-word codes yield limited reliable fluency/prosody scores. Real on-air code conventions can vary and remain pending expert review.
**Limits**: REST short-audio max 30 sec for pronunciation assessment; implemented UI cap 20 sec. Browser decoders vary on Safari. If a format cannot be decoded, show fallback and keep the original local recording available.

## Acceptance
- [ ] GET /api/speech-assess returns JSON `enabled:false` when secret or flag absent.
- [ ] Disabled POST returns 503 with no external call.
- [ ] Validate same-origin restrictions, reference allowlist, WAV format, request size, per-instance limits.
- [ ] UI renders when disabled (no pretend scores), normal/slow listening, local record/replay unaffected.
- [ ] Azure mock response parser tests including missing prosody and phoneme results.
- [ ] Typecheck + Vitest + Vercel Preview build + full Playwright CI.
- [ ] iPad Safari: recording, WAV decode, explicit consent, real Azure responses, permission denial and interrupted connection.
- [ ] Confirm no API key is present in Vite JS bundles, PWA cache or any GitHub commit.

Docs: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-speech-to-text-short
