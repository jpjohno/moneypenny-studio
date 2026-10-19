'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.join(__dirname,'..'),source=fs.readFileSync(path.join(root,'theme-init.js'),'utf8');
function paint(saved,{blocked=false}={}){
 const element={dataset:{},style:{}};
 const context={document:{documentElement:element},localStorage:{getItem(){if(blocked)throw Error('Storage blocked');return saved;}},fetch(){assert.fail('Palette startup must not request any service');}};
 vm.runInNewContext(source,context);return element;
}
test('first paint and saved display preferences agree before styles load',()=>{
 for(const name of ['midnight','sky','pearl','sage','lavender']){
  const result=paint(JSON.stringify({appearance:name,appearanceChosen:true}));
  assert.equal(result.dataset.appearance,name);assert.equal(result.dataset.appearanceTone,name==='midnight'?'dark':'light');assert.equal(result.style.colorScheme,name==='midnight'?'dark':'light');
 }
});
test('new, corrupt or unavailable browser storage opens a consistent dark view',()=>{
 for(const value of [null,'null','{}','{broken','[]','{"appearance":"unknown"}','{"appearance":"sky"}'])assert.equal(paint(value).dataset.appearance,'midnight');
 assert.equal(paint(null,{blocked:true}).dataset.appearance,'midnight');assert.equal(paint('{"appearance":"slate"}').dataset.appearance,'midnight');
});
test('the public shell applies its local theme before its first stylesheet',()=>{
 const file=path.join(root,'workspace.html');if(!fs.existsSync(file))return;
 const html=fs.readFileSync(file,'utf8'),init=html.indexOf('<script src="/theme-init.js"></script>'),css=html.indexOf('<link rel="stylesheet"');
 assert.ok(init>=0&&init<css);assert.match(html,/<html[^>]*data-appearance="midnight"[^>]*data-appearance-tone="dark"/);
});
