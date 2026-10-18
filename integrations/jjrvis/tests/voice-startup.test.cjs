'use strict';
// Run the real startup controller against simulated permissions, without using
// the host microphone, a browser, the network, or the selected voice service.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'..','workspace.js'),'utf8');
const startup=source.slice(source.indexOf('let voiceStartupInitialised='),source.indexOf('\nasync function streamAssistantAnswer('));
const tick=()=>new Promise(setImmediate);

function harness({permission='granted',profile='moneypenny',automatic=true,query,preferences,contextState='running'}={}){
 const listeners=new Map(),nodes=new Map(),calls={captures:0,greetings:[],wakeStarts:0,status:[],released:0};
 const storage=new Map([['jjrvis-auto-microphone',String(automatic)]]),session=new Map();
 const node=()=>({textContent:'',hidden:false,disabled:false,attrs:{},setAttribute(k,v){this.attrs[k]=v;},after(child){calls.enable=child;}});
 const $=selector=>{if(!nodes.has(selector))nodes.set(selector,node());return nodes.get(selector);};
 const ctx={console,setTimeout,clearTimeout,window:{JJSettings:{preferences:()=>({startup:false})}},
  document:{hidden:false,querySelector:$,createElement:node,addEventListener(type,handler){listeners.set(type,handler);},removeEventListener(type,handler){if(listeners.get(type)===handler)listeners.delete(type);}},
  localStorage:{getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,value)},
  sessionStorage:{getItem:key=>session.get(key)??null,setItem:(key,value)=>session.set(key,value)},
  navigator:{permissions:{query:query||(async()=>({state:permission}))},mediaDevices:{async getUserMedia(){calls.captures++;return {getTracks:()=>[{stop(){calls.released++;}}]};}}},
  AudioContext:class{constructor(){this.state=contextState;}async resume(){this.state=contextState;}},
  api:preferences||(async()=>({profile,choices:[{id:'moneypenny',name:'Moneypenny'},{id:'english',name:'Jarvis'}]})),
  $,playStartup(){assert.fail('The saved animation preference must be respected');},
  voiceState:message=>calls.status.push(message),speak:(text,started)=>{calls.greetings.push(text);started?.();},closeWakeMicrophone(){calls.released++;},
 };
 vm.createContext(ctx);vm.runInContext(`let stopped=false,wakeEnabled=false,wakePaused=false,wakeFailures=0,wakeMicStream=null,localAudioContext=null;const wakeStarter=()=>calls.wakeStarts++;\n${startup}\nglobalThis.startupState={stop(){wakeEnabled=false;},get enabled(){return wakeEnabled;},get paused(){return wakePaused;}};`,Object.assign(ctx,{calls}));
 return {ctx,calls,listeners,storage,start:()=>ctx.initialiseVoiceStartup(),gesture:async(target='neutral')=>{listeners.get('pointerdown')?.({type:'pointerdown',isTrusted:true,target:{closest:selector=>target==='stop'&&selector.includes('#assistant-stop')?{}:null}});await tick();}};
}

test('previously granted microphone starts once and greets in the selected male identity',async()=>{
 const h=harness({profile:'english'});await h.start();await tick();
 assert.equal(h.calls.captures,1);assert.equal(h.ctx.startupState.enabled,true);
 assert.match(h.calls.greetings[0],/Jarvis here/);assert.doesNotMatch(h.calls.greetings[0],/Moneypenny/);
 assert.equal(h.ctx.$('#assistant-heading').textContent,'Jarvis');assert.equal(h.ctx.$('[data-open-assistant]').textContent,'✦ Jarvis');
 await h.start();assert.equal(h.calls.captures,1,'Repeated workspace rendering must not recapture or greet');
});

test('new microphone permission waits for a real interaction and uses a compact affordance',async()=>{
 const h=harness({permission:'prompt'});await h.start();
 assert.equal(h.calls.captures,0);assert.deepEqual(h.calls.greetings,[]);assert.equal(h.calls.enable.hidden,false);
 await h.gesture();assert.equal(h.calls.captures,0,'An unrelated click must not request microphone permission');await h.calls.enable.onclick();await tick();assert.equal(h.calls.captures,1);assert.equal(h.calls.enable.hidden,true);assert.match(h.calls.greetings[0],/Moneypenny here/);
 assert.equal(h.listeners.has('pointerdown'),false);
});

test('microphone denial is quiet and never creates a repeated permission loop',async()=>{
 const h=harness({permission:'denied'});await h.start();await h.gesture();await h.start();
 assert.equal(h.calls.captures,0);assert.deepEqual(h.calls.greetings,[]);assert.equal(h.listeners.size,0);
 assert.match(h.calls.status.at(-1),/blocked/);assert.equal(h.calls.enable.hidden,false);
});

test('Stop during startup prevents pending automatic work from reopening the microphone',async()=>{
 let resolvePermission;const h=harness({query:()=>new Promise(resolve=>{resolvePermission=resolve;})});
 const startup=h.start();await tick();h.ctx.startupState.stop();resolvePermission({state:'granted'});await startup;await tick();
 assert.equal(h.calls.captures,0);assert.deepEqual(h.calls.greetings,[]);assert.equal(h.ctx.startupState.enabled,false);
});

test('explicit automatic-start opt out persists and leaves voice available for manual use',async()=>{
 const h=harness({automatic:false});await h.start();
 assert.equal(h.calls.captures,0);assert.deepEqual(h.calls.greetings,[]);assert.equal(h.listeners.size,0);assert.equal(h.ctx.startupState.enabled,false);
 assert.equal(h.calls.enable,undefined);
});

test('Stop as the first interaction cancels the permission affordance',async()=>{
 const h=harness({permission:'prompt'});await h.start();await h.gesture('stop');h.ctx.startupState.stop();await h.gesture();
 assert.equal(h.calls.captures,0);assert.equal(h.calls.enable.hidden,true);assert.equal(h.listeners.size,0);
});
