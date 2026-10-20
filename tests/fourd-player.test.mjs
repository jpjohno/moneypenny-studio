import test from 'node:test';
import assert from 'node:assert/strict';
import {FourDPlayer,createGLTFFrameLoader,disposeThreeFrame} from '../static/fourd-player.js';

const turn=()=>new Promise(resolve=>setImmediate(resolve));
const sequence=(count=1000)=>({fps:10,frames:Array.from({length:count},(_,index)=>`frame-${index}.glb`)});
function deferred(){let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};}

test('only a rolling bounded window of recorded frames is decoded',async()=>{
 const loaded=[],shown=[],disposed=[],live=new Set();let peak=0;
 const player=new FourDPlayer(sequence(),{
  loadFrame:async(_,{index})=>{loaded.push(index);const asset={index};live.add(asset);peak=Math.max(peak,live.size);return asset;},
  showFrame:(asset,index)=>{if(asset)shown.push(index);},
  disposeFrame:asset=>{assert.ok(live.delete(asset),'resource disposed twice');disposed.push(asset.index);},
 });
 await player.play();await turn();
 assert.deepEqual(loaded,[0,1,2]);assert.equal(player.status().cached,3);
 for(let index=1;index<=12;index++){player.update(.10001);await turn();assert.ok(player.status().cached<=3);}
 assert.equal(player.frame,12);assert.ok(loaded.length<18,'player fetched beyond the rolling window');
 assert.ok(peak<=3,`decoded resource peak ${peak}`);assert.ok(disposed.length>=10);
 player.dispose();assert.equal(live.size,0);assert.equal(player.status().cached,0);
 assert.equal(shown.at(-1),12);
});

test('rapid seeks cancel stale work and dispose late decoders before loading another',async()=>{
 const calls=[],shown=[],released=[];
 const player=new FourDPlayer(sequence(12),{
  loadFrame:(_,{index,signal})=>{const pending=deferred();calls.push({index,signal,...pending});return pending.promise;},
  showFrame:(asset,index)=>{if(asset)shown.push(index);},disposeFrame:asset=>released.push(asset.index),
 });
 const first=player.seek(0),second=player.seek(8);
 assert.equal(await first,false);assert.equal(calls.length,1);assert.equal(calls[0].signal.aborted,true);
 calls[0].resolve({index:0});await turn();assert.deepEqual(released,[0]);assert.equal(calls[1].index,8);
 const third=player.seek(2);assert.equal(await second,false);assert.equal(calls[1].signal.aborted,true);
 calls[1].resolve({index:8});await turn();assert.deepEqual(released,[0,8]);assert.equal(calls[2].index,2);
 calls[2].resolve({index:2});assert.equal(await third,true);await turn();
 assert.deepEqual(shown,[2]);assert.equal(player.frame,2);assert.equal(player.status().cached,1);
 player.dispose();assert.deepEqual(released,[0,8,2]);
});

test('pausing keeps the displayed frame and stops background prefetch',async()=>{
 const calls=[],released=[];
 const player=new FourDPlayer(sequence(20),{
  loadFrame:(_,{index,signal})=>{const pending=deferred();calls.push({index,signal,...pending});return pending.promise;},
  disposeFrame:asset=>released.push(asset.index),
 });
 const ready=player.play();calls[0].resolve({index:0});assert.equal(await ready,true);await turn();
 assert.equal(calls[1].index,1);player.pause();assert.equal(calls[1].signal.aborted,true);
 calls[1].resolve({index:1});await turn();player.update(20);await turn();
 assert.equal(calls.length,2);assert.equal(player.frame,0);assert.equal(player.status().cached,1);
 assert.deepEqual(released,[1]);assert.equal(player.playing,false);player.dispose();
 assert.deepEqual(released,[1,0]);
});

test('stop releases visible and pending resources; disposal prevents further use',async()=>{
 const pending=deferred(),shown=[],released=[];let loads=0;
 const player=new FourDPlayer(sequence(5),{
  loadFrame:async(_,{index})=>{loads++;return index===0?{index}:pending.promise;},
  showFrame:(asset,index)=>shown.push(index),disposeFrame:asset=>released.push(asset.index),
 });
 await player.play();await turn();player.stop();assert.equal(player.frame,null);
 assert.equal(shown.at(-1),null);assert.deepEqual(released,[0]);
 pending.resolve({index:1});await turn();assert.deepEqual(released,[0,1]);assert.equal(loads,2);
 assert.equal(player.status().cached,0);player.dispose();
 assert.throws(()=>player.play(),/disposed/);assert.throws(()=>player.seek(0),/disposed/);
});

test('load failures settle a seek once and allow an explicit retry',async()=>{
 let attempts=0;const errors=[];
 const player=new FourDPlayer(sequence(4),{
  loadFrame:async(_,{index})=>{if(++attempts===1)throw new Error('offline');return {index};},
  disposeFrame:()=>{},onError:value=>errors.push(value),
 });
 assert.equal(await player.seek(2),false);await turn();await turn();
 assert.equal(attempts,1);assert.equal(errors.length,1);assert.equal(errors[0].index,2);
 assert.equal(await player.seek(2),true);assert.equal(attempts,2);player.dispose();
});

test('a slow decoder does not chase targets forever or blank the last frame',async()=>{
 const calls=[],shown=[];
 const player=new FourDPlayer(sequence(30),{prefetch:0,
  loadFrame:(_,{index})=>{const pending=deferred();calls.push({index,...pending});return pending.promise;},
  showFrame:(asset,index)=>{if(asset)shown.push(index);},disposeFrame:()=>{},
 });
 const ready=player.play();calls[0].resolve({index:0});await ready;await turn();
 player.update(.1);await turn();assert.equal(calls[1].index,1);
 for(let i=0;i<30;i++)player.update(.1);
 assert.equal(player.requested,1);assert.equal(player.frame,0);assert.equal(player.status().buffering,true);
 calls[1].resolve({index:1});await turn();assert.deepEqual(shown,[0,1]);
 player.update(.1);await turn();assert.equal(calls[2].index,2);player.dispose();calls[2].resolve({index:2});await turn();
});

test('playback skips late frames, loops when requested, and holds the final frame otherwise',async()=>{
 const states=[];
 const player=new FourDPlayer(sequence(4),{prefetch:0,loop:false,loadFrame:async(_,{index})=>({index}),disposeFrame:()=>{},onState:state=>states.push(state)});
 await player.play();player.update(.31);await turn();assert.equal(player.frame,3);
 player.update(.2);assert.equal(player.playing,false);assert.equal(player.frame,3);assert.equal(states.at(-1).playing,false);
 await player.play();assert.equal(player.frame,0);assert.equal(player.playing,true);
 player.loop=true;await player.seek(0);await player.play();player.update(.51);await turn();assert.equal(player.frame,1);
 player.dispose();
});

test('invalid sequence and seek inputs are rejected before loading',()=>{
 const loadFrame=async()=>({});
 assert.throws(()=>new FourDPlayer({fps:0,frames:['a.glb']},{loadFrame}),/sequence/);
 assert.throws(()=>new FourDPlayer({fps:30,frames:[]},{loadFrame}),/sequence/);
 assert.throws(()=>new FourDPlayer({fps:30,frames:[{}]},{loadFrame}),/URL/);
 const player=new FourDPlayer(sequence(2),{loadFrame});
 for(const value of [-1,2,.5,NaN])assert.throws(()=>player.seek(value),/range/);
 player.dispose();
});

test('GLTF fetch honours cancellation and disposes a parse that finishes late',async()=>{
 const pending=deferred(),controller=new AbortController();let disposed=0;
 const scene={traverse:visit=>visit({geometry:{dispose(){disposed++;}}})};
 const loader={parseAsync:async()=>pending.promise};
 let requested;
 const load=createGLTFFrameLoader(loader,{baseURL:'http://127.0.0.1:8090/review/',fetch:async(url,{signal})=>{
  requested={url,signal};return {ok:true,arrayBuffer:async()=>new ArrayBuffer(8)};
 }});
 const work=load({url:'frame-0.glb'},{signal:controller.signal});await turn();controller.abort();pending.resolve({scene});
 await assert.rejects(work,{name:'AbortError'});assert.equal(disposed,1);
 assert.equal(requested.url,'http://127.0.0.1:8090/review/frame-0.glb');assert.equal(requested.signal,controller.signal);
});

test('Three frame cleanup releases shared-within-frame resources exactly once',()=>{
 const calls={geometry:0,material:0,texture:0,image:0,skeleton:0,detach:0};
 const image={close(){calls.image++;}},texture={isTexture:true,source:{data:image},dispose(){calls.texture++;}};
 const geometry={dispose(){calls.geometry++;}},material={map:texture,normalMap:texture,dispose(){calls.material++;}},skeleton={dispose(){calls.skeleton++;}};
 const scene={traverse:visit=>{visit({geometry,material,skeleton});visit({geometry,material:[material],skeleton});},removeFromParent(){calls.detach++;}};
 disposeThreeFrame({scene});assert.deepEqual(calls,{geometry:1,material:1,texture:1,image:1,skeleton:1,detach:1});
});
