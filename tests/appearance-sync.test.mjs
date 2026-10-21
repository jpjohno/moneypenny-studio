import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
const source=await readFile(new URL('../static/studio.js',import.meta.url),'utf8');
const sync=source.slice(source.indexOf('async function syncAppearance('),source.indexOf('\nfunction saveAppearance()'));
function harness(){
 const nodes=Object.fromEntries(['hairTone','eyeTone','blouseColor','lightingLook','lightBrightness','appearanceState'].map(id=>[id,{value:'old',textContent:''}]));
 const saved={hairTone:'lightblonde',eyeTone:'brightblue',blouseColor:'ivory',lightingLook:'neutral',lightBrightness:'1.15'},requests=[],effects=[];
 let fail=false;
 const context={head:{armature:{}},wardrobe:{setPalette:v=>effects.push(['blouse',v])},$:id=>nodes[id],
  setLook:()=>effects.push(['light']),setHairTone:(_,v)=>effects.push(['hair',v]),setEyeTone:(_,v)=>effects.push(['eyes',v]),
  api(){throw new Error('Reading must never call the POST helper');},fetch:async(url,options)=>{requests.push({url,options});return {ok:!fail,json:async()=>saved};},
 };
 vm.createContext(context);vm.runInContext(`let appearanceSnapshot='';const appearanceIds=${JSON.stringify(Object.keys(saved))};${sync};globalThis.sync=syncAppearance;`,context);
 return {nodes,saved,requests,effects,context,setFail:value=>fail=value};
}
test('shared appearance is read with GET and re-applied after an older saved persona opens',async()=>{
 const h=harness();await h.context.sync();
 assert.deepEqual(h.requests,[{url:'/api/appearance',options:undefined}]);
 assert.equal(h.nodes.hairTone.value,'lightblonde');assert.equal(h.nodes.eyeTone.value,'brightblue');
 assert.ok(h.effects.some(([kind,value])=>kind==='eyes'&&value==='brightblue'));
 h.nodes.hairTone.value='darkblonde';h.nodes.blouseColor.value='petrol';
 await h.context.sync(true);
 assert.equal(h.nodes.hairTone.value,'lightblonde');assert.equal(h.nodes.blouseColor.value,'ivory');
 assert.equal(h.nodes.appearanceState.textContent,'Appearance shared with JJRVIS');
});
test('a failed read preserves current choices and a later retry really applies them',async()=>{
 const h=harness();h.setFail(true);await h.context.sync();
 assert.equal(h.nodes.hairTone.value,'old');assert.equal(h.effects.length,0);
 assert.match(h.nodes.appearanceState.textContent,/unavailable/);
 h.setFail(false);await h.context.sync();assert.equal(h.nodes.hairTone.value,'lightblonde');
});
