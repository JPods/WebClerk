/**
 * pos.js — Purchase orders received by this vendor.
 */
import * as wcapi from '../../wcapi.js';
import { read, format, formatDate, statusBadge } from '../../pjpv.js';

export async function renderPOs(el) {
  const user = wcapi.getUser();

  try {
    // RBAC scopes results to this vendor's org
    const data = await wcapi.getRecords('purchase', {
      limit: 50,
      order_by: '-dt_created',
    });
    const pos = data?.results || data || [];

    if (!pos.length) {
      el.innerHTML = `
        <div class="card">
          <h3>Purchase Orders</h3>
          <p style="color: var(--color-text-muted)">No purchase orders on file.</p>
        </div>
      `;
      return;
    }

    el.innerHTML = `
      <div class="card">
        <h3>Purchase Orders</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>date</th>
                <th>PO #</th>
                <th>status</th>
                <th>total</th>
                <th>balance</th>
              </tr>
            </thead>
            <tbody>
              ${pos.map(po => `
                <tr>
                  <td>${formatDate(po.dt_created)}</td>
                  <td>${esc(po.ida || po.id)}</td>
                  <td>${statusBadge(po.status)}</td>
                  <td>${format(read(po, 'totals.total'), 'totals.total')}</td>
                  <td>${format(read(po, 'totals.balance'), 'totals.balance')}</td>
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
