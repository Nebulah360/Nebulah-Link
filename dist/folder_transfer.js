'use strict';
const folderStatus=message=>{$('folder-transfer-status').textContent=message;};
const consoleFolder=path=>path.replace(/\\?$/,'\\');
function folderName(name,file=false){
  if(typeof name!=='string'||name.length>42||!name||name==='.'||name==='..'||/[\\/\x00-\x1f:"<>|?*]/.test(name))throw Error('Folder contains an unsupported console name.');
  if(file&&(name.length>32||!/^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9]{1,8})?$/.test(name)))throw Error('Folder file names must fit the 32-character console transfer format.');
  return name;
}
async function listFolder(path){
  const result=await api('browse',{path:consoleFolder(path)});
  if(result.listing?.truncated||result.listing?.rejected)throw Error('Folder listing is incomplete; transfer stopped.');
  return result.files;
}
async function ensureFolder(path){
  const parent=consoleFolder(path.slice(0,path.lastIndexOf('\\'))),name=path.slice(path.lastIndexOf('\\')+1);
  folderName(name);
  const existing=(await listFolder(parent)).find(item=>item.name.toLowerCase()===name.toLowerCase());
  if(existing){if(!existing.directory)throw Error('A file blocks folder '+name);return;}
  await api('transfer/mkdir',{path,confirmed:true});
}
function uploadManifest(files){
  if(!files.length||files.length>200)throw Error('Choose a folder with 1–200 files.');
  let total=0,root='';const seen=new Set(),manifest=[];
  for(const file of files){
    const parts=file.webkitRelativePath.split('/');
    if(parts.length<2||parts.length>9)throw Error('Folder depth limit is eight.');
    parts.forEach((part,index)=>folderName(part,index===parts.length-1));
    if(!root)root=parts[0];
    if(parts[0]!==root)throw Error('Choose one PC folder.');
    const key=parts.join('\\').toLowerCase();if(seen.has(key))throw Error('Case-insensitive filename collision.');seen.add(key);
    if(file.size>128*1024*1024)throw Error('A file exceeds the 128 MiB limit.');
    total+=file.size;if(total>512*1024*1024)throw Error('Folder exceeds the 512 MiB limit.');
    manifest.push({file,parts});
  }
  return manifest;
}
async function uploadFolder(files,destination){
  if(!connected||!destination)throw Error('Connect and select a console destination folder.');
  const manifest=uploadManifest(files),base=consoleFolder(destination),made=new Set();
  await listFolder(base);
  let done=0;
  for(const {file,parts} of manifest){
    let folder=base;
    for(const part of parts.slice(0,-1)){
      folder+=part;
      if(!made.has(folder.toLowerCase())){await ensureFolder(folder);made.add(folder.toLowerCase());}
      folder+='\\';
    }
    const path=folder+parts.at(-1);
    if((await listFolder(folder)).some(item=>item.name.toLowerCase()===parts.at(-1).toLowerCase()))throw Error('Destination exists: '+path);
    folderStatus('Uploading '+(done+1)+' of '+manifest.length+' · '+parts.join('/'));
    if(!await runTransfer('upload',path,file))break;
    done++;if(transferCancel)break;
  }
  folderStatus('Verified '+done+' of '+manifest.length+' files. No existing files were replaced.');
}
async function consoleManifest(root){
  const queue=[{path:consoleFolder(root),parts:[],depth:0}],files=[];let total=0,visited=0;
  while(queue.length){
    if(++visited>2000)throw Error('Folder contains too many directories.');
    const current=queue.shift();
    for(const item of await listFolder(current.path)){
      folderName(item.name);
      if(item.directory){if(current.depth>=8)throw Error('Folder depth limit is eight.');queue.push({path:current.path+item.name+'\\',parts:[...current.parts,item.name],depth:current.depth+1});}
      else{if(item.size>128*1024*1024)throw Error('A file exceeds the 128 MiB limit.');total+=item.size;if(total>512*1024*1024)throw Error('Folder exceeds the 512 MiB limit.');files.push({path:current.path+item.name,parts:[...current.parts,item.name]});if(files.length>200)throw Error('Folder exceeds 200 files.');}
    }
  }
  return files;
}
async function downloadFolder(root,destination){
  if(!connected||!root)throw Error('Connect and choose a console folder.');
  const files=await consoleManifest(root);
  const name=folderName(root.replace(/\\$/,'').split('\\').at(-1));
  let dir=destination;
  try{dir=await destination.getDirectoryHandle(name);}catch(error){if(error.name!=='NotFoundError')throw error;dir=await destination.getDirectoryHandle(name,{create:true});}
  let done=0;
  for(const item of files){
    let parent=dir;
    for(const part of item.parts.slice(0,-1))parent=await parent.getDirectoryHandle(part,{create:true});
    const leaf=item.parts.at(-1);
    try{await parent.getFileHandle(leaf);throw Error('PC destination exists: '+leaf);}catch(error){if(error.name!=='NotFoundError')throw error;}
    folderStatus('Downloading '+(done+1)+' of '+files.length+' · '+item.parts.join('/'));
    const result=await runTransfer('download',item.path,null,async blob=>{
      const handle=await parent.getFileHandle(leaf,{create:true});
      const writer=await handle.createWritable();
      try{await writer.write(blob);await writer.close();}catch(error){await writer.abort();throw error;}
    });
    if(!result)break;
    done++;if(transferCancel)break;
  }
  folderStatus('Verified '+done+' of '+files.length+' files in the selected PC folder.');
}
if($('folder-upload-button'))$('folder-upload-button').onclick=()=>task(()=>uploadFolder([...$('folder-upload-files').files],$('folder').value));
if($('folder-download-button'))$('folder-download-button').onclick=async()=>{
  if(typeof showDirectoryPicker!=='function'){folderStatus('This browser cannot choose a PC folder. Use Chrome or Edge.');return;}
  try{const destination=await showDirectoryPicker({mode:'readwrite'});await task(()=>downloadFolder($('folder-download-path').value.trim(),destination));}
  catch(error){if(error.name!=='AbortError')folderStatus(error.message);}
};
