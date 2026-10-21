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

// Evaluate gain over a sustained nonzero signal, rather than just checking API calls.
function gainFixture(value=1){
 const points=[{time:0,value}],param={value,
  setValueAtTime(value,time){points.push({time,value});},
  linearRampToValueAtTime(value,time){points.push({time,value,ramp:true});},
  cancelScheduledValues(time){for(let i=points.length-1;i>=0;i--)if(points[i].time>=time)points.splice(i,1);},
  cancelAndHoldAtTime(time){const value=at(time);for(let i=points.length-1;i>=0;i--)if(points[i].time>=time)points.splice(i,1);points.push({time,value});},
 };
 function at(time){
  const sorted=[...points].sort((a,b)=>a.time-b.time);let previous=sorted[0];
  for(const point of sorted.slice(1)){
   if(point.time>time)return point.ramp?previous.value+(point.value-previous.value)*(time-previous.time)/(point.time-previous.time):previous.value;
   previous=point;
  }
  return previous.value;
 }
 return {param,at,points};
}
test('a slow setup does not consume the phrase fade or truncate its last samples',async()=>{
 const {connectSpeechSource}=await import('../static/presence-audio.js');
 const envelope=gainFixture(),context={currentTime:5.020,createGain:()=>({gain:envelope.param,connect(){}})};
 // Twenty milliseconds of gaze/DOM work has elapsed; use one future start for
 // source.start(startAt) and the gain envelope, preserving the full 100 ms PCM.
 const startAt=context.currentTime+.004;
 connectSpeechSource(context,{buffer:{duration:.1},connect(){}},{},startAt);
 assert.equal(envelope.at(startAt),0);
 assert.ok(envelope.at(startAt+.002)>.49&&envelope.at(startAt+.002)<.51);
 assert.equal(envelope.at(startAt+.080),1);
 assert.ok(envelope.at(startAt+.098)>.49);
 assert.ok(Math.abs(envelope.at(startAt+.1))<1e-10);
});
test('interrupting a phrase fades its sustained signal and can reopen during that fade',async()=>{
 const {fadeSpeechGain}=await import('../static/presence-audio.js');
 const gain=gainFixture();const stopAt=fadeSpeechGain(gain.param,2,0);
 assert.equal(gain.at(2),1);assert.ok(Math.abs(gain.at(2.003)-.5)<1e-10);assert.equal(gain.at(stopAt),0);
 // A replacement cancels the old scheduled mute, even when it arrives early.
 const replacement=gainFixture();fadeSpeechGain(replacement.param,2,0);
 fadeSpeechGain(replacement.param,2.003,1,.004);
 assert.ok(Math.abs(replacement.at(2.003)-.5)<1e-10);
 assert.equal(replacement.at(2.007),1);assert.equal(replacement.at(2.02),1);
});
test('older Web Audio fallback captures gain before cancelling automation',async()=>{
 const {fadeSpeechGain}=await import('../static/presence-audio.js');let held;
 const param={value:.4,cancelScheduledValues(){this.value=1;},setValueAtTime(value){held=value;},linearRampToValueAtTime(){}};
 fadeSpeechGain(param,1,0);assert.equal(held,.4);
});

test('future output gate opening preserves the interruption fade and stays muted until arrival',async()=>{
 const {fadeSpeechGain,openSpeechGate}=await import('../static/presence-audio.js');
 const gain=gainFixture();fadeSpeechGain(gain.param,2,0);openSpeechGate(gain.param,2.15);
 assert.ok(Math.abs(gain.at(2.003)-.5)<1e-10);
 assert.equal(gain.at(2.1),0);assert.equal(gain.at(2.15),0);
 assert.ok(Math.abs(gain.at(2.152)-.5)<1e-10);assert.equal(gain.at(2.154),1);
});
