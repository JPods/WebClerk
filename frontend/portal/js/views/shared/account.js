/**
 * account.js — View/edit contact profile + communication panels.
 *
 * Communications (phone, email, address, domain) are separate models
 * linked by contact_id. Each panel is a standard db.column view.
 */
import * as wcapi from '../../wcapi.js';

export async function renderAccount(el) {
  const me = await wcapi.getMe();
  const user = me?.user || me;
  let contact = user;

  try {
    const full = await wcapi.getRecord('contact', user.id);
    contact = full?.record || full || user;
  } catch { /* fall back to /me/ data */ }

  el.innerHTML = `
    <div class="card">
      <h3>Account Information</h3>
      <form id="account-form" class="form-grid">
        <div class="form-field"><label>company</label><input name="company" value="${esc(contact.company)}"></div>
        <div class="form-field"><label>department</label><input name="department" value="${esc(contact.department)}"></div>
        <div class="form-field"><label>title</label><input name="title" value="${esc(contact.title)}"></div>
        <div class="form-field"><label>name_first</label><input name="name_first" value="${esc(contact.name_first)}"></div>
        <div class="form-field"><label>name_last</label><input name="name_last" value="${esc(contact.name_last)}"></div>
        <div class="form-field"><label>attention</label><input name="attention" value="${esc(contact.attention)}" disabled></div>
      </form>
      <div style="margin-top: 1rem">
        <button id="account-save" class="btn btn-primary">Save Changes</button>
        <span id="account-msg" style="margin-left: 1rem; font-size: .85rem"></span>
      </div>
    </div>

    <div class="card" id="panel-email"></div>
    <div class="card" id="panel-phone"></div>
    <div class="card" id="panel-address"></div>
    <div class="card" id="panel-domain"></div>
  `;

  // Save contact fields
  document.getElementById('account-save').addEventListener('click', async () => {
    const form = document.getElementById('account-form');
    const fields = {};
    for (const input of form.querySelectorAll('input:not([disabled])')) {
      fields[input.name] = input.value.trim();
    }
    fields.id = contact.id;
    const msg = document.getElementById('account-msg');
    try {
      await wcapi.saveRecord('contact', fields);
      msg.textContent = 'Saved';
      msg.style.color = 'var(--color-success)';
    } catch (err) {
      msg.textContent = err.message;
      msg.style.color = 'var(--color-error)';
    }
  });

  // Render communication panels
  renderCommPanel('panel-email', 'Email', 'email', contact.id, [
    { name: 'email', label: 'email', type: 'email' },
    { name: 'name', label: 'name' },
    { name: 'type', label: 'type' },
  ]);
  renderCommPanel('panel-phone', 'Phone', 'phone', contact.id, [
    { name: 'number', label: 'number', type: 'tel' },
    { name: 'name', label: 'name' },
  ]);
  renderCommPanel('panel-address', 'Address', 'address', contact.id, [
    { name: 'address1', label: 'address1' },
    { name: 'city', label: 'city' },
    { name: 'state', label: 'state' },
    { name: 'zip', label: 'zip' },
  ]);
  renderCommPanel('panel-domain', 'Domain', 'domain', contact.id, [
    { name: 'domain', label: 'domain' },
    { name: 'name', label: 'name' },
  ]);
}

/**
 * Render a communication panel: list existing records + add new.
 */
async function renderCommPanel(elId, title, modelName, contactId, columns) {
  const container = document.getElementById(elId);

  let records = [];
  try {
    const data = await wcapi.getRecords(modelName, { contact_id: contactId, limit: 20 });
    records = data?.results || data || [];
  } catch { /* model may not be accessible */ }

  const colHeaders = columns.map(c => `<th>${c.label}</th>`).join('');

  container.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: .75rem">
      <h3 style="margin: 0">${title}</h3>
      <button class="btn btn-sm btn-add-comm">+ Add</button>
    </div>
    ${records.length ? `
      <div class="table-wrap">
        <table>
          <thead><tr>${colHeaders}<th></th></tr></thead>
          <tbody>
            ${records.map(r => `
              <tr data-id="${r.id}">
                ${columns.map(c => `<td>${esc(r[c.name])}</td>`).join('')}
                <td><button class="btn btn-sm btn-edit-comm" data-id="${r.id}">Edit</button></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    ` : `<p style="color: var(--color-text-muted); font-size: .85rem">None on file.</p>`}
    <div id="${elId}-form" style="display: none; margin-top: .75rem">
      <div class="form-grid">
        ${columns.map(c => `
          <div class="form-field">
            <label>${c.label}</label>
            <input name="${c.name}" type="${c.type || 'text'}">
          </div>
        `).join('')}
      </div>
      <input type="hidden" name="record-id" value="">
      <div style="margin-top: .5rem; display: flex; gap: .5rem; align-items: center">
        <button class="btn btn-primary btn-save-comm">Save</button>
        <button class="btn btn-cancel-comm">Cancel</button>
        <span class="comm-msg" style="font-size: .85rem"></span>
      </div>
    </div>
  `;

  const formEl = document.getElementById(`${elId}-form`);

  // Add button
  container.querySelector('.btn-add-comm').addEventListener('click', () => {
    formEl.querySelector('[name="record-id"]').value = '';
    for (const c of columns) formEl.querySelector(`[name="${c.name}"]`).value = '';
    formEl.style.display = '';
  });

  // Cancel button
  formEl.querySelector('.btn-cancel-comm').addEventListener('click', () => {
    formEl.style.display = 'none';
  });

  // Edit buttons
  container.querySelectorAll('.btn-edit-comm').forEach(btn => {
    btn.addEventListener('click', () => {
      const rec = records.find(r => String(r.id) === btn.dataset.id);
      if (!rec) return;
      formEl.querySelector('[name="record-id"]').value = rec.id;
      for (const c of columns) {
        formEl.querySelector(`[name="${c.name}"]`).value = rec[c.name] || '';
      }
      formEl.style.display = '';
    });
  });

  // Save button
  formEl.querySelector('.btn-save-comm').addEventListener('click', async () => {
    const msg = formEl.querySelector('.comm-msg');
    const fields = { contact_id: contactId };
    const recId = formEl.querySelector('[name="record-id"]').value;
    if (recId) fields.id = Number(recId);
    for (const c of columns) {
      fields[c.name] = formEl.querySelector(`[name="${c.name}"]`).value.trim();
    }
    try {
      await wcapi.saveRecord(modelName, fields);
      msg.textContent = 'Saved';
      msg.style.color = 'var(--color-success)';
      // Re-render panel to show updated data
      setTimeout(() => renderCommPanel(elId, title, modelName, contactId, columns), 500);
    } catch (err) {
      msg.textContent = err.message;
      msg.style.color = 'var(--color-error)';
    }
  });
}

function esc(val) {
  if (val == null) return '';
  return String(val).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
}
