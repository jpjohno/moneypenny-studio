'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const sourcePath=path.join(__dirname,'../spoken-reply.js');
const load=vm.runInThisContext('(function(module){'+fs.readFileSync(sourcePath,'utf8')+'\n;return module.exports;})',{filename:sourcePath});
const {create,boundary}=load({exports:{}});
const tick=()=>new Promise(setImmediate);
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
test('first audio plays before final text and completes only after playback drains',async()=>{
 const log=[],first=deferred(),last=deferred();let done=false;
 const s=create({prepare:async text=>{log.push(['prepare',text]);return text;},play:async(text,{onStarted})=>{onStarted();log.push(['play',text]);await (text.startsWith('Ready')?first.promise:last.promise);},finish:()=>log.push(['finish']),onDone:()=>done=true});
 s.update('Ready when you are.');await tick();assert.deepEqual(log,[['prepare','Ready when you are.'],['play','Ready when you are.']]);assert.equal(done,false);
 s.update('Ready when you are. What shall we work on?',true);await tick();assert.equal(log.at(-1)[0],'prepare');assert.equal(log.filter(x=>x[0]==='play').length,1);
 first.resolve();await tick();assert.equal(log.at(-1)[0],'play');assert.equal(done,false);last.resolve();assert.equal((await s.done).state,'complete');assert.equal(log.at(-1)[0],'finish');
});
test('one phrase is prefetched and each phrase is prepared and played once in order',async()=>{
 const texts=['The first sentence.','The second sentence.','The third sentence.'],prepared=[],played=[],gates=texts.map(deferred);let index=0;
 const s=create({prepare:async text=>{prepared.push(text);return text;},play:async(text,{onStarted})=>{onStarted();played.push(text);await gates[index++].promise;}});
 s.update(texts.join(' '),true);await tick();assert.deepEqual(prepared,texts.slice(0,2));assert.deepEqual(played,texts.slice(0,1));
 gates[0].resolve();await tick();assert.deepEqual(prepared,texts);assert.deepEqual(played,texts.slice(0,2));gates[1].resolve();await tick();gates[2].resolve();await s.done;assert.deepEqual(prepared,texts);assert.deepEqual(played,texts);
});
test('new streamed text cannot start another prepare while the first phrase is preparing',async()=>{
 const first='The first sentence.',second='The second sentence.',prepareFirst=deferred(),playFirst=deferred(),prepared=[],played=[];let active=0,maxActive=0;
 const s=create({prepare:async text=>{prepared.push(text);active++;maxActive=Math.max(maxActive,active);try{if(text===first)await prepareFirst.promise;return text;}finally{active--;}},play:async(text,{onStarted})=>{onStarted();played.push(text);if(text===first)await playFirst.promise;}});
 s.update(first);await tick();s.update(first+' '+second);await tick();s.update(first+' '+second,true);await tick();
 assert.deepEqual(prepared,[first]);assert.deepEqual(played,[]);assert.equal(maxActive,1);
 prepareFirst.resolve();await tick();assert.deepEqual(prepared,[first,second]);assert.deepEqual(played,[first]);assert.equal(maxActive,1,'Prefetch begins only after the first generation finishes');
 playFirst.resolve();assert.equal((await s.done).state,'complete');assert.deepEqual(played,[first,second]);
});
test('text arriving while a prefetched prepare is awaited cannot start a third generation',async()=>{
 const [first,second,third]=['The first sentence.','The second sentence.','The third sentence.'],prepareSecond=deferred(),playFirst=deferred(),playSecond=deferred(),prepared=[],played=[];let active=0,maxActive=0;
 const s=create({prepare:async text=>{prepared.push(text);active++;maxActive=Math.max(maxActive,active);try{if(text===second)await prepareSecond.promise;return text;}finally{active--;}},play:async(text,{onStarted})=>{onStarted();played.push(text);if(text===first)await playFirst.promise;if(text===second)await playSecond.promise;}});
 s.update(first+' '+second);await tick();assert.deepEqual(prepared,[first,second]);assert.deepEqual(played,[first]);
 playFirst.resolve();await tick();s.update([first,second,third].join(' '),true);await tick();
 assert.deepEqual(prepared,[first,second]);assert.deepEqual(played,[first]);assert.equal(maxActive,1,'The awaited prefetch still owns the only generation slot');
 prepareSecond.resolve();await tick();assert.deepEqual(prepared,[first,second,third]);assert.deepEqual(played,[first,second]);assert.equal(maxActive,1);
 playSecond.resolve();assert.equal((await s.done).state,'complete');assert.deepEqual(played,[first,second,third]);
});
test('cancel stops preparation ownership and never starts queued or stale audio',async()=>{
 const gate=deferred(),played=[],signals=[];
 const s=create({prepare:async(text,signal)=>{signals.push(signal);await gate.promise;return text;},play:async text=>played.push(text)});
 s.update('The first sentence. The second sentence.',true);await tick();s.cancel();gate.resolve();await tick();assert.equal((await s.done).state,'cancelled');assert.equal(signals[0].aborted,true);assert.deepEqual(played,[]);
});
test('cumulative reset and excessive text fail closed without repeating earlier speech',async()=>{
 const s=create({prepare:async text=>text,play:async()=>{}});s.update('The first sentence.');assert.throws(()=>s.update('A different reply.'),/changed/);assert.equal((await s.done).state,'cancelled');
 const large=create({prepare:async()=>{},play:async()=>{}});assert.throws(()=>large.update('x'.repeat(24001)),/too long/);assert.equal((await large.done).state,'cancelled');
});
test('phrase boundaries preserve decimals and bound long words',()=>{
 const text='The measurement is 1.25 metres. Next sentence.';assert.equal(text.slice(0,boundary(text,true,false)),'The measurement is 1.25 metres.');assert.equal(boundary('x'.repeat(500),true,false),48);assert.equal(boundary('A short reply',true,false),0);assert.equal(boundary('A short reply',true,true),13);
});
test('a preparation failure produces one error and no playback or completion',async()=>{
 let errors=0,completed=0,played=0;const s=create({prepare:async()=>{throw new Error('Voice unavailable');},play:async()=>played++,onError:()=>errors++,onDone:()=>completed++});s.update('A complete sentence.',true);assert.equal((await s.done).state,'error');assert.equal(errors,1);assert.equal(completed,0);assert.equal(played,0);
});
test('Stop during final audio drain never completes the cancelled reply',async()=>{
 const gate=deferred();let finishing=false,completed=0,errors=0;
 const s=create({prepare:async text=>text,play:async(_,{onStarted})=>onStarted(),finish:async()=>{finishing=true;await gate.promise;},onDone:()=>completed++,onError:()=>errors++});
 s.update('A complete sentence.',true);await tick();assert.equal(finishing,true);
 s.cancel();assert.equal((await s.done).state,'cancelled');gate.resolve();await tick();
 assert.equal(completed,0);assert.equal(errors,0);assert.equal(s.signal.aborted,true);
});
