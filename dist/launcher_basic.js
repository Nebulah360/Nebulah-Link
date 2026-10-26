'use strict';
/* Launcher preferences only. No console writes, FTP, packet, or admin controls. */
const launcherPanel=$('launcher-settings-panel');
if(launcherPanel){
  launcherPanel.hidden=phoneBrowser;
  if(!phoneBrowser){
    const form=$('launcher-settings-form');
    launcherPanel.addEventListener('toggle',()=>{
      if(!launcherPanel.open)return;
      task(async()=>{
        const settings=await api('launcher/settings');
        $('launcher-phone-access').checked=settings.phone_access;
        $('launcher-browser').value=settings.browser;
        $('launcher-open-browser').checked=settings.open_browser;
        $('launcher-rpc-on-startup').checked=settings.rpc_on_startup;
        $('launcher-settings-status').textContent='Saved settings loaded. Changes take effect on the next bridge start.';
      });
    });
    form.addEventListener('submit',event=>{
      event.preventDefault();
      task(async()=>{
        await api('launcher/save',{
          phone_access:$('launcher-phone-access').checked,
          browser:$('launcher-browser').value,
          open_browser:$('launcher-open-browser').checked,
          rpc_on_startup:$('launcher-rpc-on-startup').checked
        });
        $('launcher-settings-status').textContent='Saved. Restart Nebulah Link to apply these settings.';
      });
    });
  }
}
