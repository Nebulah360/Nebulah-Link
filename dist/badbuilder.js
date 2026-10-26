'use strict';
const bytesLabel=size=>size>=1073741824?(size/1073741824).toFixed(1)+' GiB':size>=1048576?(size/1048576).toFixed(1)+' MiB':size+' B';
let usbBuilderDisks=[];
async function refreshUsbInventory(){
  const host=$('usb-disks'),picker=$('badbuilder-disk');host.replaceChildren();if(picker)picker.replaceChildren();
  const choose=document.createElement('option');choose.value='';choose.textContent='Choose a USB disk after refresh';if(picker)picker.append(choose);
  usbBuilderDisks=[];
  $('usb-status').textContent='Reading connected Windows USB disks...';
  try{
    const result=await api('usb/inventory');
    $('usb-status').textContent=result.disks.length===0?'No USB disk is currently reported by Windows.':
      result.disks.length+' USB '+(result.disks.length===1?'disk':'disks')+' reported by Windows.';
    for(const disk of result.disks){
      const card=document.createElement('article');card.className='usb-disk';
      const heading=document.createElement('h3');heading.textContent=disk.model+' - Disk '+disk.number;
      const meta=document.createElement('p');meta.className='small';
      meta.textContent=bytesLabel(disk.bytes)+' - '+disk.partition_style+' - '+disk.operational_status+
        (disk.read_only?' - Windows read-only':'')+(disk.system||disk.boot?' - System/boot disk':'');
      card.append(heading,meta);
      if(!disk.volumes.length){const empty=document.createElement('p');empty.textContent='No mounted volume reported.';card.append(empty);}
      for(const volume of disk.volumes){
        const row=document.createElement('div');row.className='usb-volume';
        const name=document.createElement('strong');name.textContent=volume.letter+' '+volume.label;
        const detail=document.createElement('small');detail.textContent=volume.filesystem+' - '+bytesLabel(volume.free_bytes)+' free of '+bytesLabel(volume.bytes)+' - '+volume.health;
        row.append(name,detail);card.append(row);
      }
      host.append(card);
      if(disk.system||disk.boot||disk.read_only||disk.operational_status!=='Online')continue;
      usbBuilderDisks.push(disk);
      const option=document.createElement('option');option.value=String(disk.number);
      option.textContent='Disk '+disk.number+' - '+disk.model+' - '+bytesLabel(disk.bytes);if(picker)picker.append(option);
    }
    if(picker)updateBadBuilderDisk();
  }catch(error){$('usb-status').textContent=error.message||'Windows USB inventory unavailable.';throw error;}
}
$('usb-refresh').onclick=()=>task(refreshUsbInventory);

const badBuilderArchives=[
  ['dashboard-update','Dashboard update'],['exploit-badupdate','BadUpdate'],
  ['exploit-abadavatar','ABadAvatar'],['exploit-abadavatarupdate','ABadAvatar 1.3'],
  ['bootstrap-xeunshackle','XeUnshackle'],['bootstrap-freemyxe','FreeMyXe'],
  ['badupdate-gamedata','Rock Band Blitz game data'],['homebrew-aurora','Aurora'],
  ['homebrew-xexmenu','XeXMenu'],['homebrew-simple360nandflasher','Simple 360 NAND Flasher']
];
const badBuilderAvailable=!!$('badbuilder-form');
let badBuilderCustom=[],badBuilderJob=localStorage.getItem('nebulah-badbuilder-job')||null,badBuilderPoll=null;
for(const [id,name] of badBuilderArchives){
  const label=document.createElement('label');label.textContent=name;
  const input=document.createElement('input');input.type='text';input.placeholder='Optional local archive path';input.autocomplete='off';input.dataset.artifact=id;
  label.append(input);if(badBuilderAvailable)$('badbuilder-archive-paths').append(label);
}
function updateBadBuilderDisk(){
  const disk=usbBuilderDisks.find(item=>String(item.number)===$('badbuilder-disk').value);
  $('badbuilder-confirm-hint').textContent=disk?'Type ERASE DISK '+disk.number+' to erase '+disk.model+' ('+bytesLabel(disk.bytes)+').':'Choose a USB disk to see its confirmation phrase.';
  $('badbuilder-confirmation').value='';
}
if(badBuilderAvailable)$('badbuilder-disk').onchange=updateBadBuilderDisk;
function updateBadBuilderMode(){
  const update=$('badbuilder-mode').value==='update';
  $('badbuilder-exploit-options').hidden=update;
  $('badbuilder-launch').disabled=update||$('badbuilder-bootstrap').value!=='XeUnshackle';
  if($('badbuilder-launch').disabled)$('badbuilder-launch').value='';
}
if(badBuilderAvailable)$('badbuilder-mode').onchange=updateBadBuilderMode;
if(badBuilderAvailable)$('badbuilder-bootstrap').onchange=updateBadBuilderMode;
function renderBadBuilderCustom(){
  const host=$('badbuilder-custom-list');host.replaceChildren();
  badBuilderCustom.forEach((item,index)=>{
    const row=document.createElement('div');row.className='badbuilder-custom';
    const name=document.createElement('strong');name.textContent=item.path;
    const label=document.createElement('label');label.textContent='Entry point';
    const select=document.createElement('select');const none=document.createElement('option');none.value='';none.textContent='Do not auto-launch';select.append(none);
    for(const path of item.entries){const option=document.createElement('option');option.value=path;option.textContent=path;select.append(option);}
    select.value=item.entryPoint||'';select.onchange=()=>{item.entryPoint=select.value||null;renderBadBuilderLaunch();};
    label.append(select);
    const remove=document.createElement('button');remove.type='button';remove.className='secondary';remove.textContent='Remove';
    remove.onclick=()=>{badBuilderCustom.splice(index,1);renderBadBuilderCustom();renderBadBuilderLaunch();};
    row.append(name,label,remove);host.append(row);
  });
}
function renderBadBuilderLaunch(){
  const select=$('badbuilder-launch'),previous=select.value;select.replaceChildren();
  const none=document.createElement('option');none.value='';none.textContent='None';select.append(none);
  const builtins=[...document.querySelectorAll('.badbuilder-homebrew input:checked')];
  for(const input of builtins){
    if(input.value==='homebrew-xexmenu')continue;
    const option=document.createElement('option');option.value=input.value;option.textContent=input.value==='homebrew-aurora'?'Aurora':'Simple 360 NAND Flasher';select.append(option);
  }
  badBuilderCustom.forEach((item,index)=>{if(!item.entryPoint)return;const option=document.createElement('option');option.value='homebrew-custom-'+index;option.textContent=item.path.split(/[\\/]/).pop();select.append(option);});
  select.value=[...select.options].some(option=>option.value===previous)?previous:'';updateBadBuilderMode();
}
if(badBuilderAvailable)for(const input of document.querySelectorAll('.badbuilder-homebrew input'))input.onchange=renderBadBuilderLaunch;
if(badBuilderAvailable)$('badbuilder-add-custom').onclick=()=>task(async()=>{
  const path=$('badbuilder-custom-path').value.trim();if(!path)throw Error('Enter a local archive path on this PC.');
  const result=await api('badbuilder/web/scan',{path});
  badBuilderCustom.push({path,entries:result.entry_points,entryPoint:result.entry_points.length===1?result.entry_points[0]:null});
  $('badbuilder-custom-path').value='';renderBadBuilderCustom();renderBadBuilderLaunch();
  $('badbuilder-status').textContent='Archive added. Review its entry point and default launch.';
});
function badBuilderRequest(){
  const disk=usbBuilderDisks.find(item=>String(item.number)===$('badbuilder-disk').value);
  if(!disk)throw Error('Choose a current, writable USB disk.');
  const confirmation=$('badbuilder-confirmation').value.trim();
  if(confirmation!=='ERASE DISK '+disk.number)throw Error('Type ERASE DISK '+disk.number+' exactly.');
  const update=$('badbuilder-mode').value==='update',archive_paths={};
  for(const input of document.querySelectorAll('#badbuilder-archive-paths input'))if(input.value.trim())archive_paths[input.dataset.artifact]=input.value.trim();
  return {disk_number:disk.number,disk_bytes:disk.bytes,disk_model:disk.model,
    exploit:$('badbuilder-exploit').value,bootstrap:$('badbuilder-bootstrap').value,firmware_update:update,
    homebrew_ids:update?[]:[...document.querySelectorAll('.badbuilder-homebrew input:checked')].map(input=>input.value),
    custom_homebrew:update?[]:badBuilderCustom.map(item=>({path:item.path,entry_point:item.entryPoint})),
    launch_id:update?null:$('badbuilder-launch').value||null,archive_paths,confirmation};
}
async function refreshBadBuilderStatus(){
  clearTimeout(badBuilderPoll);badBuilderPoll=null;
  if(!badBuilderAvailable)return;
  if(phoneBrowser){$('badbuilder-status').textContent='Open USB tools on the bridge PC.';return;}
  try{
    const availability=await api('badbuilder/web/availability');
    if(availability.state!=='ready'){
      $('badbuilder-start').disabled=true;$('badbuilder-status').textContent=availability.message;return;
    }
    if(!badBuilderJob){$('badbuilder-start').disabled=false;$('badbuilder-status').textContent='Choose a USB disk and build settings.';return;}
    const result=await api('badbuilder/web/status',{job_id:badBuilderJob});
    $('badbuilder-status').textContent=result.message;
    $('badbuilder-start').disabled=['queued','running'].includes(result.state);
    if($('badbuilder-start').disabled)badBuilderPoll=setTimeout(refreshBadBuilderStatus,1000);
    else {badBuilderJob=null;localStorage.setItem('nebulah-badbuilder-job','');if(result.state==='complete')await refreshUsbInventory();}
  }catch(error){$('badbuilder-status').textContent=error.message||'BadBuilder status unavailable.';}
}
if(badBuilderAvailable)$('badbuilder-form').onsubmit=event=>{event.preventDefault();task(async()=>{
  const request=badBuilderRequest();
  const result=await api('badbuilder/web/start',request);
  badBuilderJob=result.job_id;localStorage.setItem('nebulah-badbuilder-job',badBuilderJob);
  $('badbuilder-start').disabled=true;await refreshBadBuilderStatus();
});};
let usbToolsPending=null;
function refreshUsbTools(){return usbToolsPending ||= Promise.all([refreshUsbInventory(),refreshBadBuilderStatus()]).finally(()=>{usbToolsPending=null;});}
if(badBuilderAvailable)renderBadBuilderLaunch();
