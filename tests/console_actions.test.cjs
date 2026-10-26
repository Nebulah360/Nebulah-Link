const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');

function harness(){
  const elements=new Map();
  const get=id=>{
    if(!elements.has(id))elements.set(id,{value:'',textContent:'',disabled:false,hidden:false,onclick:null,onsubmit:null,oninput:null,replaceChildren(){this.children=[];},children:[],append(...nodes){this.children.push(...nodes);}});
    return elements.get(id);
  };
  const requests=[];
  const context={
    $:get,confirm:()=>true,selectTab(){},
    document:{createElement(){const node={type:'',className:'',textContent:'',onclick:null,children:[],append(...nodes){this.children.push(...nodes);if(nodes[0]&&nodes[0].textContent)this.textContent=nodes[0].textContent;}};return node;}},
    task:fn=>fn(),
    api:async(action,data)=>{requests.push({action,data});
      if(action==='games/inspect')return {plugin:true,hash:'ab'.repeat(32)};
      if(action==='plugins/capabilities')return {reason:'JRPC2 loading available; direct unload is paused for console validation.',component:false};
      if(action==='plugins/list')return {console:{items:[{name:'Example.xex'}]}};
      if(action==='plugins/load')return {name:'Example.xex',state:'loaded'};
      return {};}
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../dist/console_actions.js'),'utf8'),context);
  return {get,requests,context};
}

test('console module measure then load uses the measured hash',async()=>{
  const h=harness();
  h.get('plugin-path').value='HDD1:\\Apps\\Example.xex';
  await h.get('plugin-measure').onclick();
  assert.equal(h.requests[0].action,'games/inspect');
  assert.equal(h.get('plugin-load').disabled,false);
  await h.get('plugin-load-form').onsubmit({preventDefault(){}});
  const load=h.requests.find(item=>item.action==='plugins/load');
  assert.equal(load.data.path,'HDD1:\\Apps\\Example.xex');
  assert.equal(load.data.sha256,'ab'.repeat(32));
  assert.equal(load.data.confirmed,true);
  assert.equal(load.data.route,'neighborhood');
});

test('module refresh lists names and does not offer install',async()=>{
  const h=harness();
  await h.get('modules').onclick();
  assert.equal(h.requests[0].action,'plugins/capabilities');
  assert.equal(h.get('module-list').children.length,1);
  assert.equal(h.get('module-list').children[0].textContent,'Example.xex');
  assert.equal(h.requests.some(item=>item.action==='plugins/install'),false);
});
