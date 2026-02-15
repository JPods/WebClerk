import { createContext, useContext } from "react";

/**
 * Provides the full path (including query string) of the enclosing floating
 * window to descendant components.  MacWindowChrome wraps its children in
 * this context so that components rendered inside a floating window can
 * reliably parse their own query params without depending on the browser
 * URL / useSearchParams() — whose timing may lag behind the window render.
 *
 * Usage in a component:
 *   const windowPath = useWindowPath();          // e.g. "/core/contact/detail/?parent_model=customer&parent_id=42"
 *   const params = windowPath ? new URL(windowPath, "http://x").searchParams : null;
 */

const WindowPathContext = createContext<string | null>(null);

export const WindowPathProvider = WindowPathContext.Provider;

export const useWindowPath = () => useContext(WindowPathContext);
