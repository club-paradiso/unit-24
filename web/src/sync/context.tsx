import { createContext, useCallback, useContext, useEffect, useMemo, useState, useSyncExternalStore, type ReactNode } from "react";
import { useStore } from "../state";
import { isSyncConfigured } from "./config";
import { SyncEngine, type SyncBackend, type SyncSnapshot } from "./engine";

export const SIGNED_IN_KEY = "unit24.signedIn";

export interface Account {
  uid: string;
  email: string | null;
  provider: string | null;
}

/** What the UI needs from the auth provider; the Firebase module implements it. */
export interface AuthApi {
  watchAccount(cb: (a: Account | null) => void): Promise<() => void>;
  signInWithGoogle(lang: string): Promise<void>;
  sendEmailLink(email: string, lang: string): Promise<void>;
  signOutAccount(): Promise<void>;
  deleteCloudProgress(uid: string): Promise<void>;
  backend: SyncBackend;
}

async function firebaseApi(): Promise<AuthApi> {
  const m = await import("./firebase");
  return { ...m, backend: m.firestoreBackend };
}

interface SyncContextValue {
  configured: boolean;
  /** undefined while we do not yet know (SDK not loaded or auth not checked). */
  account: Account | null | undefined;
  snapshot: SyncSnapshot;
  connect: () => Promise<AuthApi>;
  syncNow: () => Promise<void>;
}

const SyncContext = createContext<SyncContextValue | null>(null);

const OFF: SyncSnapshot = { status: "off", lastSyncedAt: null, error: null };

function rememberedSignIn(): boolean {
  try {
    return window.localStorage.getItem(SIGNED_IN_KEY) === "1";
  } catch {
    return false;
  }
}

export function SyncProvider({
  children,
  api = firebaseApi,
  configured = isSyncConfigured(),
}: {
  children: ReactNode;
  api?: () => Promise<AuthApi>;
  configured?: boolean;
}) {
  const store = useStore();
  const [authApi, setAuthApi] = useState<AuthApi | null>(null);
  const [account, setAccount] = useState<Account | null | undefined>(undefined);
  const engine = useMemo(() => (authApi ? new SyncEngine(store, authApi.backend) : null), [authApi, store]);
  const snapshot = useSyncExternalStore(engine?.subscribe ?? (() => () => {}), engine?.getSnapshot ?? (() => OFF), () => OFF);

  const connect = useCallback(async () => {
    if (authApi) return authApi;
    const a = await api();
    setAuthApi(a);
    return a;
  }, [authApi, api]);

  // Only learners who signed in before load the SDK at startup.
  useEffect(() => {
    if (configured && rememberedSignIn()) void connect();
  }, [configured, connect]);

  useEffect(() => {
    if (!authApi) return;
    let stop: (() => void) | undefined;
    void authApi.watchAccount((a) => setAccount(a)).then((s) => (stop = s));
    return () => stop?.();
  }, [authApi]);

  useEffect(() => {
    if (!engine || account === undefined) return;
    try {
      if (account) window.localStorage.setItem(SIGNED_IN_KEY, "1");
      else window.localStorage.removeItem(SIGNED_IN_KEY);
    } catch {
      /* remembering is optional */
    }
    if (!account) {
      engine.stop();
      return;
    }
    void engine.start(account.uid);
    const onVisibility = () => {
      if (document.visibilityState === "hidden") void engine.flush();
      else void engine.syncNow();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      engine.stop();
    };
  }, [engine, account]);

  const value = useMemo<SyncContextValue>(
    () => ({ configured, account, snapshot, connect, syncNow: async () => engine?.syncNow() }),
    [configured, account, snapshot, connect, engine],
  );
  return <SyncContext.Provider value={value}>{children}</SyncContext.Provider>;
}

export function useSync(): SyncContextValue {
  const v = useContext(SyncContext);
  if (!v) throw new Error("useSync must be used inside <SyncProvider>");
  return v;
}
