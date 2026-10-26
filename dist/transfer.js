'use strict';
class FileHash {
  constructor(){this.h=new Uint32Array([0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]);this.buffer=new Uint8Array(64);this.used=0;this.length=0;}
  update(bytes){this.length+=bytes.length;for(let i=0;i<bytes.length;){const n=Math.min(64-this.used,bytes.length-i);this.buffer.set(bytes.subarray(i,i+n),this.used);this.used+=n;i+=n;if(this.used===64){this.block(this.buffer);this.used=0;}}return this;}
  block(bytes){const k=FileHash.K,w=new Uint32Array(64),rotate=(x,n)=>(x>>>n)|(x<<(32-n));for(let i=0;i<16;i++)w[i]=(bytes[4*i]<<24)|(bytes[4*i+1]<<16)|(bytes[4*i+2]<<8)|bytes[4*i+3];for(let i=16;i<64;i++){const a=w[i-15],b=w[i-2];w[i]=(w[i-16]+(rotate(a,7)^rotate(a,18)^(a>>>3))+w[i-7]+(rotate(b,17)^rotate(b,19)^(b>>>10)))>>>0;}let [a,b,c,d,e,f,g,h]=this.h;for(let i=0;i<64;i++){const t1=(h+(rotate(e,6)^rotate(e,11)^rotate(e,25))+((e&f)^(~e&g))+k[i]+w[i])>>>0,t2=((rotate(a,2)^rotate(a,13)^rotate(a,22))+((a&b)^(a&c)^(b&c)))>>>0;h=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0;}[a,b,c,d,e,f,g,h].forEach((v,i)=>this.h[i]=(this.h[i]+v)>>>0);}
  hex(){const bits=this.length*8;this.buffer[this.used++]=128;if(this.used>56){this.buffer.fill(0,this.used);this.block(this.buffer);this.used=0;}this.buffer.fill(0,this.used,56);const view=new DataView(this.buffer.buffer);view.setUint32(56,Math.floor(bits/4294967296));view.setUint32(60,bits>>>0);this.block(this.buffer);return Array.from(this.h,v=>v.toString(16).padStart(8,'0')).join('');}
}
FileHash.K=new Uint32Array([0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]);
let transferCancel=false;
function encodeBytes(bytes){let text='';for(const byte of bytes)text+=String.fromCharCode(byte);return btoa(text);}
function decodeBytes(text){return Uint8Array.from(atob(text),c=>c.charCodeAt(0));}
function reviewTransferInline(message){return new Promise(resolve=>{
  const card=document.createElement('div');
  const detail=document.createElement('p');detail.className='mono';detail.style.whiteSpace='pre-wrap';detail.textContent=message;
  const approve=document.createElement('button');approve.type='button';approve.className='primary';approve.textContent='Upload checked XEX';
  const cancel=document.createElement('button');cancel.type='button';cancel.className='secondary';cancel.textContent='Cancel upload';
  const finish=answer=>{card.remove();resolve(answer);};
  approve.onclick=()=>finish(true);cancel.onclick=()=>finish(false);
  card.append(detail,approve,cancel);$('transfer-message').after(card);
});}
if($('transfer-cancel'))$('transfer-cancel').onclick=()=>{transferCancel=true;$('transfer-message').textContent='Cancellation requested.';};
if($('upload-file'))$('upload-file').onchange=()=>{$('upload-name').value=$('upload-file').files[0]?.name||'';};
async function runTransfer(direction,path,file,saveDownload){
  transferCancel=false;$('transfer-cancel').disabled=false;$('transfer-progress').value=0;
  let state=null;const chunks=[],hash=new FileHash();
  try{
    let sha256;
    if(file){
      if(file.size>128*1024*1024)throw Error('Maximum transfer size is 128 MiB.');
      const initial=new FileHash();
      for(let offset=0;offset<file.size;offset+=1048576){
        if(transferCancel){$('transfer-message').textContent='Cancelled before upload.';return;}
        initial.update(new Uint8Array(await file.slice(offset,offset+1048576).arrayBuffer()));
      }
      sha256=initial.hex();
    }
    state=await api('transfer/start',{direction,path,size:file?.size,sha256,confirmed:direction==='upload',upload_protocol:2});
    if(direction==='upload'&&state.path!==path){
      const proposed=state.path;
      await api('transfer/cancel',{id:state.id});
      $('upload-name').value=proposed.split('\\').pop();
      $('transfer-message').textContent='Filename adjusted to '+proposed+'. Submit upload again with this exact name.';
      return;
    }
    while(state.offset<state.size){
      if(transferCancel){state=await api('transfer/cancel',{id:state.id});$('transfer-message').textContent='Cancelled.';return;}
      const payload={id:state.id,offset:state.offset};
      if(file)payload.content=encodeBytes(new Uint8Array(await file.slice(state.offset,state.offset+state.chunk_size).arrayBuffer()));
      state=await api('transfer/chunk',payload);
      if(direction==='download'){const bytes=decodeBytes(state.content);hash.update(bytes);chunks.push(bytes);}
      $('transfer-progress').value=state.size?100*state.offset/state.size:100;
      $('transfer-message').textContent=(direction==='upload'?'Staging on PC':'Download')+' · '+state.offset+' / '+state.size;
    }
    do{
      if(transferCancel){state=await api('transfer/cancel',{id:state.id});$('transfer-message').textContent='Cancelled before finalizing.';return;}
      if(direction==='upload'&&state.phase==='checked'){
        const report=state.checkpoint;
        if(!report||!state.consent||report.sha256!==sha256||report.size!==file?.size||typeof report.note!=='string')throw Error('Executable checkpoint report missing. Update the local bridge.');
        const message='Staged executable\nBytes: '+report.size+'\nReview: '+report.registry.status+'\nSHA-256: '+report.sha256+'\n'+report.note+'\n\nUpload these bytes to '+path+'?';
        $('transfer-message').textContent=message;
        if(!await reviewTransferInline(message)){state=await api('transfer/cancel',{id:state.id});$('transfer-message').textContent='Executable upload cancelled before console write.';return;}
        state=await api('transfer/approve',{id:state.id,consent:state.consent,confirmed:true});
      }
      state=await api('transfer/finish',{id:state.id});
    }while(state.state!=='completed');
    if(direction==='download'){
      if(hash.hex()!==state.sha256)throw Error('Download hash mismatch. File was not offered for saving.');
      if(saveDownload)await saveDownload(new Blob(chunks));
      else{const url=URL.createObjectURL(new Blob(chunks)),a=document.createElement('a');a.href=url;a.download=path.split('\\').pop();document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);}
    }
    $('transfer-progress').value=100;
    $('transfer-message').textContent='Completed · SHA-256 '+state.sha256;
    return state;
  }catch(error){
    if(state){try{state=await api('transfer/cancel',{id:state.id});}catch(cancelError){}}
    $('transfer-message').textContent='Transfer failed. '+error.message;
    throw error;
  }finally{$('transfer-cancel').disabled=true;}
}
if($('upload-form'))$('upload-form').onsubmit=event=>{
  event.preventDefault();
  task(async()=>{
    const file=$('upload-file').files[0],name=$('upload-name').value.trim();
    if(!connected||!file||!$('folder').value||!$('upload-confirm').checked)throw Error('Connect, choose a destination folder, and confirm the upload.');
    if(/[\\/\x00-\x1f]/.test(name)||name==='.'||name==='..')throw Error('Use a filename without path separators or control characters.');
    await runTransfer('upload',$('folder').value.replace(/\\?$/,'\\')+name,file);
    $('upload-confirm').checked=false;
  });
};
