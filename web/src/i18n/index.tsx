import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { en } from "./en";
import { ko, type Dict, type Key } from "./ko";

export type Lang = "ko" | "en";
export const LANG_KEY = "unit24.lang";
const DICTS: Record<Lang, Dict> = { ko, en };

type Params<K extends Key> = Dict[K] extends (p: infer P) => string ? [P] : [];
export type T = <K extends Key>(key: K, ...params: Params<K>) => string;

function readLang(): Lang {
  try {
    const v = window.localStorage.getItem(LANG_KEY);
    if (v === "ko" || v === "en") return v;
  } catch {
    /* storage unavailable: use the default */
  }
  return "ko";
}

export function translator(lang: Lang): T {
  const dict = DICTS[lang];
  return ((key: Key, ...params: unknown[]) => {
    const v = dict[key] as string | ((p: unknown) => string);
    return typeof v === "function" ? v(params[0]) : v;
  }) as T;
}

interface I18n {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: T;
}

const I18nContext = createContext<I18n | null>(null);

export function I18nProvider({ children, initial }: { children: ReactNode; initial?: Lang }) {
  const [lang, setLangState] = useState<Lang>(() => initial ?? readLang());
  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try {
      window.localStorage.setItem(LANG_KEY, l);
    } catch {
      /* not persisted; still applies for this visit */
    }
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  const value = useMemo(() => ({ lang, setLang, t: translator(lang) }), [lang, setLang]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18n {
  const v = useContext(I18nContext);
  if (!v) throw new Error("useI18n must be used inside <I18nProvider>");
  return v;
}

export function useT(): T {
  return useI18n().t;
}
