import { useEffect, useState } from "react";
import { useT } from "../i18n";

/** Offer an update without forcing a reload or touching learning data. */
export function AppUpdate() {
  const t = useT();
  const [waiting, setWaiting] = useState<ServiceWorker | null>(null);
  const [applying, setApplying] = useState(false);
  useEffect(() => {
    if (!import.meta.env.PROD || !("serviceWorker" in navigator)) return;
    let stopped = false;
    let registration: ServiceWorkerRegistration | undefined;
    let timer: ReturnType<typeof setInterval> | undefined;
    const offer = () => {
      if (!stopped) setWaiting(navigator.serviceWorker.controller && registration?.waiting?.state === "installed" ? registration.waiting : null);
    };
    const update = () => { if (navigator.onLine) void registration?.update().catch(() => {}); };
    const found = () => {
      const worker = registration?.installing;
      worker?.addEventListener("statechange", offer);
    };
    void navigator.serviceWorker.register("/sw.js", { updateViaCache: "none" }).then(r => {
      if (stopped) return;
      registration = r; offer(); r.waiting?.addEventListener("statechange", offer); found(); r.addEventListener("updatefound", found);
      timer = setInterval(update, 60 * 60 * 1000);
      update();
    }).catch(() => {});
    window.addEventListener("online", update);
    window.addEventListener("focus", update);
    return () => { stopped = true; if (timer) clearInterval(timer); registration?.removeEventListener("updatefound", found); window.removeEventListener("online", update); window.removeEventListener("focus", update); };
  }, []);
  if (!waiting) return null;
  const apply = () => {
    setApplying(true);
    navigator.serviceWorker.addEventListener("controllerchange", () => window.location.reload(), { once: true });
    waiting.postMessage({ type: "SKIP_WAITING" });
  };
  return <aside className="card stack-sm" role="status" aria-label={t("update.title")}>
    <strong>{t("update.title")}</strong><p>{t("update.message")}</p>
    <button type="button" className="btn btn-primary" disabled={applying} onClick={apply}>{t("update.apply")}</button>
  </aside>;
}
