"""
core.services.ui_config — Save UI configuration to Contact.config.ui

All user interface preferences live in one namespace: config.ui
  theme    — active mode, dark/light color sets, font size
  navbar   — models list, dashboards list
  console  — visible, position, height
  detail   — auto_edit, default_view
  list     — page_size, default_sort
  badge    — bg_color, text_color, initials
  format   — button_style, phone_display, date_format, currency_locale

Called via wcapi/manage { action: "save_ui_config", config_ui: { theme: { active: "dark" } } }
"""
import logging
from django.apps import apps

log = logging.getLogger(__name__)

# Default config.ui structure — seed for new contacts
DEFAULT_UI_CONFIG = {
    "theme": {
        "active": "dark",
        "dark": {
            "colors": {"text": "#ececec", "surface": "#252526", "accent": "#9cdcfe"},
            "font": {"size": 14},
        },
        "light": {
            "colors": {"text": "#212529", "surface": "#ffffff", "accent": "#1e40af"},
            "font": {"size": 14},
        },
    },
    "navbar": {
        "models": ["proposal", "order", "invoice", "purchase", "action"],
        "dashboards": [
            "dashboard", "products", "transactions", "orgs",
            "administration", "alice", "kanban", "gantt",
            "databrowser", "json",
        ],
    },
    "console": {
        "visible": True,
        "position": "bottom",
        "height": 200,
    },
    "detail": {
        "auto_edit": True,
        "default_view": "app",
    },
    "list": {
        "page_size": 50,
        "default_sort": "dt_modified",
    },
    "badge": {
        "bg_color": "",
        "text_color": "",
        "initials": "",
    },
    "format": {
        "button_style": "glass",
        "phone_display": "local",
        "date_format": "MM/DD/YYYY",
        "currency_locale": "en-US",
    },
}


def save_ui_config(config_ui: dict, contact_id: int = None) -> dict:
    """
    Deep-merge config_ui into Contact.config.ui for the given user.

    Accepts partial updates — e.g. {"theme": {"active": "light"}} merges
    into the existing theme without clobbering other theme keys.
    """
    if not config_ui:
        return {"saved": False, "reason": "no config_ui provided"}

    Contact = apps.get_model('core', 'Contact')
    cid = contact_id or 8  # TODO: get from request.user when auth is wired

    try:
        contact = Contact.objects.get(id=cid)
    except Contact.DoesNotExist:
        return {"saved": False, "reason": f"contact {cid} not found"}

    config = contact.config if isinstance(contact.config, dict) else {}
    ui = config.get('ui', {})
    _deep_merge(ui, config_ui)
    config['ui'] = ui
    contact.config = config
    contact.save(update_fields=['config', 'dt_modified'])

    log.info(f"Saved config.ui for contact {cid}: {list(config_ui.keys())}")
    return {"saved": True, "contact_id": cid, "keys": list(config_ui.keys())}


def get_ui_config(contact_id: int = None) -> dict:
    """Return config.ui for a contact, with defaults filled in."""
    Contact = apps.get_model('core', 'Contact')
    cid = contact_id or 8

    try:
        contact = Contact.objects.get(id=cid)
    except Contact.DoesNotExist:
        return {**DEFAULT_UI_CONFIG}

    config = contact.config if isinstance(contact.config, dict) else {}
    ui = config.get('ui', {})

    # Merge defaults under saved values (saved wins)
    result = {}
    _deep_merge(result, DEFAULT_UI_CONFIG)
    _deep_merge(result, ui)
    return result


def migrate_prefs_to_config_ui(contact_id: int) -> dict:
    """
    One-time migration: move scattered prefs into config.ui.

    Sources:
      prefs.wcui / prefs.staff.wcui → config.ui.theme, config.ui.format, config.ui.detail
      prefs.badge → config.ui.badge
      prefs.color_mode / prefs.staff.color_mode → config.ui.theme
      prefs.display → config.ui.detail
    """
    Contact = apps.get_model('core', 'Contact')

    try:
        contact = Contact.objects.get(id=contact_id)
    except Contact.DoesNotExist:
        return {"migrated": False, "reason": f"contact {contact_id} not found"}

    prefs = contact.prefs if isinstance(contact.prefs, dict) else {}
    config = contact.config if isinstance(contact.config, dict) else {}
    ui = config.get('ui', {})

    # Start from defaults
    _deep_merge(ui, DEFAULT_UI_CONFIG)

    # --- Pull from prefs.wcui or prefs.staff.wcui ---
    wcui = prefs.get('staff', {}).get('wcui', {}) or prefs.get('wcui', {})
    if wcui:
        # Theme
        if 'theme' in wcui:
            ui.setdefault('theme', {})['active'] = wcui['theme']
        if 'font_size' in wcui:
            active = ui.get('theme', {}).get('active', 'dark')
            ui.setdefault('theme', {}).setdefault(active, {}).setdefault('font', {})['size'] = wcui['font_size']

        # Detail
        for key in ('detail_view_pref', 'view_mode'):
            if key in wcui:
                ui.setdefault('detail', {})['default_view'] = wcui[key]

        # Format
        fmt = ui.setdefault('format', {})
        for key in ('button_style', 'phone_display', 'date_format', 'currency_locale', 'phone_separator', 'default_country'):
            if key in wcui:
                fmt[key] = wcui[key]

    # --- Pull from prefs.badge ---
    badge = prefs.get('badge', {})
    if badge:
        ui['badge'] = {**ui.get('badge', {}), **badge}

    # --- Pull from prefs.color_mode or prefs.staff.color_mode ---
    color_mode = prefs.get('staff', {}).get('color_mode', {}) or prefs.get('color_mode', {})
    if color_mode:
        # color_mode was {list: "dark", detail: "light"} — zone-specific themes
        # This was a partial override; store as reference but theme.active is the primary
        pass  # Zone themes were experimental — config.ui.theme.active is the replacement

    # --- Pull from prefs.display ---
    display = prefs.get('display', {})
    if display:
        if 'theme' in display:
            ui.setdefault('theme', {})['active'] = display['theme']

    config['ui'] = ui
    contact.config = config
    contact.save(update_fields=['config', 'dt_modified'])

    migrated_keys = []
    if wcui:
        migrated_keys.append('wcui')
    if badge:
        migrated_keys.append('badge')
    if color_mode:
        migrated_keys.append('color_mode')

    log.info(f"Migrated prefs → config.ui for contact {contact_id}: {migrated_keys}")
    return {"migrated": True, "contact_id": contact_id, "sources": migrated_keys}


def _deep_merge(target: dict, source: dict):
    """Recursively merge source into target. Source wins on leaf conflicts."""
    for key, val in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(val, dict):
            _deep_merge(target[key], val)
        else:
            target[key] = val
