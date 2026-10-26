'use strict';
async function refreshFtp(){
  const toggle=$('settings-ftp-enabled');
  const status=$('settings-ftp-status');
  if(!toggle||!status)return;
  if(phoneBrowser||!connected){
    toggle.disabled=true;
    toggle.checked=false;
    status.textContent=phoneBrowser?'FTP proxy is available only on the bridge PC.':'Connect a console on this PC to manage FTP.';
    return;
  }
  const result=await api('ftp/status');
  toggle.disabled=false;
  toggle.checked=result.enabled===true;
  if(result.enabled){
    const roots=Object.keys(result.roots||{}).join(', ')||'none';
    status.textContent='FTP on '+result.bind+' user '+result.username+' password '+result.password+'. Roots: '+roots+'. Cleartext. No TLS. 128 MiB cap. No overwrite.';
  }else status.textContent='FTP proxy off. Enable to bind 127.0.0.1:2121 for this session.';
}
const ftpPanel=$('settings-ftp-panel');
if(ftpPanel){
  ftpPanel.addEventListener('toggle',()=>{if(ftpPanel.open)task(refreshFtp);});
  $('settings-ftp-enabled').onchange=()=>task(async()=>{
    const enabled=$('settings-ftp-enabled').checked;
    $('settings-ftp-enabled').disabled=true;
    try{
      if(enabled){
        if(!confirm('Start the PC FTP proxy on 127.0.0.1:2121? Uploads stay capped, refuse overwrite, and stage before the console write.')){
          $('settings-ftp-enabled').checked=false;
          return;
        }
        await api('ftp/start',{host:'127.0.0.1',port:2121,confirmed:true});
      }else await api('ftp/stop');
      await refreshFtp();
    }catch(error){
      $('settings-ftp-enabled').checked=!enabled;
      $('settings-ftp-status').textContent=error.message;
      throw error;
    }finally{$('settings-ftp-enabled').disabled=!connected||phoneBrowser;}
  });
}
