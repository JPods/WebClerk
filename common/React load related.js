async function loadAllRelated(contact_id) {
    const response = await fetch(`/wcapi/related/?contact_id=${contact_id}`);
    const data = await response.json();
    if (data.success) {
        // Now you have data.actions, data.emails, data.phones, etc.
        renderActions(data.actions);
        renderEmails(data.emails);
        renderPhones(data.phones);
        renderAddresses(data.addresses);
        renderDomains(data.domains);
    } else {
        console.error('Failed to load related data:', data.error);
    }
}