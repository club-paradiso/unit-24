/** A short vibration where the device supports it and the learner has not asked for reduced motion. */
export function haptic(kind: "success" | "error" | "tap"): void {
  try {
    if (typeof navigator === "undefined" || typeof navigator.vibrate !== "function") return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    if (window.localStorage.getItem("unit24.haptics") === "off") return;
    navigator.vibrate(kind === "error" ? [40, 60, 40] : kind === "success" ? 15 : 8);
  } catch {
    /* vibration is a nicety; never let it break answering */
  }
}
