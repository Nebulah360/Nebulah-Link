'use strict';
const $=id=>document.getElementById(id);
let connected=false, inspectionId=null, candidate=null, keyTimeout=null;
async function api(action,data={},authorization){
  const headers={'Content-Type':'application/json'};
  if(authorization)headers.Authorization='Bearer '+authorization;
  const response=await fetch('/api/'+action,{method:'POST',headers,body:JSON.stringify(data),credentials:'same-origin'});
  const result=await response.json();
  if(!response.ok)throw Error(result.error||'The local bridge could not complete this read.');
  return result;
}
async function task(work){
  $('message').textContent='Reading…';
  try{await work();$('message').textContent='Done.';}catch(error){$('message').textContent=error.message;}
}
function showStatus(value){
  connected=true;
  $('connection').textContent='Connected · read-only console access';
  $('title').textContent=value.current_title?.executable?.split(/[\\/]/).pop()||'Unavailable';
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
    row.append(button('Download',async()=>{const value=await api('files/download',{path});const bytes=Uint8Array.from(atob(value.base64),c=>c.charCodeAt(0));saveDownload(value.filename,bytes);$('inspection').textContent='Download SHA-256: '+value.sha256;}));
    if(/\.xex$/i.test(file.name))row.append(button('Inspect',()=>inspect(path)));
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
    const parts=file.path.split('\\'),name=parts.pop();return fileRow({name,directory:false},parts.join('\\'));
  }));
  const saved=await api('favorites/list');
  $('favorites').replaceChildren(...[...(saved.favorites||[]),...(saved.recent||[])].map(item=>{
    const row=document.createElement('div');row.className='file';const label=document.createElement('span');label.className='name';label.textContent=item.name||item.path;row.append(label);
    if(item.directory)row.append(button('Browse',async()=>{$('folder').value=item.path;selectTab('storage');await browse();}));
    else if(/\.xex$/i.test(item.path))row.append(button('Inspect',()=>inspect(item.path)));
    return row;
  }));
}
async function profiles(){
  const value=await api('profiles/list');
  $('profiles').replaceChildren(...value.profiles.map(item=>button(item.name,async()=>{$('target').value=item.target;showStatus(await api('connect',{target:item.target}));})));
}
function clearPrivate(){clearTimeout(keyTimeout);$('private-key').textContent='';}
function selectTab(name){
  clearPrivate();for(const element of document.querySelectorAll('.view'))element.hidden=element.id!==name;
  for(const element of document.querySelectorAll('[data-tab]'))element.classList.toggle('selected',element.dataset.tab===name);
}
for(const element of document.querySelectorAll('[data-tab]'))element.onclick=()=>task(async()=>{selectTab(element.dataset.tab);if(element.dataset.tab==='library')await library();if(element.dataset.tab==='settings'){const value=await api('settings/read');$('default-ip').value=value.default_console_ip;await profiles();}});
$('connect-form').onsubmit=event=>{event.preventDefault();task(async()=>{clearPrivate();inspectionId=null;const recovery=await api('recovery/status');if(recovery.recovery_required&&!confirm('A previous read failed. Confirm the console is responsive before reconnecting.'))return;showStatus(await api('connect',{target:$('target').value.trim(),recovery_confirmed:recovery.recovery_required}));});};
$('refresh').onclick=()=>task(async()=>showStatus(await api('status')));
$('discover').onclick=()=>task(async()=>{const value=await api('storage/discover');$('drive').replaceChildren(...value.drives.map(root=>new Option(root,root)));$('folder').value=$('drive').value;});
$('drive').onchange=()=>{$('folder').value=$('drive').value;};
$('browse-form').onsubmit=event=>{event.preventDefault();task(browse);};
$('up').onclick=()=>task(async()=>{const path=$('folder').value.replace(/\\$/,'');if(path.includes('\\'))$('folder').value=path.slice(0,path.lastIndexOf('\\')+1);await browse();});
$('candidate-form').onsubmit=event=>{event.preventDefault();task(async()=>{if(!inspectionId)throw Error('Inspect an XEX first.');const value=await api('games/propose',{inspection_id:inspectionId,title:$('candidate-title').value,provenance:$('provenance').value});candidate=value.candidate;$('candidate').textContent=JSON.stringify(candidate,null,2);$('candidate-download').disabled=false;});};
$('candidate-download').onclick=()=>{if(candidate)saveDownload('game-baseline-candidate.json',JSON.stringify(candidate,null,2),'application/json');};
$('library-refresh').onclick=()=>task(library);
$('scan').onclick=()=>task(async()=>{let value=await api('scan/start',{path:$('folder').value,formats:'xex',depth:6});while(value.state==='running'){ $('scan-status').textContent=value.visited+' folders · '+value.found+' XEX files';value=await api('scan/step',{id:value.id});} $('scan-status').textContent=value.state+' · '+value.found+' files · '+value.errors+' unavailable folders';await library();});
$('capture').onclick=()=>task(async()=>{const value=await api('console/screenshot');$('screen').src='data:image/png;base64,'+value.png;$('screen').hidden=false;});
$('modules').onclick=()=>task(async()=>{$('module-list').textContent=JSON.stringify(await api('plugins/list'),null,2);});
$('cpu-key').onclick=()=>task(async()=>{clearPrivate();if(!confirm('Read and temporarily display the connected console CPU key on this trusted device? HTTP on this network is unencrypted.'))return;const ticket=await api('cpu-key/prepare');const value=await api('cpu-key/reveal',{confirmed:true,confirmation_ticket:ticket.confirmation_ticket});$('private-key').textContent=value.cpu_key;keyTimeout=setTimeout(clearPrivate,60000);});
document.addEventListener('visibilitychange',()=>{if(document.hidden)clearPrivate();});
$('settings-form').onsubmit=event=>{event.preventDefault();task(()=>api('settings/save',{default_console_ip:$('default-ip').value.trim(),allow_writes:false}));};
$('profile-form').onsubmit=event=>{event.preventDefault();task(async()=>{await api('profiles/save',{name:$('profile-name').value,target:$('profile-target').value});await profiles();});};
$('phone-form').onsubmit=event=>{event.preventDefault();task(async()=>{showStatus((await api('session/phone-pair',{pin:$('phone-pin').value})).status);$('phone-pin').value='';});};
$('show-pin').onclick=()=>task(async()=>{const value=await api('session/phone-pin');$('pin-display').textContent=value.url+' · PIN '+value.pin;setTimeout(()=>$('pin-display').textContent='',60000);});
$('sign-out').onclick=()=>task(async()=>{await api('session/logout');clearPrivate();connected=false;inspectionId=null;$('connection').textContent='Signed out.';$('screen').removeAttribute('src');$('screen').hidden=true;});
$('accent').value=localStorage.getItem('nebulah-free-accent')||'#74b5d6';
document.documentElement.style.setProperty('--accent',$('accent').value);
$('accent').oninput=()=>{document.documentElement.style.setProperty('--accent',$('accent').value);localStorage.setItem('nebulah-free-accent',$('accent').value);};
task(async()=>{const pair=new URLSearchParams(location.hash.slice(1)).get('pair');history.replaceState(null,'',location.pathname);if(pair)await api('session/pair',{},pair);else{try{const value=await api('session/resume');if(value.status){showStatus(value.status);return;}}catch{}await api('session/local-pair');}$('connection').textContent='PC paired. Connect a console to begin.';});
