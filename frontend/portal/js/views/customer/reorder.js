/**
 * reorder.js — Review cart and submit as a new order.
 *
 * Cart items come from:
 *   - catalog.js "Add to Order" buttons
 *   - orders.js "Reorder" (loads past invoice lines)
 */
import * as wcapi from '../../wcapi.js';
import { format } from '../../pjpv.js';

export async function renderReorder(el) {
  const cart = window._portalCart || [];

  if (!cart.length) {
    el.innerHTML = `
      <div class="card">
        <h3>Reorder</h3>
        <p style="color: var(--color-text-muted)">
          Your order is empty. Browse the <a href="#/catalog">Catalog</a> to add items,
          or click "Reorder" on a past order.
        </p>
      </div>
    `;
    return;
  }

  render(el, cart);
}

function render(el, cart) {
  const total = cart.reduce((sum, c) => sum + (c.price * c.quantity), 0);

  el.innerHTML = `
    <div class="card">
      <h3>Review Order</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>item</th><th>qty</th><th>price</th><th>ext</th><th></th></tr>
          </thead>
          <tbody>
            ${cart.map((c, i) => `
              <tr>
                <td>${esc(c.item_name)}</td>
                <td>
                  <input type="number" class="qty-input" data-idx="${i}"
                    value="${c.quantity}" min="1" style="width: 60px; padding: .2rem .4rem; border: 1px solid var(--color-border); border-radius: var(--radius);">
                </td>
                <td>${format(c.price, 'price.unit')}</td>
                <td>${format(c.price * c.quantity, 'price.extended')}</td>
                <td><button class="btn btn-sm btn-remove" data-idx="${i}">Remove</button></td>
              </tr>
            `).join('')}
          </tbody>
          <tfoot>
            <tr>
              <td colspan="3" style="text-align: right; font-weight: 600">Total</td>
              <td style="font-weight: 600">${format(total, 'totals.total')}</td>
              <td></td>
            </tr>
          </tfoot>
        </table>
      </div>
      <div style="margin-top: 1rem; display: flex; gap: .5rem; align-items: center">
        <button id="btn-submit-order" class="btn btn-primary">Submit Order</button>
        <button id="btn-clear-cart" class="btn">Clear</button>
        <span id="order-msg" style="font-size: .85rem"></span>
      </div>
    </div>
  `;

  // Quantity changes
  el.querySelectorAll('.qty-input').forEach(input => {
    input.addEventListener('change', () => {
      const idx = Number(input.dataset.idx);
      cart[idx].quantity = Math.max(1, Number(input.value) || 1);
      render(el, cart);
    });
  });

  // Remove buttons
  el.querySelectorAll('.btn-remove').forEach(btn => {
    btn.addEventListener('click', () => {
      cart.splice(Number(btn.dataset.idx), 1);
      window._portalCart = cart;
      render(el, cart);
    });
  });

  // Clear cart
  document.getElementById('btn-clear-cart').addEventListener('click', () => {
    window._portalCart = [];
    renderReorder(el);
  });

  // Submit order
  document.getElementById('btn-submit-order').addEventListener('click', async () => {
    const msg = document.getElementById('order-msg');
    const btn = document.getElementById('btn-submit-order');
    btn.disabled = true;
    msg.textContent = 'Submitting...';
    msg.style.color = 'var(--color-text-muted)';

    try {
      const user = wcapi.getUser();
      const lines = cart.map((c, i) => ({
        item_id: c.item_id,
        quantity: c.quantity,
        unit_price: c.price,
        sequence: i + 1,
      }));

      await wcapi.saveTransaction({
        model_name: 'order',
        header: {
          customer_id: user.id,
          status: 'planned',
        },
        lines,
      });

      window._portalCart = [];
      msg.textContent = 'Order submitted successfully!';
      msg.style.color = 'var(--color-success)';
      btn.textContent = 'Submitted';

    } catch (err) {
      msg.textContent = err.message;
      msg.style.color = 'var(--color-error)';
      btn.disabled = false;
    }
  });
}

function esc(val) {
  if (val == null) return '';
  return String(val).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
}
