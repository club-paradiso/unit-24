import { createContext, useContext, useEffect, useMemo, useSyncExternalStore, type ReactNode } from "react";
import { ProgressStore, type ProgressState } from "./lib/progress";

const StoreContext = createContext<ProgressStore | null>(null);

export function ProgressProvider({ store, children }: { store?: ProgressStore; children: ReactNode }) {
  const value = useMemo(() => store ?? new ProgressStore(), [store]);
  useEffect(() => {
    const changed = (event: StorageEvent) => { if (event.key === "unit24.progress") value.refresh(); };
    window.addEventListener("storage", changed);
    return () => window.removeEventListener("storage", changed);
  }, [value]);
  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore(): ProgressStore {
  const store = useContext(StoreContext);
  if (!store) throw new Error("useStore must be used inside <ProgressProvider>");
  return store;
}

export function useProgress(): ProgressState {
  const store = useStore();
  return useSyncExternalStore(store.subscribe, store.getState, store.getState);
}

/** The storage notice is not part of the persisted state, so it is subscribed to separately. */
export function useStorageNotice() {
  const store = useStore();
  const getNotice = () => store.notice;
  return useSyncExternalStore(store.subscribe, getNotice, getNotice);
}

export function useTitle(title: string) {
  useEffect(() => {
    document.title = title ? `${title} · Unit-24` : "Unit-24";
  }, [title]);
}
