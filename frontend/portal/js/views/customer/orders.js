/**
 * orders.js — Order/invoice history for the customer.
 *
 * List view: standard table of invoices.
 * Detail view: order header panel + invoiceline panel (standard db.column).
 */
import * as wcapi from '../../wcapi.js';
import { read, format, formatDate, statusBadge } from '../../pjpv.js';

export async function renderOrders(el) {
  const user = wcapi.getUser();

  el.innerHTML = `
    <div class="toolbar"><h3>Order History</h3></div>
    <div id="orders-list"></div>
    <div id="order-detail" style="display:none"></div>
  `;

  const listEl = document.getElementById('orders-list');
  const detailEl = document.getElementById('order-detail');

  try {
    const data = await wcapi.getRecords('invoice', { limit: 50, order_by: '-dt_created' });
    const invoices = data?.results || data || [];

    if (!invoices.length) {
      listEl.innerHTML = '<div class="card"><p style="color: var(--color-text-muted)">No orders on file.</p></div>';
      return;
    }

    listEl.innerHTML = `
      <div class="card">
        <div class="table-wrap">
          <table>
            <thead><tr>
              <th>date</th><th>order #</th><th>status</th>
              <th>total</th><th>balance</th><th></th>
            </tr></thead>
            <tbody>
              ${invoices.map(inv => `
                <tr>
                  <td>${formatDate(inv.dt_created)}</td>
                  <td>${esc(inv.ida || inv.id)}</td>
                  <td>${statusBadge(inv.status)}</td>
                  <td>${format(read(inv, 'totals.total'), 'totals.total')}</td>
                  <td>${format(read(inv, 'totals.balance'), 'totals.balance')}</td>
                  <td>
                    <button class="btn btn-sm btn-view-order" data-id="${inv.id}">View</button>
                    <button class="btn btn-sm btn-reorder" data-id="${inv.id}">Reorder</button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    listEl.querySelectorAll('.btn-view-order').forEach(btn => {
      btn.addEventListener('click', () => showOrderDetail(btn.dataset.id, detailEl, listEl));
    });
    listEl.querySelectorAll('.btn-reorder').forEach(btn => {
      btn.addEventListener('click', () => reorderFromInvoice(btn.dataset.id));
    });

  } catch (err) {
    listEl.innerHTML = `<div class="card"><p class="error-msg">${err.message}</p></div>`;
  }
}

async function showOrderDetail(invoiceId, detailEl, listEl) {
  try {
    const data = await wcapi.getRecord('invoice', invoiceId);
    const inv = data?.record || data;

    listEl.style.display = 'none';
    detailEl.style.display = '';

    detailEl.innerHTML = `
      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: .75rem">
          <h3>Order ${esc(inv.ida || inv.id)}</h3>
          <button class="btn btn-sm" id="btn-back-to-list">Back to List</button>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr>
              <th>ida</th><th>status</th><th>date</th><th>price_level</th>
              <th>subtotal</th><th>tax</th><th>total</th><th>balance</th>
            </tr></thead>
            <tbody><tr>
              <td>${esc(inv.ida)}</td>
              <td>${statusBadge(inv.status)}</td>
              <td>${formatDate(inv.dt_created)}</td>
              <td>${esc(inv.price_level || 'retail')}</td>
              <td>${format(read(inv, 'totals.subtotal'), 'totals.subtotal')}</td>
              <td>${format(read(inv, 'totals.tax'), 'totals.tax')}</td>
              <td>${format(read(inv, 'totals.total'), 'totals.total')}</td>
              <td>${format(read(inv, 'totals.balance'), 'totals.balance')}</td>
            </tr></tbody>
          </table>
        </div>
      </div>
      <div class="card" id="order-lines-panel"></div>
    `;

    document.getElementById('btn-back-to-list').addEventListener('click', () => {
      detailEl.style.display = 'none';
      listEl.style.display = '';
    });

    // Render lines panel
    renderLinesPanel(invoiceId);

  } catch (err) {
    detailEl.innerHTML = `<div class="card"><p class="error-msg">${err.message}</p></div>`;
    detailEl.style.display = '';
  }
}

async function renderLinesPanel(invoiceId) {
  const panel = document.getElementById('order-lines-panel');

  // Load lines from the parent invoice record (always available via _collect_lines)
  let lines = [];
  try {
    const data = await wcapi.getRecord('invoice', invoiceId);
    const inv = data?.record || data;
    lines = inv.lines || [];
  } catch { /* empty */ }

  panel.innerHTML = `
    <h3>Lines</h3>
    ${lines.length ? `
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>line</th><th>item</th><th>sku</th>
            <th>qty ordered</th><th>unit price</th><th>extended</th><th>status</th>
          </tr></thead>
          <tbody>
            ${lines.map(ln => {
              const item = ln.item || {};
              const qty = ln.quantity || {};
              const price = ln.price || {};
              const qtyVal = qty.ordered ?? qty.shipped ?? qty.active ?? qty.remaining ?? '';
              return `
                <tr>
                  <td>${ln.line_number || ''}</td>
                  <td>${esc(item.name || ln.name || '')}</td>
                  <td>${esc(item.sku || ln.sku || '')}</td>
                  <td>${qtyVal}</td>
                  <td>${format(price.unit, 'price.unit')}</td>
                  <td>${format(price.extended, 'price.extended')}</td>
                  <td>${statusBadge(ln.status || '')}</td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    ` : '<p style="color: var(--color-text-muted)">No line items.</p>'}
  `;
}

async function reorderFromInvoice(invoiceId) {
  try {
    let lines = [];
    try {
      const data = await wcapi.getRecords('invoiceline', { invoice_id: invoiceId, limit: 50 });
      lines = data?.results || data || [];
    } catch {
      const data = await wcapi.getRecord('invoice', invoiceId);
      lines = data?.related?.lines || data?.record?.lines || [];
    }

    window._portalCart = lines.map(ln => {
      const item = ln.item || {};
      const price = ln.price || {};
      const qty = ln.quantity || {};
      return {
        item_id: item.id || ln.item_fk_id || ln.item_id,
        item_name: item.name || ln.name || '',
        price: price.unit || 0,
        quantity: qty.ordered || qty.shipped || 1,
      };
    });

    window.location.hash = '#/reorder';
  } catch (err) {
    alert('Could not load order: ' + err.message);
  }
}

function esc(val) {
  if (val == null) return '';
  return String(val).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
}
