/**
 * items.js — Items this vendor supplies in the catalog.
 */
import * as wcapi from '../../wcapi.js';
import { read, format } from '../../pjpv.js';

export async function renderItems(el) {
  const user = wcapi.getUser();

  try {
    // RBAC scopes results to this vendor's items
    const data = await wcapi.getRecords('item', {
      limit: 100,
      is_active: true,
    });
    const items = data?.results || data || [];

    if (!items.length) {
      el.innerHTML = `
        <div class="card">
          <h3>Our Items</h3>
          <p style="color: var(--color-text-muted)">No items linked to your account.</p>
        </div>
      `;
      return;
    }

    el.innerHTML = `
      <div class="card">
        <h3>Our Items in Catalog</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>name</th>
                <th>sku</th>
                <th>retail</th>
                <th>on hand</th>
                <th>on PO</th>
              </tr>
            </thead>
            <tbody>
              ${items.map(item => `
                <tr>
                  <td>${esc(item.name)}</td>
                  <td>${esc(item.sku || '')}</td>
                  <td>${format(read(item, 'price.retail'), 'price.retail')}</td>
                  <td>${read(item, 'quantity.on_hand', '\u2014')}</td>
                  <td>${read(item, 'quantity.on_po', '\u2014')}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    el.innerHTML = `<div class="card"><p class="error-msg">${err.message}</p></div>`;
  }
}

function esc(val) {
  if (val == null) return '';
  return String(val).replace(/&/g, '&amp;').replace(/</g, '&lt;');
}
