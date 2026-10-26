"""Public edition operation allowlists. Unknown actions stay rejected.

Locked Basic console writes are listed here. allow_writes is not a bypass, and
editor, RTE, profile-write, Stream360, and LinkUI actions are absent.
"""

ADAPTER_ACTIONS = frozenset({'status','cpu-key','plugins','storage','capacity','file-info',
    'download-file','browse','browse-many','receive','upload-file','upload-empty','verify-upload',
    'rename-transfer','delete-file','delete-directory','create-directory','notify','power','launch',
    'plugin-load','plugin-unload','plugin-probe','component-ping','component-probe','component-session',
    'component-input-probe','component-input-stop','component-input-pulse','component-load',
    'component-state','component-unload','component-force-release','launch-ini-export','launch-ini-hash',
    'launch-ini-read','launch-ini-resolve-plugin','launch-ini-save','launch-ini-apply'})
BRIDGE_ACTIONS = frozenset('''connect status recovery/status browse browse-many validate launch
    storage/discover storage/capacity storage/health files/download console/screenshot
    console/power console/notify controller/pulse
    console/launch-ini console/launch-ini-switch console/launch-ini/plugins
    console/launch-ini/plugins/preview console/launch-ini/plugins/save
    ftp/status ftp/start ftp/stop
    transfer/start transfer/chunk transfer/approve transfer/finish transfer/cancel
    transfer/status transfer/cleanup transfer/mkdir
    plugins/list plugins/load plugins/unload plugins/install plugins/force-release plugins/managed-state
    games/inspect games/propose games/list games/cover games/remove games/save
    games/addons games/title-update games/install-plan registry/list registry/check
    profiles/list profiles/save profiles/remove favorites/list favorites/save favorites/remove
    library/list library/label library/clear library/prune-uninspected
    metadata/lookup metadata/aurora-import scan/start scan/step scan/cancel
    repos/list repos/save repos/remove repos/check discover/status discover/filters
    discover/suggest discover/search discover/detail usb/inventory
    badbuilder/web/availability badbuilder/web/scan badbuilder/web/start badbuilder/web/status
    discord/status discord/start discord/stop cpu-key/prepare cpu-key/reveal
    profile-package/list profile-package/active profile-package/inspect
    cherry/status cherry/switch cherry/profile cherry/profile/gamertag cherry/profile/gamerscore
    cherry/profile/membership cherry/profile/motto cherry/profile/bio'''.split())
LOCAL_ACTIONS = frozenset('''session/local-pair session/pair session/phone-pair session/resume
    session/logout session/phone-pin launcher/settings launcher/save settings/read settings/save'''.split())
API_ACTIONS = BRIDGE_ACTIONS | LOCAL_ACTIONS


def assert_allowed(action, allowed):
    if not isinstance(action, str) or action not in allowed:
        raise ValueError('This free bridge rejected that operation.')
