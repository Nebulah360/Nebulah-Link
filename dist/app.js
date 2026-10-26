'use strict';
const $=id=>document.getElementById(id);
let phoneBrowser=false, browserPaired=false, connected=false, inspectionId=null, candidate=null, keyTimeout=null;
function setPcAccess(pc){
  phoneBrowser=!pc;
  document.querySelector('nav').hidden=!pc;
  for(const element of document.querySelectorAll('.view'))element.hidden=!pc||element.id!=='storage';
  $('storage-health-panel').hidden=!pc;
  $('target').parentElement.hidden=!pc;
  $('connect-form').querySelector('button').hidden=!pc;
  const appearance=$('appearance-open');if(appearance)appearance.hidden=!pc;
  const discord=$('discord-presence-panel');if(discord)discord.hidden=!pc;
  const launcher=$('launcher-settings-panel');if(launcher)launcher.hidden=!pc;
}
async function api(action,data={},authorization){
  const headers={'Content-Type':'application/json'};
  if(authorization)headers.Authorization='Bearer '+authorization;
  const response=await fetch('/api/'+action,{method:'POST',headers,body:JSON.stringify(data),credentials:'same-origin'});
  const result=await response.json();
  if(!response.ok){const error=Error(result.error||'The local bridge could not complete this request.');error.recoveryRequired=Boolean(result.recovery_required);throw error;}
  return result;
}
async function task(work){
  $('message').textContent='Working…';
  try{await work();$('message').textContent='Done.';}catch(error){$('message').textContent=error.message;}
}
const knownTitles={'415607D1':'Call of Duty 2','415607E6':'Call of Duty 4','4156081C':'Call of Duty: World at War','41560817':'Call of Duty: Modern Warfare 2','41560855':'Call of Duty: Black Ops','415608CB':'Call of Duty: Modern Warfare 3','41560914':'Call of Duty: Advanced Warfare','415608FC':'Call of Duty: Ghosts','415608C3':'Call of Duty: Black Ops 2','4156091D':'Call of Duty: Black Ops 3'};
function runningTitleName(title){
  const path=title?.executable||'',file=path.split(/[\\/]/).pop();
  if(title?.title_id==='FFFE07D1'){
    if(/^(?:360Dash(?:Rev\d+)?|NebulahDash)\.xex$/i.test(file))return 'Nebulah Dash';
    if(/^Aurora\.xex$/i.test(file)||/[\\/]Aurora[\\/]default\.xex$/i.test(path))return 'Aurora';
    if(/^dash\.xex$/i.test(file))return 'Xbox 360 Dashboard';
  }
  if(typeof title?.name==='string'&&title.name.trim()&&!/\.xex$/i.test(title.name.trim()))return title.name.trim();
  return knownTitles[title?.title_id]||(title?.title_id?'Title name unavailable':'Unavailable');
}
function showStatus(value){
  connected=true;
  $('connection').textContent='Connected';
  $('title').textContent=runningTitleName(value.current_title);
  $('cpu').textContent=value.temperatures?.cpu?value.temperatures.cpu+' °C':'Unavailable';
  $('gpu').textContent=value.temperatures?.gpu?value.temperatures.gpu+' °C':'Unavailable';
  $('kernel').textContent=value.kernel||'Unavailable';
  const selected=$('drive').value;
  $('drive').replaceChildren(...(value.drives||[]).map(root=>new Option(root,root)));
  if((value.drives||[]).includes(selected))$('drive').value=selected;
  if(!$('folder').value)$('folder').value=$('drive').value;
}
function saveDownload(name,bytes,type='application/octet-stream'){
  const url=URL.createObjectURL(new Blob([bytes],{type}));
  const link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function inspect(path){
  const value=await api('games/inspect',{path});inspectionId=value.inspection_id||null;
  candidate=null;$('candidate-download').disabled=true;$('candidate').textContent='';
  $('inspection').textContent=JSON.stringify(value,null,2);
  $('candidate-form').hidden=!inspectionId;
}
function button(label,work){const node=document.createElement('button');node.type='button';node.className='secondary';node.textContent=label;node.onclick=()=>task(work);return node;}
function fileRow(file,folder){
  const row=document.createElement('div');row.className='file';
  const label=document.createElement('span');label.className='name';label.textContent=(file.directory?'📁 ':'')+file.name;row.append(label);
  const path=folder.replace(/\\?$/,'\\')+file.name;
  if(file.directory)row.append(button('Open',async()=>{$('folder').value=path+'\\';await browse();}));
  else{
    if(!/(cpukey|keyvault|^kv)/.test(file.name.toLowerCase().replace(/[^a-z0-9]/g,'')))row.append(button('Download',async()=>{const value=await api('files/download',{path});const bytes=Uint8Array.from(atob(value.base64),c=>c.charCodeAt(0));saveDownload(value.filename,bytes);$('inspection').textContent='Download SHA-256: '+value.sha256;}));
    if(/\.xex$/i.test(file.name)){
      row.append(button('Inspect',()=>inspect(path)));
      row.append(button('Launch',()=>validateAndLaunch(path)));
      row.append(button('Module',()=>useAsModule(path)));
    }
  }
  row.append(button('Favorite',()=>api('favorites/save',{path,name:file.name,directory:!!file.directory,mode:''})));
  return row;
}
async function browse(){
  const folder=$('folder').value;const value=await api('browse',{path:folder});
  $('files').replaceChildren(...value.files.map(file=>fileRow(file,folder)));
  if(!value.files.length)$('files').textContent='No entries returned.';
}
async function library(){
  const value=await api('library/list',{view:'files'});
  const files=value.files||[];
  $('library-files').replaceChildren(...files.map(file=>{
    const parts=file.path.split('\\'),name=parts.pop(),row=fileRow({name,directory:false},parts.join('\\'));if(/\.xex$/i.test(name))row.append(button('Find content',()=>addons(file.path)));return row;
  }));
  const saved=await api('favorites/list');
  $('favorites').replaceChildren(...[...(saved.favorites||[]),...(saved.recent||[])].map(item=>{
    const row=document.createElement('div');row.className='file';const label=document.createElement('span');label.className='name';label.textContent=item.name||item.path;row.append(label);
    if(item.directory)row.append(button('Browse',async()=>{$('folder').value=item.path;selectTab('storage');await browse();}));
    else if(/\.xex$/i.test(item.path))row.append(button('Inspect',()=>inspect(item.path)));
    return row;
  }));
}
function bytesLabel(value){
  if(typeOfNumber(value)!=='number'||value<0)return 'unknown';
  if(value<1024)return value+' B';
  if(value<1048576)return (value/1024).toFixed(1)+' KiB';
  if(value<1073741824)return (value/1048576).toFixed(1)+' MiB';
  return (value/1073741824).toFixed(2)+' GiB';
}
function typeOfNumber(value){return typeof value==='number'&&Number.isFinite(value)?'number':'other';}
async function addons(gamePath){
  const value=await api('games/addons',{path:gamePath});
  const rows=[];
  for(const [kind,items] of Object.entries(value.items||{}))for(const item of items){
    const row=document.createElement('div');row.className='file';
    const label=document.createElement('span');label.className='name';label.textContent=kind.replaceAll('_',' ')+' · '+item.name+' · '+item.source;row.append(label);
    if(kind==='title_updates')row.append(button('Inspect update',async()=>{$('addon-inspection').textContent=JSON.stringify(await api('games/title-update',{game_path:gamePath,path:item.path}),null,2);$('addon-inspection').hidden=false;}));
    rows.push(row);
  }
  $('addons').replaceChildren(...rows);
  if(!rows.length)$('addons').textContent=value.incomplete?'Search incomplete; no candidates found.':'No related content found.';
  $('addon-inspection').hidden=true;
  const plan=$('install-plan-panel');
  if(plan){plan.hidden=false;$('install-plan-game-path').value=gamePath;$('install-plan-outcome').textContent='';}
}
async function refreshCherryLocal(){
  const status=await api('cherry/status');
  $('cherry-local-enabled').checked=status.enabled;
  $('cherry-local-form').hidden=!status.enabled;
  $('cherry-local-status').textContent=status.enabled?'Local virtual profile API enabled for this bridge session.':'Local virtual profile API off.';
  if(!status.enabled)return;
  const profile=await api('cherry/profile');
  for(const key of ['gamertag','gamerscore','membership','motto','bio','location','theme','avatarId'])
    $('cherry-'+key.replace(/[A-Z]/g,letter=>'-'+letter.toLowerCase())).value=profile[key];
  $('cherry-bypass').checked=profile.bypass;
}
function showProfileDetail(result,storage){
  const dialog=$('profile-detail-dialog');
  $('profile-detail-title').textContent=result.display_name||'Name unavailable';
  $('profile-detail-storage').textContent=storage||'';
  const picture=$('profile-detail-picture');
  if(result.picture){picture.src=result.picture;picture.hidden=false;}else{picture.removeAttribute('src');picture.hidden=true;}
  const dash=result.dashboard||{};
  $('profile-detail-score').textContent=dash.score!=null?String(dash.score):'Unavailable';
  $('profile-detail-games').textContent=dash.games!=null?String(dash.games):'Unavailable';
  $('profile-detail-size').textContent=bytesLabel(result.size);
  $('profile-detail-hash').textContent=result.sha256||'';
  $('profile-detail-note').textContent=result.note||'';
  dialog.showModal();
}
async function loadProfilePackages(){
  $('profile-list').replaceChildren();
  $('profile-list-status').textContent='Reading profile packages…';
  $('profile-package-result').textContent='Choose a profile to inspect its package.';
  const result=await api('profile-package/list');
  $('profile-list-status').textContent=result.profiles.length+' profile package'+(result.profiles.length===1?'':'s')+
    (result.unavailable?' · '+result.unavailable+' unavailable':'')+(result.truncated?' · truncated':'')+'.';
  for(const profile of result.profiles){
    const card=document.createElement('button');card.type='button';card.className='profile-card';
    if(profile.picture){const img=document.createElement('img');img.src=profile.picture;img.alt='';card.append(img);}
    else{const empty=document.createElement('span');empty.className='profile-picture-empty';empty.textContent='No picture';card.append(empty);}
    const text=document.createElement('span');
    const name=document.createElement('strong');name.textContent=profile.display_name;
    const meta=document.createElement('small');meta.textContent=(profile.storage||'')+(profile.dashboard?.score!=null?' · score '+profile.dashboard.score:'');
    text.append(name,meta);card.append(text);
    card.onclick=()=>task(async()=>{
      $('profile-package-result').textContent='Inspecting…';
      const inspected=await api('profile-package/inspect',{selection:profile.selection});
      $('profile-package-result').textContent='Profile package inspected.';
      showProfileDetail(inspected,profile.storage);
    });
    $('profile-list').append(card);
  }
  if(!result.profiles.length)$('profile-package-result').textContent='No readable profile package found on HDD or numbered USB devices.';
}
async function profiles(){
  const value=await api('profiles/list');
  $('profiles').replaceChildren(...value.profiles.map(item=>button(item.name,async()=>{$('target').value=item.target;showStatus(await api('connect',{target:item.target}));})));
}
function clearPrivate(){clearTimeout(keyTimeout);$('private-key').textContent='';}
function selectTab(name){
  clearPrivate();for(const element of document.querySelectorAll('.view'))element.hidden=element.id!==name;$('storage-health-panel').hidden=name!=='storage';
  for(const element of document.querySelectorAll('[data-tab]')){const selected=element.dataset.tab===name;element.classList.toggle('selected',selected);element.setAttribute('aria-pressed',String(selected));}
}
for(const element of document.querySelectorAll('[data-tab]'))element.onclick=()=>task(async()=>{selectTab(element.dataset.tab);if(element.dataset.tab==='library')await library();if(element.dataset.tab==='discover'&&typeof refreshDiscover==='function')await refreshDiscover();if(element.dataset.tab==='console'&&connected){await loadProfilePackages().catch(error=>{$('profile-list-status').textContent=error.message;});if(typeof refreshModules==='function')await refreshModules();}if(element.dataset.tab==='usb')await refreshUsbTools();if(element.dataset.tab==='settings'){const value=await api('settings/read');$('default-ip').value=value.default_console_ip;await profiles();}});
$('install-plan-preview').onclick=()=>task(async()=>{
  const gamePath=$('install-plan-game-path').value;const selected=$('install-plan-file').files?.[0];
  if(!gamePath)throw Error('Select a saved XEX with Find content first.');
  if(!selected)throw Error('Choose a local file.');
  $('install-plan-outcome').textContent='Checking destination…';
  const result=await api('games/install-plan',{game_path:gamePath,kind:$('install-plan-kind').value,name:selected.name,size:selected.size});
  $('install-plan-outcome').textContent=result.destination+' · '+bytesLabel(result.size)+' · '+(result.folder_exists?'folder exists':'folder must be created')+' · '+(result.conflict?'name conflict':'no name conflict')+' · '+(result.free===null?'free space unknown':bytesLabel(result.free)+' free')+' · '+(result.enough_space===false?'insufficient reported space':'space check '+(result.enough_space===true?'passes':'unknown'))+'. '+result.note;
});
$('profile-package-refresh').onclick=()=>task(loadProfilePackages);
$('profile-package-inspect').onclick=()=>task(async()=>{
  const path=$('profile-package-path').value.trim();if(!path)throw Error('Enter a profile package path.');
  $('profile-package-result').textContent='Inspecting…';
  const result=await api('profile-package/inspect',{path});
  $('profile-package-result').textContent='Profile package inspected.';
  showProfileDetail(result);
});
$('profile-detail-dialog')?.querySelector('.close')?.addEventListener('click',()=>$('profile-detail-dialog').close());
$('discover-detail-dialog')?.querySelector('.close')?.addEventListener('click',()=>$('discover-detail-dialog').close());
$('appearance-dialog')?.querySelector('.close')?.addEventListener('click',()=>$('appearance-dialog').close());
$('cherry-local-panel').ontoggle=()=>{if($('cherry-local-panel').open)task(refreshCherryLocal);};
$('cherry-local-enabled').onchange=()=>task(async()=>{
  try{await api('cherry/switch',{enabled:$('cherry-local-enabled').checked});await refreshCherryLocal();}
  catch(error){$('cherry-local-enabled').checked=!$('cherry-local-enabled').checked;throw error;}
});
$('cherry-local-form').onsubmit=event=>{event.preventDefault();task(async()=>{
  await api('cherry/profile',{gamertag:$('cherry-gamertag').value,gamerscore:Number($('cherry-gamerscore').value),
    membership:$('cherry-membership').value,motto:$('cherry-motto').value,bio:$('cherry-bio').value,
    location:$('cherry-location').value,theme:$('cherry-theme').value,
    avatarId:Number($('cherry-avatar-id').value),bypass:$('cherry-bypass').checked});
  $('cherry-local-status').textContent='Virtual profile saved on this PC. Xbox profile unchanged.';
});};
$('connect-form').onsubmit=event=>{event.preventDefault();task(async()=>{clearPrivate();inspectionId=null;const recovery=await api('recovery/status');if(recovery.recovery_required&&!confirm('A previous read failed. Confirm the console is responsive before reconnecting.'))return;showStatus(await api('connect',{target:$('target').value.trim(),recovery_confirmed:recovery.recovery_required}));});};
$('refresh').onclick=()=>task(async()=>showStatus(await api('status')));
$('storage-health').onclick=()=>task(async()=>{$('storage-health-result').textContent=JSON.stringify(await api('storage/health'),null,2);});
$('storage-discover').onclick=()=>task(async()=>{const value=await api('storage/discover');$('drive').replaceChildren(...value.drives.map(root=>new Option(root,root)));$('folder').value=$('drive').value;});
$('drive').onchange=()=>{$('folder').value=$('drive').value;};
$('browse-form').onsubmit=event=>{event.preventDefault();task(browse);};
$('up').onclick=()=>task(async()=>{const path=$('folder').value.replace(/\\$/,'');if(path.includes('\\'))$('folder').value=path.slice(0,path.lastIndexOf('\\')+1);await browse();});
$('candidate-form').onsubmit=event=>{event.preventDefault();task(async()=>{if(!inspectionId)throw Error('Inspect an XEX first.');const value=await api('games/propose',{inspection_id:inspectionId,title:$('candidate-title').value,provenance:$('provenance').value});candidate=value.candidate;$('candidate').textContent=JSON.stringify(candidate,null,2);$('candidate-download').disabled=false;});};
$('candidate-download').onclick=()=>{if(candidate)saveDownload('game-baseline-candidate.json',JSON.stringify(candidate,null,2),'application/json');};
$('library-refresh').onclick=()=>task(library);
$('scan').onclick=()=>task(async()=>{let value=await api('scan/start',{path:$('folder').value,formats:'xex',depth:6});while(value.state==='running'){ $('scan-status').textContent=value.visited+' folders · '+value.found+' XEX files';value=await api('scan/step',{id:value.id});} $('scan-status').textContent=value.state+' · '+value.found+' files · '+value.errors+' unavailable folders';await library();});
$('capture').onclick=()=>task(async()=>{const value=await api('console/screenshot');$('screen').src='data:image/png;base64,'+value.png;$('screen').hidden=false;});
$('cpu-key').onclick=()=>task(async()=>{clearPrivate();if(!confirm('Read and temporarily display the connected console CPU key on this trusted device? HTTP on this network is unencrypted.'))return;const ticket=await api('cpu-key/prepare');const value=await api('cpu-key/reveal',{confirmed:true,confirmation_ticket:ticket.confirmation_ticket});$('private-key').textContent=value.cpu_key;keyTimeout=setTimeout(clearPrivate,60000);});
document.addEventListener('visibilitychange',()=>{if(document.hidden)clearPrivate();});
$('settings-form').onsubmit=event=>{event.preventDefault();task(()=>api('settings/save',{default_console_ip:$('default-ip').value.trim(),allow_writes:false}));};
$('profile-form').onsubmit=event=>{event.preventDefault();task(async()=>{await api('profiles/save',{name:$('profile-name').value,target:$('profile-target').value});await profiles();});};
$('phone-form').onsubmit=event=>{event.preventDefault();task(async()=>{const value=await api('session/phone-pair',{pin:$('phone-pin').value});setPcAccess(false);showStatus(value.status);$('phone-pin').value='';});};
$('show-pin').onclick=()=>task(async()=>{const value=await api('session/phone-pin');$('pin-display').textContent=value.url+' · PIN '+value.pin;setTimeout(()=>$('pin-display').textContent='',60000);});
$('sign-out').onclick=()=>task(async()=>{await api('session/logout');clearPrivate();connected=false;inspectionId=null;$('connection').textContent='Signed out.';$('screen').removeAttribute('src');$('screen').hidden=true;});
task(async()=>{
  const pair=new URLSearchParams(location.hash.slice(1)).get('pair');
  history.replaceState(null,'',location.pathname);
  if(pair){await api('session/pair',{},pair);browserPaired=true;}
  else{
    try{
      const value=await api('session/resume');
      if(value.status){browserPaired=true;setPcAccess(value.pc!==false);showStatus(value.status);return;}
      if(value.awaiting_console){browserPaired=true;setPcAccess(value.pc!==false);}
    }catch{}
    if(!browserPaired){await api('session/local-pair');browserPaired=true;}
  }
  $('connection').textContent='PC paired. Connect a console to begin.';
});
