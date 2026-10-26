"""First-party Nebulah modules that may use the storage upload checkpoint.

Filename plus the DLL/plugin flag only. Editor and LinkUI modules are not trusted here.
"""

PRODUCT_PLUGINS = {
    'nebulahcompanion.xex': {
        'id': 'nebulah-companion',
        'name': 'Nebulah Companion',
        'trace': 'Nebulah Companion module. Structural XEX checks and digest identity only. '
                 'Eligible for storage upload. Load via Plugins; cannot launch as a title.',
    },
}


def product_plugin_trust(destination, inspection):
    """Return a trust trace for the Companion module, else None."""
    if not inspection or inspection.get('plugin') is not True:
        return None
    if not isinstance(destination, str):
        return None
    filename = destination.replace('/', '\\').rsplit('\\', 1)[-1]
    entry = PRODUCT_PLUGINS.get(filename.casefold())
    if not entry:
        return None
    return {
        'id': entry['id'],
        'name': entry['name'],
        'filename': filename,
        'plugin': True,
        'upload_allowed': True,
        'launch_as_title': False,
        'trace': entry['trace'],
    }
