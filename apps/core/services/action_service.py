from django.utils import timezone

def append_contact_link(instance, user_id):
    """
    Append a contact link to the action's refs.contact_links list.

    Args:
        instance: The Action instance
        user_id: The ID of the current user
    """
    now_ms = int(timezone.now().timestamp() * 1000)
    contact_links = instance.refs.get('contact_links', [])
    contact_links.append({"id_contact": user_id, "dt": now_ms})
    instance.refs['contact_links'] = contact_links