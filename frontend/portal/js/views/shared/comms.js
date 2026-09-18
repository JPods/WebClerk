/**
 * comms.js — Communication records (Touch model).
 */
import * as wcapi from '../../wcapi.js';
import { formatDate } from '../../pjpv.js';

export async function renderComms(el) {
  const user = wcapi.getUser();

  let records = [];
  try {
    const data = await wcapi.getRecords('touch', {
      contact_id: user.id,
      limit: 50,
      order_by: '-dt_created',
    });
    records = data?.results || data || [];
  } catch {
    // Touch model may not exist or user has no records
  }

  if (!records.length) {
    el.innerHTML = `
      <div class="card">
        <h3>Messages</h3>
        <p style="color: var(--color-text-muted)">No communication records.</p>
      </div>
    `;
    return;
  }

  el.innerHTML = `
    <div class="card">
      <h3>Messages</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>date</th>
              <th>type</th>
              <th>subject</th>
              <th>summary</th>
            </tr>
          </thead>
          <tbody>
            ${records.map(r => `
              <tr>
                <td>${formatDate(r.dt_created)}</td>
                <td>${esc(r.touch_type || r.kind || '')}</td>
                <td>${esc(r.subject || '')}</td>
                <td>${esc(truncate(r.body || r.summary || r.notes || '', 120))}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function esc(val) {
  if (val == null) return '';
  return String(val).replace(/&/g, '&amp;').replace(/</g, '&lt;');
}

function truncate(str, len) {
  return str.length > len ? str.slice(0, len) + '...' : str;
}
