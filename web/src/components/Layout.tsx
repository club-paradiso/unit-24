import { useEffect, useRef } from "react";
import { Link, NavLink, Outlet, matchPath, useLocation } from "react-router";
import { content } from "../content";
import { useT } from "../i18n";
import { Icon, type IconName } from "./Icon";
import { StorageNotice } from "./StorageNotice";

const NAV: { to: string; key: "nav.home" | "nav.learn" | "nav.practice" | "nav.reference" | "nav.progress"; end: boolean; icon: IconName }[] = [
  { to: "/", key: "nav.home", end: true, icon: "home" },
  { to: "/chp", key: "nav.learn", end: true, icon: "learn" },
  { to: "/chp/practice", key: "nav.practice", end: true, icon: "practice" },
  { to: "/chp/reference", key: "nav.reference", end: false, icon: "search" },
  { to: "/progress", key: "nav.progress", end: false, icon: "progress" },
];

/** Screens where the learner works through a task: no tab bar, a close button instead. */
const FOCUS: { pattern: string; exitTo: string }[] = [
  { pattern: "/chp/practice/session", exitTo: "/chp/practice" },
  { pattern: "/chp/flashcards", exitTo: "/chp" },
  { pattern: "/chp/lessons/:lessonId", exitTo: "/chp" },
];

export function Layout() {
  const t = useT();
  const location = useLocation();
  const mainRef = useRef<HTMLElement>(null);
  const first = useRef(true);
  const focus = FOCUS.find((f) => matchPath(f.pattern, location.pathname));

  useEffect(() => {
    // Move focus to the new page's heading so screen-reader and keyboard users land on the new content.
    if (first.current) {
      first.current = false;
      return;
    }
    const h1 = mainRef.current?.querySelector("h1");
    if (h1) {
      h1.setAttribute("tabindex", "-1");
      h1.focus({ preventScroll: true });
    }
    window.scrollTo?.(0, 0);
  }, [location.pathname]);

  return (
    <div className={`shell ${focus ? "is-focus" : ""}`}>
      <a className="skip-link" href="#main">
        {t("a11y.skip")}
      </a>
      <header className="topbar">
        <div className="topbar-inner">
          {focus ? (
            <Link to={focus.exitTo} className="icon-btn" aria-label={t("common.exit")}>
              <Icon name="close" size={22} />
            </Link>
          ) : (
            <Link to="/" className="brand" aria-label={t("a11y.brandHome")}>
              <span className="brand-mark" aria-hidden="true">
                U24
              </span>
              <span className="brand-name">Unit-24</span>
            </Link>
          )}
          <nav aria-label={t("a11y.mainNav")} className="nav-top">
            {NAV.slice(1).map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end}>
                {t(n.key)}
              </NavLink>
            ))}
            <NavLink to="/about">{t("nav.sources")}</NavLink>
          </nav>
          <Link to="/settings" className="icon-btn" aria-label={t("nav.settings")}>
            <Icon name="settings" size={22} />
          </Link>
        </div>
      </header>
      <StorageNotice />
      <main id="main" ref={mainRef} className="main">
        <Outlet />
      </main>
      {!focus && (
        <footer className="footer">
          <p>
            {t("footer.disclaimer", { verified: content.counts.human_verified, total: content.counts.teachable })}{" "}
            <Link to="/about">{t("footer.howWeSource")}</Link>
          </p>
        </footer>
      )}
      {!focus && (
        <nav aria-label={t("a11y.mobileNav")} className="nav-bottom">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end}>
              <Icon name={n.icon} />
              <span>{t(n.key)}</span>
            </NavLink>
          ))}
        </nav>
      )}
    </div>
  );
}
