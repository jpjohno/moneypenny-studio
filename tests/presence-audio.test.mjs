import test from 'node:test';
import assert from 'node:assert/strict';
import {PresenceAudio} from '../static/presence-audio.js';
const tick=()=>new Promise(setImmediate);
function harness(){
 const events=[],decoded=[],playing=[],busy=[];
 const controller=new PresenceAudio({stopAudio:async()=>{},decode:audio=>new Promise(resolve=>decoded.push({audio,resolve})),playAudio:(audio,options)=>new Promise(resolve=>playing.push({audio,options,resolve})),setBusy:value=>busy.push(value),emit:(type,data)=>events.push({type,...data})});
 const phrase=(id,sequence,first=false,final=false)=>controller.play({requestId:id,sequence,first,final,audio:new ArrayBuffer(100)});
 return {controller,events,decoded,playing,busy,phrase};
}
test('one decoded broker WAV drives playback and acknowledges each passage before final completion',async()=>{
 const h=harness(),pending=h.phrase('reply',0,true);await tick();
 assert.equal(h.events.length,0);const actualAudio={name:'the exact decoded WAV'};h.decoded[0].resolve(actualAudio);await tick();
 assert.equal(h.playing[0].audio,actualAudio);h.playing[0].options.onStarted();
 assert.deepEqual(h.events[0],{type:'moneypenny-presence-speaking',requestId:'reply',sequence:0});
 h.playing[0].resolve();await pending;
 assert.deepEqual(h.events.at(-1),{type:'moneypenny-presence-idle',requestId:'reply',sequence:0,final:false});
 assert.equal(h.busy.at(-1),true,'Phrase boundaries keep the reply busy');
 await h.controller.end({requestId:'reply'});
 assert.equal(h.events.at(-1).final,true);assert.equal(h.busy.at(-1),false);
});
test('Stop and a replacement reply reject delayed old decodes and stale completion',async()=>{
 const h=harness(),old=h.phrase('old',0,true);await tick();h.controller.cancel();
 const current=h.phrase('current',0,true,true);await tick();
 h.decoded[0].resolve({old:true});await old;assert.equal(h.playing.length,0);
 h.decoded[1].resolve({current:true});await tick();h.playing[0].options.onStarted();h.playing[0].resolve();await current;
 assert.equal(h.events.every(event=>event.requestId==='current'),true);assert.equal(h.events.at(-1).final,true);
});
test('end arriving during playback waits for the actual source to finish',async()=>{
 const h=harness(),pending=h.phrase('reply',0,true);await tick();h.decoded[0].resolve({});await tick();
 await h.controller.end({requestId:'reply'});assert.equal(h.events.length,0);
 h.playing[0].options.onStarted();h.playing[0].resolve();await pending;
 assert.equal(h.events.at(-1).final,true);assert.equal(h.events.filter(event=>event.type==='moneypenny-presence-idle').length,1);
});
test('oversized or unordered audio cannot start another decoder',async()=>{
 const h=harness();await h.controller.play({requestId:'reply',sequence:0,first:true,audio:new ArrayBuffer(6_000_045)});
 await h.phrase('unknown',1,false);assert.equal(h.decoded.length,0);
});


test('phrase edge ramps are bounded and do not overlap for short audio',async()=>{
 const {connectSpeechSource}=await import('../static/presence-audio.js');
 for(const duration of [.002,.1,3]){
  const events=[],gain={gain:{setValueAtTime:(v,t)=>events.push([v,t]),linearRampToValueAtTime:(v,t)=>events.push([v,t])},connect(){}};
  const source={buffer:{duration},connect(node){assert.equal(node,gain);}};
  connectSpeechSource({currentTime:5,createGain:()=>gain},source,{});
  assert.deepEqual(events.map(x=>x[0]),[0,1,1,0]);assert.equal(events[0][1],5);assert.equal(events.at(-1)[1],5+duration);
  assert.ok(events.every((e,i)=>!i||e[1]>=events[i-1][1]));
 }
});
