'use strict';
async function validateAndLaunch(path){
  if(!confirm('Inspect this XEX again and launch it? Plugin files and failed checks do not launch.'))return;
  const value=await api('validate',{path});
  if(!value.ticket)throw Error(value.launch_block_reason||'Inspection did not authorize launch.');
  const result=await api('launch',{ticket:value.ticket});
  if(result.accepted!==true)throw Error('Launch was not accepted.');
  $('power-status').textContent='Launch accepted. Check the console.';
}
async function consolePower(mode){
  const label={warm:'warm reboot',cold:'cold reboot',shutdown:'shutdown'}[mode];
  if(!confirm('Confirm console '+label+'?'))return;
  const result=await api('console/power',{mode,confirmed:true});
  if(result.accepted!==true)throw Error('Power command was not confirmed.');
  connected=false;
  $('connection').textContent='Reconnect required after '+label+'.';
  $('power-status').textContent='Accepted. Reconnect when the console is back.';
}
for(const mode of ['warm','cold','shutdown']){
  const button=$('power-'+mode);
  if(button)button.onclick=()=>task(()=>consolePower(mode));
}
if($('console-notify-form'))$('console-notify-form').onsubmit=event=>{
  event.preventDefault();
  task(async()=>{
    const message=$('console-notify-message').value;
    if(!/^[ -~]{1,80}$/.test(message))throw Error('Use 1–80 printable ASCII characters.');
    const result=await api('console/notify',{message,icon:14,confirmed:true});
    if(result.accepted!==true)throw Error('Xbox notification was not confirmed.');
    $('console-notify-result').textContent='Command accepted. Check the Xbox screen.';
  });
};
const controllerPad=$('controller-pad');
if(controllerPad){
  for(const name of ['up','down','left','right','a','b','x','y','lb','rb','start','back']){
    const button=document.createElement('button');
    button.type='button';button.className='secondary';button.textContent=name.toUpperCase();
    button.onclick=()=>task(async()=>{
      const result=await api('controller/pulse',{button:name});
      $('controller-status').textContent=result.accepted?'Pulse accepted: '+name+'.':'Pulse was not confirmed.';
    });
    controllerPad.append(button);
  }
}
async function refreshLaunchIni(){
  const result=await api('console/launch-ini');
  const list=$('launch-ini-list');
  list.replaceChildren();
  if(result.state!=='verified'){
    $('launch-ini-status').textContent='Active launch.ini not verified. '+(result.reason||'Check DashLaunch.');
    return;
  }
  $('launch-ini-status').textContent='Active file '+result.active_path+'. Switching changes this session. Loaded plugins stay loaded.';
  for(const item of result.candidates||[]){
    const row=document.createElement('div');
    const label=document.createElement('span');
    label.className='mono';
    label.textContent=(item.active?'Active: ':'')+item.path;
    row.append(label);
    if(!item.active){
      const button=document.createElement('button');
      button.type='button';button.className='secondary';button.textContent='Switch';
      button.onclick=()=>task(async()=>{
        if(!confirm('Use '+item.path+' as the active launch.ini for this session?'))return;
        await api('console/launch-ini-switch',{path:item.path,sha256:item.sha256,confirmed:true});
        $('launch-ini-status').textContent='Switch confirmed for this session.';
        await refreshLaunchIni();
      });
      row.append(button);
    }
    list.append(row);
  }
}
if($('launch-ini-refresh'))$('launch-ini-refresh').onclick=()=>task(refreshLaunchIni);
if($('launch-plugin-refresh'))$('launch-plugin-refresh').onclick=()=>task(async()=>{
  const result=await api('console/launch-ini/plugins');
  const host=$('launch-plugin-slots');
  host.replaceChildren();
  const slots=result.slots||[];
  $('launch-plugin-status').textContent=(result.note||'Plugin slots read.')+' Active '+ (result.active_path||'');
  const inputs=[];
  for(const slot of slots){
    const label=document.createElement('label');
    label.textContent='Plugin '+slot.number+' ('+slot.module_observation+')';
    const input=document.createElement('input');
    input.value=slot.path||'';
    input.maxLength=512;
    input.spellcheck=false;
    label.append(input);
    host.append(label);
    inputs.push(input);
  }
  if(inputs.length!==5)return;
  const save=document.createElement('button');
  save.type='button';save.className='secondary';save.textContent='Review and save plugin slots';
  save.onclick=()=>task(async()=>{
    const preview=await api('console/launch-ini/plugins/preview',{slots:inputs.map(input=>input.value.trim())});
    const lines=(preview.changes||[]).map(change=>'Slot '+change.slot+': '+(change.before||'(empty)')+' -> '+(change.after||'(empty)')).join('\n');
    if(!confirm((lines||'No listed changes.')+'\n\nSave these slots? A backup stays on the console. Changes apply on the next boot.'))return;
    const saved=await api('console/launch-ini/plugins/save',{preview:preview.preview,confirmed:true});
    $('launch-plugin-status').textContent=saved.state==='saved'?'Plugin slots saved and read back. '+(saved.sha256||''):(saved.reason||'Save was not confirmed.');
  });
  host.append(save);
});
let measuredPlugin=null;
function clearMeasuredPlugin(){measuredPlugin=null;if($('plugin-load'))$('plugin-load').disabled=true;}
async function measurePlugin(){
  const path=$('plugin-path').value.trim();
  if(!path)throw Error('Enter a console XEX path.');
  clearMeasuredPlugin();
  const value=await api('games/inspect',{path});
  const plugin=value.plugin===true&&typeof value.hash==='string';
  measuredPlugin=plugin?{path,hash:value.hash}:null;
  $('plugin-load').disabled=!plugin;
  $('plugin-measure-result').textContent=plugin?'Plugin module. SHA-256 '+value.hash+'. Confirm load to send it.':'This XEX is not a plugin module. It was not loaded.';
}
async function useAsModule(path){
  $('plugin-path').value=path;
  selectTab('console');
  await measurePlugin();
}
async function refreshModules(){
  const caps=await api('plugins/capabilities');
  $('plugin-capability').textContent=caps.reason||'Module control checked.';
  const value=await api('plugins/list');
  const host=$('module-list');
  host.replaceChildren();
  const items=(value.console&&value.console.items)||[];
  if(!items.length){host.textContent='No modules reported.';return;}
  for(const item of items){
    const row=document.createElement('div');row.className='file';
    const label=document.createElement('span');label.className='name';label.textContent=item.name;row.append(label);
    if(caps.component){
      try{
        const managed=await api('plugins/managed-state',{name:item.name});
        if(managed.state==='managed'){
          const unload=document.createElement('button');
          unload.type='button';unload.className='secondary';unload.textContent='Unload';
          unload.onclick=()=>task(async()=>{
            if(!confirm('Unload '+item.name+' through Companion? This can run once for that load.'))return;
            const result=await api('plugins/unload',{name:item.name,confirmed:true,route:'component'});
            $('plugin-measure-result').textContent=result.state==='unloaded'?item.name+' unloaded.':'Unload was not confirmed.';
            await refreshModules();
          });
          row.append(unload);
        }
      }catch{/* A name that is not a module filename stays listed without an unload control. */}
    }
    host.append(row);
  }
}
if($('plugin-path'))$('plugin-path').oninput=()=>{clearMeasuredPlugin();$('plugin-measure-result').textContent='Measure again before load.';};
if($('plugin-measure'))$('plugin-measure').onclick=()=>task(measurePlugin);
if($('modules'))$('modules').onclick=()=>task(refreshModules);
if($('plugin-load-form'))$('plugin-load-form').onsubmit=event=>{
  event.preventDefault();
  task(async()=>{
    if(!measuredPlugin||measuredPlugin.path!==$('plugin-path').value.trim())throw Error('Measure this path again before load.');
    if(!confirm('Load '+measuredPlugin.path+'? It must match a reviewed build.'))return;
    const result=await api('plugins/load',{path:measuredPlugin.path,sha256:measuredPlugin.hash,confirmed:true,route:'neighborhood'});
    clearMeasuredPlugin();
    $('plugin-measure-result').textContent=(result.name||'Module')+' loaded as '+result.state+'.';
    await refreshModules();
  });
};
