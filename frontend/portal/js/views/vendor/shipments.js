/**
 * shipments.js — Shipment/fulfillment status for vendor POs.
 */
import * as wcapi from '../../wcapi.js';
import { read, format, formatDate, statusBadge } from '../../pjpv.js';

export async function renderShipments(el) {
  const user = wcapi.getUser();

  try {
    // Shipments are typically invoices where this vendor is the vendor_id
    // and status indicates fulfillment state
    // RBAC scopes results to this vendor's shipments
    const data = await wcapi.getRecords('invoice', {
      limit: 50,
      order_by: '-dt_created',
    });
    const shipments = data?.results || data || [];

    if (!shipments.length) {
      el.innerHTML = `
        <div class="card">
          <h3>Shipments</h3>
          <p style="color: var(--color-text-muted)">No shipment records.</p>
        </div>
      `;
      return;
    }

    el.innerHTML = `
      <div class="card">
        <h3>Shipments</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>date</th>
                <th>invoice #</th>
                <th>status</th>
                <th>ship via</th>
                <th>total</th>
              </tr>
            </thead>
            <tbody>
              ${shipments.map(s => `
                <tr>
                  <td>${formatDate(s.dt_created)}</td>
                  <td>${esc(s.ida || s.id)}</td>
                  <td>${statusBadge(s.status)}</td>
                  <td>${esc(s.ship_via || '')}</td>
                  <td>${format(read(s, 'totals.total'), 'totals.total')}</td>
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
