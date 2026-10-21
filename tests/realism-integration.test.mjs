import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import * as THREE from 'three';
import {FourDPlayer,createGLTFFrameLoader,disposeThreeFrame} from '../static/fourd-player.js';

const source=(await readFile(new URL('../static/realism.js',import.meta.url),'utf8')).replace(/^import .*;\n/gm,'');
const turn=()=>new Promise(resolve=>setImmediate(resolve));
const deferred=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};};
const manifest=()=>({fps:15,frames:['frames/frame0000.glb','frames/frame0001.glb','frames/frame0002.glb'],metadata:{fullSequence:true},bounds:{min:[-2,0,-1],max:[2,3,1]}});

function harness({view='4d',fetchHook,parseHook}={}){
 const elements=new Map(),requests=[],players=[],assets=[],listeners={},lifecycle={};
 const element=id=>{if(!elements.has(id))elements.set(id,{textContent:'',value:'0',setAttribute(){},append(){},getBoundingClientRect:()=>({width:800,height:600})});return elements.get(id);};
 const asset=index=>{const scene=new THREE.Group(),geometry=new THREE.BoxGeometry(.4,1.6,.4);let released=0;
  geometry.addEventListener('dispose',()=>released++);scene.add(new THREE.Mesh(geometry,new THREE.MeshBasicMaterial()));
  scene.position.y=.8;const value={scene,index,get released(){return released;}};assets.push(value);return value;};
 const fetch=async(url,options={})=>{url=String(url);requests.push({url,...options});
  if(fetchHook){const response=await fetchHook(url,options);if(response)return response;}
  if(url.endsWith('manifest.json'))return {ok:true,json:async()=>manifest()};
  return {ok:true,arrayBuffer:async()=>new Uint8Array([url.endsWith('scan.glb')?200:Number(url.match(/frame(\d+)\.glb$/)?.[1])]).buffer};
 };
 class Loader{async parseAsync(bytes,base){const index=new Uint8Array(bytes)[0];return parseHook?parseHook(index,base,asset):asset(index);}}
 class Renderer{constructor(){this.domElement={};lifecycle.renderer=this;}setPixelRatio(){}setClearColor(){}setSize(){}render(){}dispose(){this.disposed=true;}}
 class Camera extends THREE.PerspectiveCamera{constructor(...args){super(...args);lifecycle.camera=this;}}
 class Controls{constructor(){this.target=new THREE.Vector3();lifecycle.controls=this;}update(){}dispose(){this.disposed=true;}}
 class Observer{constructor(){lifecycle.observer=this;}observe(){}disconnect(){this.disconnected=true;}}
 class Player extends FourDPlayer{constructor(...args){super(...args);players.push(this);}}
 const context={THREE:{...THREE,WebGLRenderer:Renderer,PerspectiveCamera:Camera},GLTFLoader:Loader,OrbitControls:Controls,FourDPlayer:Player,
  createGLTFFrameLoader:(loader,options)=>createGLTFFrameLoader(loader,{...options,fetch}),disposeThreeFrame,
  authoredNeutral:()=>({}),RigController:class{},fetch,AbortController,DOMException,URL,URLSearchParams,
  document:{hidden:false,getElementById:element,addEventListener:(name,handler)=>listeners[name]=handler},
  window:{addEventListener:(name,handler)=>listeners[name]=handler},location:{href:`http://127.0.0.1:8090/realism?view=${view}`,search:`?view=${view}`},
  performance:{now:()=>0},devicePixelRatio:1,ResizeObserver:Observer,requestAnimationFrame:()=>1,cancelAnimationFrame:()=>lifecycle.cancelled=true,
 };
 vm.runInNewContext(source,context,{filename:'realism.js'});
 return {element,requests,players,assets,listeners,lifecycle,context};
}

test('the viewer resolves frame URLs from the manifest and frames the complete performance',async()=>{
 const app=harness();await turn();
 assert.equal(app.players[0].frame,0);
 assert.equal(app.element('timeline').value,'0');assert.equal(app.element('timeline').max,'2');
 assert.match(app.element('status').textContent,/Captured performance/);
 assert.equal(app.requests[1].url,'http://127.0.0.1:8090/api/review-assets/4d/detail/frames/frame0000.glb');
 assert.equal(app.lifecycle.controls.target.y,1.5);assert.equal(app.lifecycle.camera.position.z,6.4);
 app.listeners.pagehide({persisted:false});
});

test('late old-mode parsing cannot replace a scan or overwrite its controls',async()=>{
 const late=deferred();let captured;
 const app=harness({parseHook:async(index,base,asset)=>{if(index===0){captured=asset(index);return late.promise;}return asset(index);}});
 await turn();assert.equal(app.players[0].frame,null);
 assert.equal(app.element('timeline').value,'0');
 await app.element('scanMode').onclick();
 const scanMessage=app.element('status').textContent;
 assert.match(scanMessage,/Drag to turn/);
 late.resolve(captured);await turn();
 assert.equal(captured.released,1);assert.equal(app.element('status').textContent,scanMessage);
 assert.equal(app.element('scanControls').hidden,false);assert.equal(app.element('fourDControls').hidden,true);
 app.listeners.pagehide({persisted:false});
});

test('switching modes aborts the pending manifest without showing a stale error',async()=>{
 const pending=deferred();let first=true;
 const app=harness({fetchHook:(url)=>{if(url.endsWith('manifest.json')&&first){first=false;return pending.promise;}}});
 const pendingRequest=app.requests[0];
 await app.element('scanMode').onclick();assert.equal(pendingRequest.signal.aborted,true);
 pending.reject(new Error('late network failure'));await turn();
 assert.match(app.element('status').textContent,/Drag to turn/);
 app.listeners.pagehide({persisted:false});
});

test('restart does not play a replacement mode after its seek completes',async()=>{
 const app=harness();await turn();
 const restarting=app.element('restart').onclick();
 const switching=app.element('scanMode').onclick();
 await restarting;await switching;
 assert.equal(app.players[0].disposed,true);assert.equal(app.players[0].playing,false);
 assert.match(app.element('status').textContent,/Drag to turn/);
 app.listeners.pagehide({persisted:false});
});

test('frame failures remain visible and reload recovers with a fresh player',async()=>{
 let fail=true;
 const app=harness({parseHook:async(index,base,asset)=>{if(index===1&&fail)throw new Error('bad GLB');return asset(index);}});
 await turn();app.element('timeline').value='1';await app.element('timeline').oninput();await turn();
 assert.equal(app.players[0].frame,0);assert.match(app.element('status').textContent,/could not load/);
 fail=false;await app.element('reload').onclick();
 assert.equal(app.players.length,2);assert.equal(app.players[0].disposed,true);
 assert.equal(app.players[1].frame,0);assert.match(app.element('status').textContent,/Captured performance/);
 app.listeners.pagehide({persisted:false});
});

test('leaving the page releases render resources; back-forward caching only pauses',async()=>{
 const app=harness();await turn();await app.element('play').onclick();await turn();
 app.listeners.pagehide({persisted:true});assert.equal(app.players[0].playing,false);
 assert.equal(app.players[0].disposed,false);assert.equal(app.lifecycle.renderer.disposed,undefined);
 app.listeners.pagehide({persisted:false});
 assert.equal(app.players[0].disposed,true);assert.equal(app.lifecycle.renderer.disposed,true);
 assert.equal(app.lifecycle.controls.disposed,true);assert.equal(app.lifecycle.observer.disconnected,true);assert.equal(app.lifecycle.cancelled,true);
 const requests=app.requests.length;await app.element('reload').onclick();assert.equal(app.requests.length,requests);
});

 test('picture quality changes only the private recorded asset source',async()=>{
 const app=harness();await turn();
 app.element('quality').value='light';await app.element('quality').onchange();
 assert.equal(app.players[0].disposed,true);assert.equal(app.players[1].frame,0);
 assert.ok(app.requests.some(request=>request.url==='http://127.0.0.1:8090/api/review-assets/4d/manifest.json'));
 assert.ok(app.requests.some(request=>request.url==='http://127.0.0.1:8090/api/review-assets/4d/frames/frame0000.glb'));
 app.listeners.pagehide({persisted:false});
});

test('Look closer frames the current head height instead of the tallest dance pose',async()=>{
 const app=harness();await turn();
 app.element('portrait').onclick();
 assert.ok(Math.abs(app.lifecycle.controls.target.y-1.408)<1e-6);
 app.element('full').onclick();assert.equal(app.lifecycle.controls.target.y,1.5);
 app.listeners.pagehide({persisted:false});
});
