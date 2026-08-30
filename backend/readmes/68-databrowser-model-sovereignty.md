# DataBrowser Model Sovereignty Fix

**Date:** 2026-08-16  
**Files changed:** `WindowManagerContext.tsx`, `useDataBrowser.ts`, `PrivateRoute.tsx`  
**Principle:** The toolbar is independent of the console that opened it. Users are in control.

---

## The Bug

In db.list, a user could change models via the select/search in the upper left. Records displayed correctly for the new model. But clicking the Layout select to change columns caused the model to jump back to `action`.

## Root Cause

Three interacting problems:

### 1. activateWindow re-navigated the active window

`MacWindowChrome` fires `activateWindow(path)` on every `onMouseDown` — every click anywhere inside the window. `activateWindow` unconditionally called `navigate(path)`, using the window's **creation-time path**.

- On `/:model` routes (e.g., `/action`): the user changed to `/contact` via `handleSelectModel`, but the window's `path` property stayed `/action`. Every subsequent click fired `navigate('/action')`, reverting the browser URL.
- On `/browser`: `handleSelectModel` set `?model=contact` in the URL. But `activateWindow('/browser')` navigated to `/browser` without query params, stripping `?model=contact`.

### 2. URL sync overrode user choices

The `useEffect` in `useDataBrowser` that syncs model from URL was designed for initial load and browser back/forward. But it ran on every render where `modelParam` differed from `selectedModel`. When `activateWindow` reverted the URL, this effect saw the old model in the URL and reset `selectedModel` back to it — or defaulted to the first alphabetical model (`action`).

### 3. Window key caused remounting

Windows were keyed by `w.path` in the render loop. If `updateWindowPath` changed the path, React saw a new key, unmounted the old DataBrowser, and mounted a fresh one — resetting all state including `selectedModel`.

## The Fix

### WindowManagerContext.tsx

**activateWindow guard:** Only navigate when switching TO a different window, not when clicking inside the already-active window.

```tsx
// Before: navigated on every mouseDown
if (navigateRef.current) {
  navigateRef.current(path);
}

// After: skip if already active
if (navigateRef.current && path !== activePath) {
  navigateRef.current(path);
}
```

**updateWindowPath:** New API lets components update a window's path after creation. When the DataBrowser changes models, it keeps the window path in sync so that future `activateWindow` calls use the current path, not the stale creation-time path.

### useDataBrowser.ts

**userSelectedModelRef:** Once the user explicitly picks a model via `handleSelectModel`, this ref is set. The URL sync effect checks it and returns early — the user's choice is authoritative. URL sync only applies on initial load (before the user has interacted).

**handleSelectModel:** After navigating, calls `wmCtx.updateWindowPath()` to keep the window path in sync with the new model.

**ROUTE_PATHS:** Added `'browser'` — was missing, which could cause `pathnameModel` to pick up `'browser'` as a model name.

### PrivateRoute.tsx

**Stable window key:** Changed from `key={w.path}` to `key={w.openedAt}`. `openedAt` is a monotonic counter set at window creation — it never changes, so path updates don't cause React to remount the component tree.

## Design Principle

The toolbar is sovereign. The user picks a model, that's the model. The URL is a convenience for initial load and bookmarking — it is not the source of truth during an active session. The window manager is infrastructure — it should not override user decisions.

This is the same principle as everywhere else in the ecosystem: the individual (user) is sovereign; the system (URL sync, window manager) is an agent with limited authority.
