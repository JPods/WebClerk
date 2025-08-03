// WebClerk 3.0 Universal API JavaScript

// CSRF Token for Django
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
           document.querySelector('[name=csrfmiddlewaretoken]')?.getAttribute('value') ||
           document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='))?.split('=')[1] || '';
}

// Universal API Helper Functions
class UniversalAPI {
    static async query(tableName, filters = {}) {
        try {
            const response = await fetch('/wcapi/query/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({
                    table_name: tableName,
                    filters: filters
                })
            });
            return await response.json();
        } catch (error) {
            console.error('Universal API Query Error:', error);
            return { error: error.message };
        }
    }
    
    static async get(tableName, id) {
        try {
            const response = await fetch(`/wcapi/${tableName}/${id}/`);
            return await response.json();
        } catch (error) {
            console.error('Universal API Get Error:', error);
            return { error: error.message };
        }
    }
    
    static async create(tableName, data) {
        try {
            const response = await fetch(`/wcapi/${tableName}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify(data)
            });
            return await response.json();
        } catch (error) {
            console.error('Universal API Create Error:', error);
            return { error: error.message };
        }
    }
    
    static async update(tableName, id, data) {
        try {
            const response = await fetch(`/wcapi/${tableName}/${id}/`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify(data)
            });
            return await response.json();
        } catch (error) {
            console.error('Universal API Update Error:', error);
            return { error: error.message };
        }
    }
    
    static async delete(tableName, id) {
        try {
            const response = await fetch(`/wcapi/${tableName}/${id}/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                }
            });
            return response.ok ? { success: true } : { error: 'Delete failed' };
        } catch (error) {
            console.error('Universal API Delete Error:', error);
            return { error: error.message };
        }
    }
}

// Contact Management Functions
function sendTestEmail() {
    const button = event.target;
    const originalText = button.innerHTML;
    button.classList.add('loading');
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
    
    // Get contact ID from the page
    const contactId = getContactIdFromPage();
    
    // Simulate email sending (replace with actual Universal API call)
    setTimeout(() => {
        button.classList.remove('loading');
        button.innerHTML = originalText;
        
        // Show success message
        showAlert('Test email sent successfully!', 'success');
    }, 2000);
}

function exportContact() {
    const contactId = getContactIdFromPage();
    
    if (contactId) {
        // Use Universal API to export contact data
        UniversalAPI.get('contacts', contactId)
            .then(data => {
                if (data.error) {
                    showAlert('Error exporting contact: ' + data.error, 'danger');
                } else {
                    // Create downloadable JSON file
                    const blob = new Blob([JSON.stringify(data, null, 2)], {
                        type: 'application/json'
                    });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `contact_${contactId}.json`;
                    a.click();
                    URL.revokeObjectURL(url);
                    
                    showAlert('Contact exported successfully!', 'success');
                }
            });
    } else {
        showAlert('Contact ID not found', 'danger');
    }
}

function editContact() {
    const contactId = getContactIdFromPage();
    
    if (contactId) {
        // Redirect to edit page (implement as needed)
        window.location.href = `/contact/edit/${contactId}/`;
    } else {
        showAlert('Contact ID not found', 'danger');
    }
}

// Universal API Management Functions
function manageEmails() {
    const contactId = getContactIdFromPage();
    if (contactId) {
        window.location.href = `/wcapi/emails/manage/?contact_id=${contactId}`;
    }
}

function managePhones() {
    const contactId = getContactIdFromPage();
    if (contactId) {
        window.location.href = `/wcapi/phones/manage/?contact_id=${contactId}`;
    }
}

function manageDomains() {
    const contactId = getContactIdFromPage();
    if (contactId) {
        window.location.href = `/wcapi/domains/manage/?contact_id=${contactId}`;
    }
}

function manageAddresses() {
    const contactId = getContactIdFromPage();
    if (contactId) {
        window.location.href = `/wcapi/addresses/manage/?contact_id=${contactId}`;
    }
}

// Utility Functions
function getContactIdFromPage() {
    // Try multiple methods to get contact ID
    const urlPath = window.location.pathname;
    const urlParams = new URLSearchParams(window.location.search);
    
    // From URL path: /contact/123/ or /contact/123
    const pathMatch = urlPath.match(/\/contact\/(\d+)\/?$/);
    if (pathMatch) {
        return pathMatch[1];
    }
    
    // From URL parameters: ?contact_id=123
    const contactId = urlParams.get('contact_id');
    if (contactId) {
        return contactId;
    }
    
    // From data attribute on the page
    const contactElement = document.querySelector('[data-contact-id]');
    if (contactElement) {
        return contactElement.getAttribute('data-contact-id');
    }
    
    return null;
}

function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        <i class="fas fa-${getAlertIcon(type)}"></i> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert at top of main content
    const main = document.querySelector('main');
    if (main) {
        main.insertBefore(alertDiv, main.firstChild);
    }
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

function getAlertIcon(type) {
    const icons = {
        'success': 'check-circle',
        'danger': 'exclamation-triangle',
        'warning': 'exclamation-circle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

// Initialize page
// In core/static/js/app.js - Update to use contact_id convention
function getContactIdFromPage() {
    // Try multiple methods to get contact ID using contact_id convention
    const urlPath = window.location.pathname;
    const urlParams = new URLSearchParams(window.location.search);
    
    // From URL path: /contact/123/ or /contact/123
    const pathMatch = urlPath.match(/\/contact\/(\d+)\/?$/);
    if (pathMatch) {
        return pathMatch[1];
    }
    
    // From URL parameters: ?contact_id=123 (Universal API convention)
    const contactId = urlParams.get('contact_id');
    if (contactId) {
        return contactId;
    }
    
    // Legacy support for ?id=123
    const legacyId = urlParams.get('id');
    if (legacyId) {
        return legacyId;
    }
    
    // From data attribute on the page
    const contactElement = document.querySelector('[data-id-contact]');
    if (contactElement) {
        return contactElement.getAttribute('data-id-contact');
    }
    
    return null;
}

// Universal API Management Functions with contact_id convention
function manageEmails() {
    const idContact = getContactIdFromPage();
    if (idContact) {
        window.location.href = `/wcapi/emails/manage/?contact_id=${idContact}`;
    }
}

function managePhones() {
    const idContact = getContactIdFromPage();
    if (idContact) {
        window.location.href = `/wcapi/phones/manage/?contact_id=${idContact}`;
    }
}

function manageDomains() {
    const idContact = getContactIdFromPage();
    if (idContact) {
        window.location.href = `/wcapi/domains/manage/?contact_id=${idContact}`;
    }
}

function manageAddresses() {
    const idContact = getContactIdFromPage();
    if (idContact) {
        window.location.href = `/wcapi/addresses/manage/?contact_id=${idContact}`;
    }
}

// Export for global use
window.UniversalAPI = UniversalAPI;
window.showAlert = showAlert;
window.sendTestEmail = sendTestEmail;
window.exportContact = exportContact;
window.editContact = editContact;
window.manageEmails = manageEmails;
window.managePhones = managePhones;
window.manageDomains = manageDomains;
window.manageAddresses = manageAddresses;