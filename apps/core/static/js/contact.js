function renderContactDetails(contact) {
    document.getElementById('name_first').value = contact.name_first || '';
    document.getElementById('name_last').value = contact.name_last || '';
    document.getElementById('title').value = contact.title || '';
    document.getElementById('company').value = contact.company || '';
    document.getElementById('department').value = contact.department || '';
    document.getElementById('status').value = contact.status || 'active';
    document.getElementById('comment').value = contact.comment || '';
    document.getElementById('refs_tags').value = (contact.refs && contact.refs.tags) || '';
    document.getElementById('source').value = contact.source || '';
    document.getElementById('created_at').value = (contact.metadata && contact.metadata.history && contact.metadata.history.created && contact.metadata.history.created.dt) || '';
    document.getElementById('updated_at').value = (contact.metadata && contact.metadata.history && contact.metadata.history.modified && contact.metadata.history.modified.dt) || '';
}

function populateRelatedTables(related) {
    ['actions', 'emails', 'phones', 'addresses', 'domains'].forEach(table => {
        const tableDiv = document.getElementById(`${table}-table`);
        if (tableDiv) {
            if (related && Array.isArray(related[table]) && related[table].length > 0) {
                tableDiv.innerHTML = related[table].map(a => {
                    if (table === 'emails') {
                        return `<div>${a.email || '[no email]'}${a.name ? ' (' + a.name + ')' : ''}</div>`;
                    }
                    if (table === 'phones') {
                        return `<div>${a.number || '[no number]'}${a.name ? ' (' + a.name + ')' : ''}</div>`;
                    }
                    if (table === 'addresses') {
                        return `<div>${a.address1 || ''} ${a.address2 || ''} ${a.city || ''} ${a.state || ''} ${a.zip || ''}</div>`;
                    }
                    if (table === 'domains') {
                        return `<div>${a.domain || a.path || '[no domain]'}</div>`;
                    }
                    if (table === 'actions') {
                        return `<div>${a.action || '[no action]'}${a.status ? ' - ' + a.status : ''}</div>`;
                    }
                    return `<div>${JSON.stringify(a)}</div>`;
                }).join('');
            } else {
                tableDiv.innerHTML = `<div class="text-muted"><small>No ${table} found.</small></div>`;
            }
        }
    });
}