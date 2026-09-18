/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useEffect } from "react";
import { useLocation } from "react-router";

export function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo({
      top: 0,
      left: 0,
      behavior: "smooth",
    });
  }, [pathname]);

  return null;
}
