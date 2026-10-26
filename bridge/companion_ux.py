"""Xbox notification catalog for Basic console toasts.

Editor menu hints and Pro-only catalog ids are omitted. Freeform console/notify
still requires an explicit confirmation and a supported icon.
"""
from __future__ import annotations

CATALOG = {
    'link.connected': {
        'message': 'Nebulah Link connection successful',
        'icon': 14,
        'tier': 'basic',
    },
    'companion.loaded': {
        'message': 'NebulahCompanion Loaded',
        'icon': 34,
        'tier': 'basic',
    },
    'companion.fault': {
        'message': 'Nebulah Companion needs recovery',
        'icon': 14,
        'tier': 'basic',
    },
    'companion.input_unsupported': {
        'message': 'Companion input unavailable on this dash',
        'icon': 14,
        'tier': 'basic',
    },
    'companion.input_fault': {
        'message': 'Companion input fault - cold reboot required',
        'icon': 14,
        'tier': 'basic',
    },
}

BASIC_CATALOG_IDS = frozenset(key for key, item in CATALOG.items() if item['tier'] == 'basic')
PRO_CATALOG_IDS = frozenset()
UI_SURFACES = frozenset({'none', 'toast', 'dash_ui'})


def catalog_entry(catalog_id):
    if not isinstance(catalog_id, str) or catalog_id not in CATALOG:
        raise ValueError('Choose a supported Xbox notification catalog id.')
    return CATALOG[catalog_id]


def format_message(catalog_id, *, suffix=None):
    entry = catalog_entry(catalog_id)
    message = entry['message']
    if suffix is not None:
        if not isinstance(suffix, str) or not suffix or len(suffix) > 48:
            raise ValueError('Notification suffix must be short printable text.')
        if not all(' ' <= char <= '~' for char in suffix):
            raise ValueError('Notification suffix must be printable ASCII.')
        message = message + ' - ' + suffix
    if not (1 <= len(message) <= 80) or not all(' ' <= char <= '~' for char in message):
        raise ValueError('Xbox notification text must be 1–80 printable ASCII characters.')
    return message


def resolve_notify(catalog_id, *, icon=None, suffix=None):
    entry = catalog_entry(catalog_id)
    message = format_message(catalog_id, suffix=suffix)
    toast_icon = entry['icon'] if icon is None else icon
    if type(toast_icon) is not int:
        raise ValueError('Choose a supported toast icon.')
    return {'catalog': catalog_id, 'message': message, 'icon': toast_icon, 'tier': entry['tier']}


def notify_requires_write(data):
    """Catalog toasts are Basic. Freeform text is still a confirmed console write."""
    if not isinstance(data, dict):
        return True
    catalog = data.get('catalog')
    if isinstance(catalog, str) and catalog in BASIC_CATALOG_IDS and data.get('message') is None:
        return False
    return True


def surface_advertisement(*, session_state=None, notify_ready=False, dash_ui_loaded=False):
    """Browser-facing flags. Basic does not advertise a Guide overlay or Pro dash UI."""
    if session_state == 'ready' or notify_ready:
        surface = 'toast'
    else:
        surface = 'none'
    if dash_ui_loaded:
        surface = 'toast'
    return {
        'ui_surface': surface,
        'guide_unsupported': True,
        'input_digital_only': True,
        'catalog_basic': sorted(BASIC_CATALOG_IDS),
        'catalog_pro': sorted(PRO_CATALOG_IDS),
    }
