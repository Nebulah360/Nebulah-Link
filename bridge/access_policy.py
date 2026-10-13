"""Public edition operation allowlists; no runtime write override exists."""

ADAPTER_ACTIONS = frozenset({'status','cpu-key','plugins','storage','capacity','file-info',
                             'download-file','browse','browse-many','receive'})
BRIDGE_ACTIONS = frozenset('''connect status recovery/status browse browse-many validate
    storage/discover storage/capacity storage/health files/download console/screenshot
    games/inspect games/propose games/list games/cover games/remove games/save
    games/addons games/title-update registry/list registry/check plugins/list
    profiles/list profiles/save profiles/remove favorites/list favorites/save favorites/remove
    library/list library/label library/clear library/prune-uninspected
    metadata/lookup metadata/aurora-import scan/start scan/step scan/cancel
    repos/list repos/save repos/remove repos/check discover/status discover/filters
    discover/suggest discover/search discover/detail usb/inventory
    discord/status discord/start discord/stop cpu-key/prepare cpu-key/reveal'''.split())
LOCAL_ACTIONS = frozenset('''session/local-pair session/pair session/phone-pair session/resume
    session/logout session/phone-pin launcher/settings launcher/save settings/read settings/save'''.split())
API_ACTIONS = BRIDGE_ACTIONS | LOCAL_ACTIONS


def assert_allowed(action, allowed):
    if not isinstance(action, str) or action not in allowed:
        raise ValueError('This free bridge accepts read-only console operations.')
