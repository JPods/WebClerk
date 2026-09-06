/**
 * app.js — Main portal application.
 *
 * Login → detect role → register role-appropriate routes → start router.
 */
import * as wcapi from './wcapi.js';
import * as pjpv from './pjpv.js';
import * as router from './router.js';

// Shared views
import { renderAccount } from './views/shared/account.js';
import { renderComms } from './views/shared/comms.js';

// Customer views
import { renderCatalog } from './views/customer/catalog.js';
import { renderOrders } from './views/customer/orders.js';
import { renderReorder } from './views/customer/reorder.js';

// Vendor views
import { renderPOs } from './views/vendor/pos.js';
import { renderItems } from './views/vendor/items.js';
import { renderShipments } from './views/vendor/shipments.js';

// DOM refs
const loginView = document.getElementById('login-view');
const contentArea = document.getElementById('content-area');
const navEl = document.getElementById('portal-nav');
const greetingEl = document.getElementById('user-greeting');
const logoutBtn = document.getElementById('btn-logout');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');

// Detect API base URL (same origin)
const BASE_URL = '';

wcapi.init(BASE_URL);

// --- Login flow ---
loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  loginError.textContent = '';

  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;

  try {
    const user = await wcapi.login(email, password);
    await onAuthenticated(user);
  } catch (err) {
    loginError.textContent = err.message || 'Login failed';
  }
});

logoutBtn.addEventListener('click', async () => {
  await wcapi.logout();
  showLogin();
});

// --- Post-login setup ---
async function onAuthenticated(user) {
  // Load PJPV catalog for formatting
  pjpv.loadCatalog(BASE_URL, wcapi.getToken());

  const roles = user.roles || [];
  const name = [user.name_first, user.name_last].filter(Boolean).join(' ') || user.email;

  greetingEl.textContent = name;
  logoutBtn.style.display = '';

  // Determine portal type from roles
  const isCustomer = roles.includes('user_customer') || user.role === 'customer';
  const isVendor = roles.includes('user_vendor') || user.role === 'vendor';

  registerRoutes(isCustomer, isVendor);

  // Show content
  loginView.style.display = 'none';
  contentArea.style.display = '';

  router.start(contentArea, navEl, roles);
}

function registerRoutes(isCustomer, isVendor) {
  // Customer routes
  if (isCustomer || (!isCustomer && !isVendor)) {
    // Default to customer view if role is ambiguous
    router.addRoute('catalog', 'Catalog', renderCatalog, []);
    router.addRoute('orders', 'Orders', renderOrders, []);
    router.addRoute('reorder', 'Reorder', renderReorder, []);
  }

  // Vendor routes
  if (isVendor) {
    router.addRoute('pos', 'Purchase Orders', renderPOs, []);
    router.addRoute('items', 'Our Items', renderItems, []);
    router.addRoute('shipments', 'Shipments', renderShipments, []);
  }

  // Shared routes (always visible)
  router.addRoute('account', 'Account', renderAccount, []);
  router.addRoute('comms', 'Messages', renderComms, []);
}

function showLogin() {
  loginView.style.display = '';
  contentArea.style.display = 'none';
  navEl.innerHTML = '';
  greetingEl.textContent = '';
  logoutBtn.style.display = 'none';
}
