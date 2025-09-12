(function(){
  const $ = (sel, el=document) => el.querySelector(sel);
  const $$ = (sel, el=document) => Array.from(el.querySelectorAll(sel));

  const state = {
    models: [],
    model: null, // singular code
    fields: [],
    selectedFields: { left: [], mid: [], right: [] },
    records: [],
    record: null,
    metaByModel: {},
  };

  // Load/save prefs in localStorage, keyed by user+model (server can adopt Setting later)
  const userKey = 'wb-default'; // can switch to request user id via template context
  function prefsKey(model){ return `wb:prefs:${userKey}:${model || state.model || 'none'}`; }
  function loadPrefs(model){
    try {
      const raw = localStorage.getItem(prefsKey(model));
      if(!raw) return null;
      return JSON.parse(raw);
    } catch(_) { return null; }
  }
  function savePrefs(){
    if(!state.model) return;
    const prefs = {
      selectedFields: state.selectedFields,
    };
    localStorage.setItem(prefsKey(), JSON.stringify(prefs));
    setStatus('Preferences saved');
  }

  function setStatus(msg, kind){
    const el = $('#wb-status');
    if(!el) return;
    el.textContent = msg || '';
    el.style.color = kind==='error' ? '#ef4444' : kind==='warn' ? '#f59e0b' : '#9ca3af';
    if(msg) setTimeout(()=>{ el.textContent = ''; }, 2000);
  }

  function api(path, opts){
    return fetch(path, Object.assign({ credentials: 'same-origin' }, opts || {})).then(r=>{
      if(!r.ok) throw new Error(`HTTP ${r.status}`);
      const ct = r.headers.get('content-type') || '';
      return ct.includes('application/json') ? r.json() : r.text();
    });
  }

  async function loadModels(){
    const data = await api(WCAPI.listModels);
    state.models = data?.data?.model_names || [];
    renderModelList();
  }

  async function loadModelDetail(model){
    const url = `${WCAPI.modelDetail}?model_name=${encodeURIComponent(model)}`;
    const data = await api(url);
    state.metaByModel[model] = data?.data?.model || null;
  }

  async function loadFieldsForModel(model){
    await loadModelDetail(model);
    const meta = state.metaByModel[model];
    const fieldEntries = meta?.fields ? Object.keys(meta.fields) : [];
    state.fields = fieldEntries;
    // initialize selected fields from prefs or defaults
    const prefs = loadPrefs(model);
    if(prefs?.selectedFields){
      state.selectedFields = prefs.selectedFields;
    } else {
      const defaultFields = fieldEntries.slice(0, Math.min(12, fieldEntries.length));
      state.selectedFields = { left: defaultFields.slice(0,4), mid: defaultFields.slice(4,8), right: defaultFields.slice(8,12) };
    }
    renderFieldPicker();
    syncFieldTextareas();
  }

  function renderModelList(){
    const ul = $('#wb-model-list');
    ul.innerHTML = '';
    const filter = ($('#wb-model-filter').value || '').toLowerCase();
    state.models
      .filter(m => !filter || m.toLowerCase().includes(filter))
      .forEach(m => {
        const li = document.createElement('li');
        li.textContent = m;
        if(state.model === m) li.classList.add('active');
        li.addEventListener('click', async ()=>{
          state.model = m;
          state.records = [];
          state.record = null;
          await loadFieldsForModel(m);
          await searchRecords();
          renderModelList();
          renderRecords();
          renderEditor();
        });
        ul.appendChild(li);
      });
  }

  function renderFieldPicker(){
    const all = $('#wb-all-fields');
    const sel = $('#wb-selected-fields');
    all.innerHTML = '';
    sel.innerHTML = '';
    const used = new Set([...state.selectedFields.left, ...state.selectedFields.mid, ...state.selectedFields.right]);
    state.fields.forEach(name => {
      const li = document.createElement('li');
      li.textContent = name;
      if(used.has(name)) li.style.opacity = 0.5;
      li.addEventListener('click', ()=> li.classList.toggle('active'));
      all.appendChild(li);
    });
    const showSelected = (arr) => {
      arr.forEach(name => {
        const li = document.createElement('li');
        li.textContent = name;
        li.addEventListener('click', ()=> li.classList.toggle('active'));
        sel.appendChild(li);
      });
    };
    showSelected(state.selectedFields.left);
    showSelected(state.selectedFields.mid);
    showSelected(state.selectedFields.right);
  }

  function syncFieldTextareas(){
    $('#wb-left-fields-json').value = JSON.stringify(state.selectedFields.left, null, 2);
    $('#wb-mid-fields-json').value = JSON.stringify(state.selectedFields.mid, null, 2);
    $('#wb-right-fields-json').value = JSON.stringify(state.selectedFields.right, null, 2);
  }

  function readFieldTextareas(){
    try { state.selectedFields.left = JSON.parse($('#wb-left-fields-json').value || '[]'); } catch(_){ setStatus('Invalid JSON (left)', 'error'); }
    try { state.selectedFields.mid = JSON.parse($('#wb-mid-fields-json').value || '[]'); } catch(_){ setStatus('Invalid JSON (middle)', 'error'); }
    try { state.selectedFields.right = JSON.parse($('#wb-right-fields-json').value || '[]'); } catch(_){ setStatus('Invalid JSON (right)', 'error'); }
  }

  function getProjectionFor(section){
    const arr = state.selectedFields[section] || [];
    return Array.isArray(arr) && arr.length ? arr : null;
  }

  async function searchRecords(){
    if(!state.model) return;
    const q = ($('#wb-record-filter').value || '').trim();
    const url = new URL(WCAPI.query, window.location.origin);
    url.searchParams.set('model_name', state.model);
    if(q){
      // Optimistically map `term` to a single safe filter if possible (e.g., name_first)
      const parts = q.split(':');
      if(parts.length === 2 && WCAPI.safeFilterFields.has(parts[0])){
        url.searchParams.set(parts[0], parts[1]);
      } else {
        // best effort: if it looks like an id, try id match via wcapi/get; else ignore
      }
    }
    const fields = getProjectionFor('mid');
    if(fields){ url.searchParams.set('fields', JSON.stringify(fields)); }
    const res = await api(url.toString());
    const env = res?.data || res; // api_response envelope
    state.records = env.results || [];
    renderRecords();
  }

  function renderRecords(){
    const ul = $('#wb-record-list');
    ul.innerHTML = '';
    state.records.forEach(rec => {
      const li = document.createElement('li');
      const title = rec.name || rec.title || rec.email || rec.code || `id ${rec.id}`;
      li.innerHTML = `<div>${title}</div><div class="code">#${rec.id}</div>`;
      if(state.record && state.record.id === rec.id) li.classList.add('active');
      li.addEventListener('click', async ()=>{
        state.record = await fetchRecord(rec.id);
        renderRecords();
        renderEditor();
      });
      ul.appendChild(li);
    });
  }

  async function fetchRecord(id){
    const url = new URL(WCAPI.get, window.location.origin);
    url.searchParams.set('model_name', state.model);
    url.searchParams.set('id', id);
    const res = await api(url.toString());
    const env = res?.data || res;
    return (env.results && env.results[0]) || null;
  }

  function renderEditor(){
    const form = $('#wb-editor-form');
    form.innerHTML = '';
    if(!state.record){
      form.innerHTML = '<div class="wb-subhead">Select a record to edit</div>';
      return;
    }
    const fields = getProjectionFor('right') || Object.keys(state.record);
    fields.forEach(name => {
      const value = state.record[name];
      const wrap = document.createElement('div');
      wrap.className = 'wb-field';
      const label = document.createElement('label');
      label.textContent = name;
      wrap.appendChild(label);
      let input;
      if(typeof value === 'boolean'){
        input = document.createElement('select');
        ['false','true'].forEach(v=>{
          const opt = document.createElement('option');
          opt.value = v; opt.textContent = v;
          if(String(value) === v) opt.selected = true;
          input.appendChild(opt);
        })
      } else if(typeof value === 'number'){
        input = document.createElement('input');
        input.type = 'number';
        input.value = String(value);
      } else if(typeof value === 'string'){
        input = document.createElement('input');
        input.type = 'text';
        input.value = value;
      } else {
        input = document.createElement('textarea');
        input.value = JSON.stringify(value, null, 2);
      }
      input.dataset.field = name;
      wrap.appendChild(input);
      form.appendChild(wrap);
    });
  }

  async function saveRecord(){
    if(!state.model || !state.record) return;
    const form = $('#wb-editor-form');
    const payload = { model_name: state.model, id: state.record.id };
    $$('.wb-field [data-field]', form).forEach(input => {
      const name = input.dataset.field;
      if(input.tagName === 'TEXTAREA'){
        try { payload[name] = JSON.parse(input.value); } catch(_) { payload[name] = input.value; }
      } else if(input.tagName === 'SELECT'){
        payload[name] = input.value === 'true';
      } else if(input.type === 'number'){
        const v = input.value.trim();
        payload[name] = v ? Number(v) : null;
      } else {
        payload[name] = input.value;
      }
    });
    try {
      const res = await api(WCAPI.save, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const env = res?.data || res;
      // optimistic refresh
      state.record = env.record || state.record;
      setStatus('Saved', 'ok');
    } catch(err){
      console.error(err);
      setStatus('Save failed', 'error');
    }
  }

  function addSelected(){
    const candidates = $$('#wb-all-fields li.active').map(li=>li.textContent);
    const dest = state.selectedFields.right; // default to editor panel for quick add
    candidates.forEach(name => {
      if(!dest.includes(name)) dest.push(name);
    });
    renderFieldPicker();
    syncFieldTextareas();
  }

  function removeSelected(){
    const selected = new Set($$('#wb-selected-fields li.active').map(li=>li.textContent));
    ['left','mid','right'].forEach(sec => {
      state.selectedFields[sec] = (state.selectedFields[sec] || []).filter(n => !selected.has(n));
    });
    renderFieldPicker();
    syncFieldTextareas();
  }

  // Wire events
  document.addEventListener('DOMContentLoaded', async ()=>{
    $('#wb-refresh').addEventListener('click', async ()=>{
      if(state.model){ await searchRecords(); }
    });
    $('#wb-save-prefs').addEventListener('click', savePrefs);
    $('#wb-model-filter').addEventListener('input', renderModelList);
    $('#wb-record-search').addEventListener('click', searchRecords);
    $('#wb-add-fields').addEventListener('click', addSelected);
    $('#wb-remove-fields').addEventListener('click', removeSelected);
    $('#wb-save-record').addEventListener('click', saveRecord);
    $('#wb-left-fields-json').addEventListener('change', ()=>{ readFieldTextareas(); renderFieldPicker(); });
    $('#wb-mid-fields-json').addEventListener('change', ()=>{ readFieldTextareas(); renderFieldPicker(); });
    $('#wb-right-fields-json').addEventListener('change', ()=>{ readFieldTextareas(); renderFieldPicker(); renderEditor(); });

    await loadModels();
  });
})();
