'use strict';
// Exercise the production speech functions and cross-frame listener without a
// browser, microphone, speech service or network connection.
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'..','workspace.js'),'utf8');
const voiceStart=source.indexOf('function voiceState('),voiceEnd=source.indexOf('\nasync function junomo(',voiceStart);
const bridgeStart=source.indexOf("window.addEventListener('message',event=>{"),bridgeEnd=source.indexOf("\ndocument.addEventListener('keydown'",bridgeStart);
assert.ok(voiceStart>0&&voiceEnd>voiceStart&&bridgeStart>0&&bridgeEnd>bridgeStart,'Locate production voice and presence bridge');
const tick=()=>new Promise(setImmediate);

function harness({ready=true,framePresent=true,name='Moneypenny',presenceMode='together'}={}){
 const events=new Map(),messages=[],audioRequests=[],stops=[],nodes=new Map();
 const frameWindow={postMessage(message,origin){messages.push({message,origin});}};
 const frame={src:'http://127.0.0.1:8090/?embed=jarvis',contentWindow:frameWindow};
 const presenceState={dataset:{state:ready?'ready':'loading'},textContent:ready?'3D READY':'LOADING'};
 const element=()=>({textContent:'',value:'',disabled:false,classList:{toggle(){},remove(){},add(){}}});
 const $=selector=>{if(!nodes.has(selector))nodes.set(selector,element());return nodes.get(selector);};
 const ctx={
  window:{speechSynthesis:{cancel(){}},addEventListener(type,listener){events.set(type,listener);}},
  document:{documentElement:{dataset:{presenceMode}},hidden:false,querySelector(selector){return selector==='#moneypenny-presence'?(framePresent?frame:null):selector==='[data-presence-state]'?presenceState:null;}},
  $,AbortController,AbortSignal,clearTimeout(){},setTimeout(){return 1;},notify(){},
  localStorage:{setItem(){}},selectedAssistantIdentity(){return {name,profile:name==='Moneypenny'?'moneypenny':'english'};},
  URL:{createObjectURL(){return 'blob:isolated-presence-test';},revokeObjectURL(){}},
  Audio:function(){throw new Error('The embedded voice must never create detached audio');},
  fetch(url,options){
   if(url==='/v1/workspace/voice/stop'){stops.push(url);return Promise.resolve({ok:true});}
   if(url==='/v1/workspace/voice/audio')return new Promise((resolve,reject)=>audioRequests.push({resolve,reject,options}));
   throw new Error('Unexpected request: '+url);
  }
 };
 vm.createContext(ctx);
 vm.runInContext(`
 let cloudAudio=null,activeUtterance=null,activeRecognition=null,speechController=null,presenceSpeech=null,presenceSpeechSequence=0;
 let speechEchoUntil=0,wakeArmedUntil=0,wakeRestart=null,wakePaused=false,wakeEnabled=true,wakeMicStream=null,wakeStarts=0;
 const wakeStarter=()=>wakeStarts++;
 ${source.slice(voiceStart,voiceEnd)}
 ${source.slice(bridgeStart,bridgeEnd)}
 globalThis.state={get utterance(){return activeUtterance;},get presence(){return presenceSpeech;},get wakeStarts(){return wakeStarts;},get wakePaused(){return wakePaused;}};
 `,ctx);
 const emit=(type,requestId,extras={})=>events.get('message')({origin:'http://127.0.0.1:8090',source:frameWindow,data:{type,requestId},...extras});
 const speakMessages=()=>messages.filter(row=>row.message.type==='jjrvis-speak');
 return {ctx,emit,events,messages,speakMessages,audioRequests,stops,frameWindow,presenceState,status:()=>$('#voice-status').textContent};
}

test('embedded playback owns the busy marker until its matching idle event',async()=>{
 const h=harness();let started=0;
 assert.equal(h.ctx.speak('Hello James. Ready when you are.',()=>started++),true);
 const sent=h.speakMessages()[0];
 assert.equal(sent.origin,'http://127.0.0.1:8090');
 assert.equal(sent.message.text,'Hello James. Ready when you are.');
 assert.equal(h.ctx.state.utterance,h.ctx.state.presence,'The front-of-house busy marker tracks embedded speech');
 assert.equal(h.ctx.state.presence.requestId,sent.message.requestId);
 h.ctx.resumeWake();assert.equal(h.ctx.state.wakeStarts,0,'A busy utterance prevents premature wake restart');
 assert.equal(started,0,'Preparation alone is not evidence playback started');
 h.emit('moneypenny-presence-speaking',sent.message.requestId);
 assert.equal(started,1);assert.match(h.status(),/speaking/);
 assert.equal(h.ctx.state.wakeStarts,1,'Wake listening can resume during actual playback for interruption');
 h.emit('moneypenny-presence-idle',sent.message.requestId);
 assert.equal(h.ctx.state.utterance,null);assert.equal(h.ctx.state.presence,null);
 assert.match(h.status(),/Listening/);assert.equal(h.presenceState.textContent,'3D READY');
 await tick();assert.equal(h.audioRequests.length,0,'Embedded playback never also generates detached audio');
});

test('Stop cancels embedded playback and late speaking or idle cannot restart it',()=>{
 const h=harness();let started=0;
 h.ctx.speak('A reply that will be interrupted.',()=>started++);
 const requestId=h.speakMessages()[0].message.requestId;
 h.ctx.stopVoice();
 assert.equal(h.messages.at(-1).message.type,'jjrvis-stop');
 assert.equal(h.ctx.state.utterance,null);assert.equal(h.ctx.state.presence,null);
 const status=h.status(),wakes=h.ctx.state.wakeStarts;
 h.emit('moneypenny-presence-speaking',requestId);h.emit('moneypenny-presence-idle',requestId);
 assert.equal(started,0);assert.equal(h.status(),status);assert.equal(h.ctx.state.wakeStarts,wakes);
});

test('stale idle and error events cannot clear a newer embedded answer',()=>{
 const h=harness();h.ctx.speak('Earlier answer.');const old=h.speakMessages()[0].message.requestId;
 h.ctx.speak('The new answer.');const current=h.speakMessages()[1].message.requestId;
 assert.notEqual(old,current);const marker=h.ctx.state.utterance;
 h.emit('moneypenny-presence-speaking',current);const status=h.status();
 h.emit('moneypenny-presence-idle',old);h.emit('moneypenny-presence-error',old);
 assert.equal(h.ctx.state.utterance,marker);assert.equal(h.ctx.state.presence.requestId,current);
 assert.equal(h.status(),status);assert.equal(h.presenceState.textContent,'SPEAKING');
});

test('readiness messages require both the trusted origin and actual iframe window',()=>{
 const h=harness({ready:false});
 h.emit('moneypenny-presence-ready',undefined,{origin:'https://untrusted.invalid'});
 assert.equal(h.presenceState.dataset.state,'loading');
 h.emit('moneypenny-presence-ready',undefined,{source:{}});
 assert.equal(h.presenceState.dataset.state,'loading');
 h.emit('moneypenny-presence-ready');assert.equal(h.presenceState.dataset.state,'ready');
 h.ctx.speak('Now the avatar can speak.');assert.equal(h.speakMessages().length,1);
});

test('unavailable or loading avatar falls back to the selected voice endpoint',async()=>{
 for(const options of [{ready:false},{framePresent:false},{name:'Jarvis'},{presenceMode:'jarvis'}]){
  const h=harness(options);h.ctx.speak('Use the selected assistant voice.');await tick();
  assert.equal(h.speakMessages().length,0);
  assert.equal(h.audioRequests.length,1);
  assert.equal(JSON.parse(h.audioRequests[0].options.body).text,'Use the selected assistant voice.');
  h.ctx.stopVoice();assert.equal(h.audioRequests[0].options.signal.aborted,true);
 }
});

test('avatar startup error disables the bridge and a current speech error releases ownership',async()=>{
 const h=harness();h.emit('moneypenny-presence-error');
 assert.equal(h.presenceState.dataset.state,'unavailable');
 h.ctx.speak('Use audio while the avatar is unavailable.');await tick();assert.equal(h.audioRequests.length,1);
 h.ctx.stopVoice();h.emit('moneypenny-presence-ready');h.ctx.speak('Retry with the avatar.');
 const requestId=h.speakMessages()[0].message.requestId;
 h.emit('moneypenny-presence-error',requestId);
 assert.equal(h.ctx.state.presence,null);assert.equal(h.ctx.state.utterance,null);
 assert.match(h.status(),/could not finish/);assert.ok(h.ctx.state.wakeStarts>0);
 assert.equal(h.audioRequests.length,1,'An embedded speech failure does not silently generate another voice');
});
