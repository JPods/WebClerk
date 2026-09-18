/**
 * catalog.js — Browse items at the customer's price level.
 */
import * as wcapi from '../../wcapi.js';
import { read, format } from '../../pjpv.js';

export async function renderCatalog(el) {
  const user = wcapi.getUser();
  // Determine price level from user prefs or default to retail
  const priceLevel = read(user, 'prefs.price_level') || read(user, 'config.price_level') || 'retail';

  el.innerHTML = `
    <div class="toolbar">
      <h3>Catalog</h3>
      <input type="search" id="catalog-search" placeholder="Search items...">
    </div>
    <div id="catalog-results" class="catalog-grid">
      <p>Loading...</p>
    </div>
  `;

  const resultsEl = document.getElementById('catalog-results');
  const searchInput = document.getElementById('catalog-search');

  let debounce = null;
  searchInput.addEventListener('input', () => {
    clearTimeout(debounce);
    debounce = setTimeout(() => loadItems(resultsEl, searchInput.value, priceLevel), 300);
  });

  await loadItems(resultsEl, '', priceLevel);
}

async function loadItems(container, query, priceLevel) {
  try {
    const params = { limit: 50, is_active: true };
    if (query) params.search = query;

    const data = await wcapi.getRecords('item', params);
    const items = data?.results || data || [];

    if (!items.length) {
      container.innerHTML = '<p style="color: var(--color-text-muted)">No items found.</p>';
      return;
    }

    container.innerHTML = items.map(item => {
      const price = resolvePrice(item, priceLevel);
      const desc = read(item, 'catalog.web.short') || read(item, 'description') || '';

      return `
        <div class="catalog-item" data-item-id="${item.id}">
          <div class="item-name">${esc(item.name)}</div>
          <div class="item-sku">${esc(item.sku || '')}</div>
          ${desc ? `<div class="item-desc">${esc(truncate(desc, 100))}</div>` : ''}
          <div class="item-price">${format(price, 'price.' + priceLevel)}</div>
          <div style="margin-top: .5rem">
            <button class="btn btn-sm btn-add-to-order" data-id="${item.id}" data-name="${esc(item.name)}" data-price="${price || 0}">
              Add to Order
            </button>
          </div>
        </div>
      `;
    }).join('');

    // Add-to-order buttons store selection for reorder view
    container.querySelectorAll('.btn-add-to-order').forEach(btn => {
      btn.addEventListener('click', () => {
        addToCart(btn.dataset.id, btn.dataset.name, Number(btn.dataset.price));
        btn.textContent = 'Added';
        btn.disabled = true;
      });
    });

  } catch (err) {
    container.innerHTML = `<p class="error-msg">${err.message}</p>`;
  }
}

/**
 * Resolve the price at the customer's level.
 * Cascade: requested level → retail → base → msrp
 */
function resolvePrice(item, level) {
  return read(item, `price.${level}`)
    || read(item, 'price.retail')
    || read(item, 'price.base')
    || read(item, 'price.msrp');
}

// --- Simple in-memory cart (shared with reorder view) ---
// Cart is stored on window so reorder.js can read it
function addToCart(itemId, itemName, price) {
  if (!window._portalCart) window._portalCart = [];
  const existing = window._portalCart.find(c => c.item_id === itemId);
  if (existing) {
    existing.quantity += 1;
  } else {
    window._portalCart.push({ item_id: itemId, item_name: itemName, price, quantity: 1 });
  }
}

function esc(val) {
  if (val == null) return '';
  return String(val).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
}

function truncate(str, len) {
  return str.length > len ? str.slice(0, len) + '...' : str;
}
