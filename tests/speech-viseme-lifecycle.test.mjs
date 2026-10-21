import test from 'node:test';
import assert from 'node:assert/strict';
import {installSpeechVisemeLifecycle} from '../static/presence-audio.js';

// Exercise the shipped HeadAudio class itself. Only the browser worklet port is
// simulated; no microphone, WAV playback, model download or inference is used.
globalThis.AudioWorkletNode=class{
  constructor(){this.messages=[];this.port={onmessage:null,postMessage:message=>this.messages.push(message)};}
};
const {HeadAudio}=await import('../static/vendor/headaudio/headaudio.min.mjs');
function headAudio(){return new HeadAudio({}, {processorOptions:{visemeEventsEnabled:true}});}
const deliver=(processor,event)=>processor.port.onmessage({data:event});

test('real vendor handler ignores AA index zero before the local adapter',()=>{
 const lips=headAudio();deliver(lips,{event:'viseme',viseme:5});
 assert.equal(lips.visemeActive,5);deliver(lips,{event:'viseme',viseme:0});
 assert.equal(lips.visemeNames[0],'viseme_aa');
 assert.equal(lips.visemeActive,5,'reproduces the actual bundled falsy-zero bug');
});

test('AA replaces a closed consonant and reaches the real viseme interpolation',()=>{
 const lips=headAudio(),values=new Map(),events=[];
 lips.onvalue=(name,value)=>values.set(name,value);lips.onviseme=event=>events.push(event.viseme);
 assert.equal(installSpeechVisemeLifecycle(lips),true);
 deliver(lips,{event:'viseme',viseme:5});lips.update(100);
 assert.equal(values.get('viseme_PP'),.75);
 deliver(lips,{event:'viseme',viseme:0});lips.update(100);
 assert.equal(lips.visemeActive,0);assert.ok(Math.abs(values.get('viseme_PP'))<1e-12);
 assert.equal(values.get('viseme_aa'),.65);assert.deepEqual(events,[5,0]);
 deliver(lips,{event:'viseme',viseme:14});lips.update(100);
 assert.equal(lips.visemeActive,-1);assert.ok(Math.abs(values.get('viseme_aa'))<1e-12);
});

test('Stop releases the active vowel without waiting for a worker ended event',()=>{
 const lips=headAudio(),values=new Map();lips.onvalue=(name,value)=>values.set(name,value);
 installSpeechVisemeLifecycle(lips);deliver(lips,{event:'viseme',viseme:0});lips.update(100);
 lips.resetAll();assert.equal(lips.visemeActive,-1);assert.equal(lips.messages.at(-1).event,'reset');
 lips.update(50);assert.ok(values.get('viseme_aa')>0&&values.get('viseme_aa')<.65);
 lips.update(50);assert.ok(Math.abs(values.get('viseme_aa'))<1e-12);
});

test('adapter preserves unrelated events and installs only once',()=>{
 const lips=headAudio();let started=0,ended=0;
 lips.onstarted=()=>started++;lips.onended=()=>ended++;
 installSpeechVisemeLifecycle(lips);const receive=lips.port.onmessage,reset=lips.resetAll;
 installSpeechVisemeLifecycle(lips);assert.equal(lips.port.onmessage,receive);assert.equal(lips.resetAll,reset);
 deliver(lips,{event:'started'});deliver(lips,{event:'viseme',viseme:2});deliver(lips,{event:'ended'});
 assert.equal(started,1);assert.equal(ended,1);assert.equal(lips.visemeActive,-1);
 assert.equal(installSpeechVisemeLifecycle({}),false);
});

test('speech frame clock uses actual elapsed audio time with bounded catch-up',async()=>{
 const {SpeechFrameClock}=await import('../static/presence-audio.js');
 const context={currentTime:10},clock=new SpeechFrameClock(context);
 context.currentTime=10.02;assert.ok(Math.abs(clock.tick()-20)<1e-9);
 context.currentTime=10.22;assert.equal(clock.tick(),100);
 context.currentTime=40;assert.equal(clock.tick(),100,'long hidden periods cannot replay a backlog');
 assert.equal(clock.tick(),0,'a suspended audio clock does not advance mouth animation');
 context.currentTime=2;assert.equal(clock.tick(),0,'audio clock replacement or reset cannot yield a negative dt');
 context.currentTime=2.04;assert.ok(Math.abs(clock.tick()-40)<1e-9);
 context.currentTime=NaN;assert.equal(clock.tick(),0);
 context.currentTime=5;assert.equal(clock.tick(),0,'the first valid sample establishes a fresh baseline');
 context.currentTime=5.07;assert.ok(Math.abs(clock.tick()-70)<1e-9);
 clock.reset();assert.equal(clock.tick(),0);
});

test('actual HeadAudio reaches the current vowel and releases on a five-fps rendered update',async()=>{
 const {SpeechFrameClock}=await import('../static/presence-audio.js');
 const context={currentTime:0},clock=new SpeechFrameClock(context),lips=headAudio(),values=new Map();
 installSpeechVisemeLifecycle(lips);lips.onvalue=(name,value)=>values.set(name,value);
 deliver(lips,{event:'viseme',viseme:0});
 context.currentTime=.2;lips.update(clock.tick());
 assert.equal(values.get('viseme_aa'),.65,'latest open vowel catches up with continuously playing audio');
 lips.resetAll();context.currentTime=.4;lips.update(clock.tick());
 assert.ok(Math.abs(values.get('viseme_aa'))<1e-12,'mouth releases at next visible frame rather than running in slow motion');
 // Control: production TalkingHead clamps its opt.update dt to twice the
 // active 30-fps frame duration even when a frame actually took 200 ms.
 const clamped=headAudio();installSpeechVisemeLifecycle(clamped);const control=new Map();
 clamped.onvalue=(name,value)=>control.set(name,value);deliver(clamped,{event:'viseme',viseme:0});clamped.update(100);
 clamped.resetAll();clamped.update(2000/30);
 assert.ok(control.get('viseme_aa')>.1,'reproduces the old retained-open vowel after a slow frame');
});
