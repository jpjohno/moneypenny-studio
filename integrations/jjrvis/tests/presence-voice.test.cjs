'use strict';
// Run production queue, audio transport and trusted-frame lifecycle together.
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'..','workspace.js'),'utf8');
const voiceStart=source.indexOf('function updateStageVoice('),voiceEnd=source.indexOf('\nasync function junomo(',voiceStart);
const bridgeStart=source.indexOf("window.addEventListener('message',event=>{"),bridgeEnd=source.indexOf("\ndocument.addEventListener('keydown'",bridgeStart);
assert.ok(voiceStart>0&&voiceEnd>voiceStart&&bridgeStart>0&&bridgeEnd>bridgeStart);
const tick=()=>new Promise(setImmediate);
function harness({ready=true,framePresent=true,name='Moneypenny',presenceMode='together',origin='https://app.jjrvis.com',frameOrigin=origin}={}){
 const events=new Map(),messages=[],audioRequests=[],stops=[],nodes=new Map(),audio=[];
 let identity={name,profile:name==='Jarvis'?'english':'moneypenny',speed:1.0};
 const frameWindow={postMessage(message,origin){messages.push({message,origin});}};
 const frame={src:frameOrigin+'/presence/?embed=jarvis',contentWindow:frameWindow};
 const presenceState={dataset:{state:ready?'ready':'loading'},textContent:ready?'3D READY':'LOADING'};
 const element=()=>({textContent:'',value:'',disabled:false,classList:{toggle(){},remove(){},add(){}}});
 const $=selector=>{if(!nodes.has(selector))nodes.set(selector,element());return nodes.get(selector);};
 class TestAudio{constructor(){audio.push(this);}play(){return Promise.resolve();}pause(){this.paused=true;}}
 const ctx={window:{JJSpokenReply:require('../spoken-reply'),JJSettings:{preferences:()=>({volume:.6})},speechSynthesis:{cancel(){}},addEventListener(type,listener){events.set(type,listener);}},
  location:{origin,href:origin+'/workspace'},document:{documentElement:{dataset:{presenceMode}},hidden:false,querySelector(selector){return selector==='#moneypenny-presence'?(framePresent?frame:null):selector==='[data-presence-state]'?presenceState:null;}},
  $,AbortController,AbortSignal,DOMException,clearTimeout(){},setTimeout(){return 1;},notify(){},localStorage:{setItem(){}},selectedAssistantIdentity(){return identity;},URL,Audio:TestAudio,
  fetch(url,options){if(url==='/v1/workspace/voice/stop'){stops.push(url);return Promise.resolve({ok:true});}if(url==='/v1/workspace/voice/audio')return new Promise((resolve,reject)=>audioRequests.push({resolve,reject,options}));throw new Error('Unexpected request: '+url);}
 };
 vm.createContext(ctx);vm.runInContext(`let conversationInvite=false,conversationActive=false;let cloudAudio=null,activeUtterance=null,activeRecognition=null,speechController=null,presenceSpeech=null,presenceSpeechSequence=0,streamingSpeech=null;let speechEchoUntil=0,wakeArmedUntil=0,wakeRestart=null,wakePaused=false,wakeEnabled=true,wakeMicStream=null,wakeStarts=0;const wakeStarter=()=>wakeStarts++;${source.slice(voiceStart,voiceEnd)}\n${source.slice(bridgeStart,bridgeEnd)}\nglobalThis.state={get utterance(){return activeUtterance;},get presence(){return presenceSpeech;},get wakeStarts(){return wakeStarts;},get speech(){return streamingSpeech;}};`,ctx);
 const emit=(type,requestId,data={},extras={})=>events.get('message')({origin:frameOrigin,source:frameWindow,data:{type,requestId,...data},...extras});
 const resolveAudio=async(index=0,overrides={})=>{const sent=JSON.parse(audioRequests[index].options.body),meta={'X-JJRVIS-Voice-Provider':'local-kokoro','X-JJRVIS-Voice-Profile':sent.profile,'X-JJRVIS-Voice-ID':sent.profile==='english'?'bm_george':'bf_emma','X-JJRVIS-Voice-Language':'en-GB',...overrides};audioRequests[index].resolve({ok:true,headers:{get:key=>meta[key]||null},blob:async()=>new Blob([new Uint8Array([1,2,3])],{type:'audio/wav'})});await tick();};
 return {ctx,emit,messages,audioRequests,stops,frameWindow,presenceState,audio,resolveAudio,setIdentity:value=>{identity=value;},audioMessages:()=>messages.filter(row=>row.message.type==='jjrvis-audio'),status:()=>$('#voice-status').textContent};
}
test('same-origin avatar receives the broker WAV and stays busy until phrase and final acknowledgements',async()=>{
 const h=harness();let started=0;h.ctx.speak('Ready when you are.',()=>started++);await tick();assert.equal(h.audioRequests.length,1);assert.equal(started,0);await h.resolveAudio();
 const sent=h.audioMessages()[0];assert.equal(sent.origin,'https://app.jjrvis.com');assert.ok(sent.message.audio instanceof ArrayBuffer);assert.equal(h.audio.length,0);assert.equal(h.ctx.state.utterance.requestId,sent.message.requestId);h.ctx.resumeWake();assert.equal(h.ctx.state.wakeStarts,0);
 h.emit('moneypenny-presence-speaking',sent.message.requestId,{sequence:0});assert.equal(started,1);assert.match(h.status(),/speaking/);assert.equal(h.ctx.state.wakeStarts,1);
 h.emit('moneypenny-presence-idle',sent.message.requestId,{sequence:0,final:false});await tick();assert.equal(h.messages.at(-1).message.type,'jjrvis-audio-end');assert.ok(h.ctx.state.utterance);
 h.emit('moneypenny-presence-idle',sent.message.requestId,{final:true});await tick();assert.equal(h.ctx.state.utterance,null);assert.equal(h.status(),'Starting microphone…');assert.equal(h.audioRequests.length,1);
});
test('Stop aborts audio generation and late frame acknowledgements cannot restart playback',async()=>{
 const h=harness();let started=0;h.ctx.speak('The pending answer.',()=>started++);await tick();h.ctx.stopVoice();assert.equal(h.audioRequests[0].options.signal.aborted,true);await h.resolveAudio();assert.equal(h.audioMessages().length,0);assert.equal(h.ctx.state.utterance,null);const status=h.status();h.emit('moneypenny-presence-speaking','1',{sequence:0});h.emit('moneypenny-presence-idle','1',{sequence:0,final:false});assert.equal(started,0);assert.equal(h.status(),status);
});
test('stale request IDs and sequences cannot finish a newer phrase',async()=>{
 const h=harness();h.ctx.speak('An earlier answer.');await tick();await h.resolveAudio();const old=h.audioMessages()[0].message.requestId;h.ctx.speak('The current answer.');await tick();await h.resolveAudio(1);const current=h.audioMessages()[1].message.requestId;assert.notEqual(old,current);const marker=h.ctx.state.utterance;
 for(const data of [{sequence:0,final:false},{sequence:44,final:false},{final:true}])h.emit('moneypenny-presence-idle',old,data);h.emit('moneypenny-presence-idle',current,{sequence:44,final:false});h.emit('moneypenny-presence-idle',current,{final:true});h.emit('moneypenny-presence-error',old);assert.equal(h.ctx.state.utterance,marker);assert.equal(h.ctx.state.presence.requestId,current);h.ctx.stopVoice();
});
test('frame readiness requires the actual window and trusted origin',()=>{
 const h=harness({ready:false});h.emit('moneypenny-presence-ready',null,{}, {origin:'https://untrusted.invalid'});h.emit('moneypenny-presence-ready',null,{}, {source:{}});assert.equal(h.presenceState.dataset.state,'loading');h.emit('moneypenny-presence-ready');assert.equal(h.presenceState.dataset.state,'ready');
 const foreign=harness({frameOrigin:'https://untrusted.invalid'});foreign.emit('moneypenny-presence-ready');assert.equal(foreign.ctx.presenceOrigin(),null);
});
test('unavailable, Jarvis-only or missing avatar uses the same fast voice endpoint without iframe audio',async()=>{
 for(const options of [{ready:false},{framePresent:false},{name:'Jarvis'},{presenceMode:'jarvis'}]){const h=harness(options);h.ctx.speak('Use the selected voice.');await tick();assert.equal(h.audioRequests.length,1);await h.resolveAudio();assert.equal(h.audioMessages().length,0);assert.equal(h.audio.length,1);assert.equal(h.audio[0].volume,.6);h.audio[0].onended();await tick();assert.equal(h.ctx.state.utterance,null);}
});
test('matching avatar error releases speech without silently generating a second voice',async()=>{
 const h=harness();h.ctx.speak('Retry with the avatar.');await tick();await h.resolveAudio();const id=h.audioMessages()[0].message.requestId;h.emit('moneypenny-presence-error',id);await tick();assert.equal(h.ctx.state.presence,null);assert.equal(h.ctx.state.utterance,null);assert.match(h.status(),/could not play/);assert.equal(h.audioRequests.length,1);assert.ok(h.ctx.state.wakeStarts>0);
});

test('ordinary workspace navigation preserves active listening and reply ownership',()=>{
 let rendered=0,voiceStops=0;
 const ctx={window:{JJCompanion:{state:()=>({mode:'workspace'})}},document:{body:{dataset:{companionHidden:'false'}}},clearTimeout(){},notify(){},render(){rendered++;},stopVoice(){voiceStops++;},$:()=>null};
 vm.createContext(ctx);
 const begin=source.indexOf('function navigate(view)'),end=source.indexOf('\n',begin);
 vm.runInContext(`let marketRefreshTimer=null,current='overview',pageOffset=0,pageQuery='',voiceReplyRequested=true;let activeRecognition={listening:true},activeUtterance={id:1};${source.slice(begin,end)};navigate('home');globalThis.after={current,voiceReplyRequested,listening:activeRecognition.listening,reply:activeUtterance.id};`,ctx);
 assert.equal(rendered,1);assert.equal(voiceStops,0);assert.equal(ctx.after.current,'home');assert.equal(ctx.after.listening,true);assert.equal(ctx.after.reply,1);assert.equal(ctx.after.voiceReplyRequested,true);
});


test('native partial speech can interrupt while matching spoken audio is excluded',()=>{
 const start=source.indexOf('function isVoiceInterruption('),end=source.indexOf('class LocalRecognition',start);
 const ctx={};vm.createContext(ctx);vm.runInContext(source.slice(start,end),ctx);
 assert.equal(ctx.isVoiceInterruption('Wait','Here are your headlines.'),true);
 assert.equal(ctx.isVoiceInterruption('Moneypenny can we talk','Here are your headlines.'),true);
 assert.equal(ctx.isVoiceInterruption('Here are your headlines','Here are your headlines.'),false);
 assert.equal(ctx.isVoiceInterruption('um','Here are your headlines.'),false);
});


test('one spoken reply pins the British identity and speed across all prefetched phrases',async()=>{
 const h=harness({framePresent:false});
 h.ctx.speak('Here is your first sentence. Here is the next sentence.');await tick();
 assert.deepEqual(JSON.parse(h.audioRequests[0].options.body),{text:'Here is your first sentence.',profile:'moneypenny',speed:1});
 h.setIdentity({name:'Jarvis',profile:'english',speed:1.4});
 await h.resolveAudio();await tick();
 assert.equal(h.audioRequests.length,2);
 const next=JSON.parse(h.audioRequests[1].options.body);assert.equal(next.profile,'moneypenny');assert.equal(next.speed,1);
 assert.match(h.status(),/Moneypenny speaking/);h.ctx.stopVoice();await h.resolveAudio(1);
});

test('mismatched or unconfirmed audio identity is not played through the avatar or browser',async()=>{
 for(const metadata of [
  {'X-JJRVIS-Voice-ID':'af_heart'},
  {'X-JJRVIS-Voice-Language':'en-US'},
  {'X-JJRVIS-Voice-Profile':'english'},
  {'X-JJRVIS-Voice-Provider':'openai'},
  {'X-JJRVIS-Voice-ID':null}
 ]){
  const h=harness();h.ctx.speak('Use the selected British voice.');await tick();await h.resolveAudio(0,metadata);
  assert.equal(h.audioMessages().length,0);assert.equal(h.audio.length,0);assert.equal(h.audioRequests.length,1);
  assert.match(h.status(),/No different voice was played/);assert.equal(h.ctx.state.utterance,null);
 }
});

test('animation creation link exists only in a local workspace movement menu',()=>{
 const begin=source.indexOf('<details class="presence-movement-menu">'),end=source.indexOf('</details>',begin);
 assert.ok(begin>0&&end>begin);
 const template=source.slice(begin,end+10);
 for(const hostname of ['127.0.0.1','localhost','app.jjrvis.com']){
  const rendered=vm.runInNewContext('`'+template+'`',{location:{hostname}});
  assert.equal(rendered.includes('http://127.0.0.1:8090/?panel=animation#animationBuilder'),hostname!=='app.jjrvis.com');
 }
});


test('Stop clears the visible speaking badge and unowned frame events cannot restore it',async()=>{
 const h=harness();h.ctx.speak('Ready for a voice check.');await tick();await h.resolveAudio();
 const id=h.audioMessages()[0].message.requestId;h.emit('moneypenny-presence-speaking',id,{sequence:0});
 assert.equal(h.presenceState.textContent,'SPEAKING');h.ctx.stopVoice();
 assert.equal(h.presenceState.textContent,'3D READY');
 h.emit('moneypenny-presence-speaking',undefined);h.emit('moneypenny-presence-speaking',id,{sequence:0});
 assert.equal(h.presenceState.textContent,'3D READY');assert.equal(h.ctx.state.presence,null);
});
