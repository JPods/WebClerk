/**
 * router.js — Simple hash-based router.
 *
 * Routes are registered as { path, label, handler, roles }.
 * The handler receives the content element and renders into it.
 */

const _routes = [];
let _contentEl = null;
let _navEl = null;
let _currentPath = null;

/**
 * Register a route.
 * @param {string} path - hash path, e.g. 'catalog', 'orders'
 * @param {string} label - nav label
 * @param {function} handler - async (contentEl) => void
 * @param {string[]} roles - which portal roles see this link
 */
export function addRoute(path, label, handler, roles = []) {
  _routes.push({ path, label, handler, roles });
}

/**
 * Initialize the router.
 * @param {HTMLElement} contentEl - where views render
 * @param {HTMLElement} navEl - where nav links go
 * @param {string[]} userRoles - current user's roles
 */
export function start(contentEl, navEl, userRoles) {
  _contentEl = contentEl;
  _navEl = navEl;
  buildNav(userRoles);

  window.addEventListener('hashchange', () => navigate());
  navigate(); // handle initial hash
}

/**
 * Build nav links based on user roles.
 */
function buildNav(userRoles) {
  _navEl.innerHTML = '';
  for (const route of _routes) {
    // Show route if roles is empty (shared) or user has a matching role
    if (route.roles.length > 0 && !route.roles.some(r => userRoles.includes(r))) {
      continue;
    }
    const a = document.createElement('a');
    a.href = `#/${route.path}`;
    a.textContent = route.label;
    a.dataset.path = route.path;
    _navEl.appendChild(a);
  }
}

/**
 * Navigate to the current hash route.
 */
async function navigate() {
  const hash = window.location.hash.replace(/^#\/?/, '') || defaultPath();
  const route = _routes.find(r => r.path === hash);

  if (!route) {
    _contentEl.innerHTML = '<div class="card"><h3>Page not found</h3></div>';
    return;
  }

  // Update active nav link
  _navEl.querySelectorAll('a').forEach(a => {
    a.classList.toggle('active', a.dataset.path === hash);
  });

  _currentPath = hash;
  _contentEl.innerHTML = '<p>Loading...</p>';

  try {
    await route.handler(_contentEl);
  } catch (err) {
    _contentEl.innerHTML = `<div class="card"><h3>Error</h3><p>${err.message}</p></div>`;
  }
}

function defaultPath() {
  const first = _routes[0];
  return first ? first.path : '';
}

/** Navigate programmatically */
export function goTo(path) {
  window.location.hash = `#/${path}`;
}

/** Get current path */
export function currentPath() { return _currentPath; }
