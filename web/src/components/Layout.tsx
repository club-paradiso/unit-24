import { useEffect, useRef } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router";
import { StorageNotice } from "./StorageNotice";

const NAV = [
  { to: "/", label: "Home", end: true, icon: "M3 11 12 3l9 8v10h-6v-6H9v6H3z" },
  { to: "/chp", label: "Learn", end: true, icon: "M4 5h7a3 3 0 0 1 3 3v12a2 2 0 0 0-2-2H4zM20 5h-4a3 3 0 0 0-3 3" },
  { to: "/chp/practice", label: "Practice", end: false, icon: "M5 12l4 4L19 6" },
  { to: "/chp/reference", label: "Reference", end: false, icon: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm10 17-5-5" },
  { to: "/progress", label: "Progress", end: false, icon: "M4 20V10m6 10V4m6 16v-7m4 7H2" },
] as const;

function Icon({ d }: { d: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  );
}

export function Layout() {
  const location = useLocation();
  const mainRef = useRef<HTMLElement>(null);
  const first = useRef(true);

  useEffect(() => {
    // Move focus to the new page's heading so screen-reader and keyboard users land on the new content.
    if (first.current) {
      first.current = false;
      return;
    }
    const h1 = mainRef.current?.querySelector("h1");
    if (h1) {
      h1.setAttribute("tabindex", "-1");
      h1.focus({ preventScroll: false });
    }
    window.scrollTo?.(0, 0);
  }, [location.pathname]);

  return (
    <div className="shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="topbar">
        <div className="topbar-inner">
          <Link to="/" className="brand" aria-label="Unit-24 home">
            <span className="brand-mark" aria-hidden="true">
              U24
            </span>
            <span className="brand-name">Unit-24</span>
          </Link>
          <nav aria-label="Main" className="nav-top">
            {NAV.slice(1).map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end}>
                {n.label}
              </NavLink>
            ))}
            <NavLink to="/about">Sources</NavLink>
          </nav>
        </div>
      </header>
      <StorageNotice />
      <main id="main" ref={mainRef} className="main">
        <Outlet />
      </main>
      <footer className="footer">
        <p>
          Study aid only — not an operational reference. Content comes from one California Highway Patrol card; no entry has been verified by a human
          reviewer. <Link to="/about">How we source content</Link>
        </p>
      </footer>
      <nav aria-label="Main (mobile)" className="nav-bottom">
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end}>
            <Icon d={n.icon} />
            <span>{n.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
