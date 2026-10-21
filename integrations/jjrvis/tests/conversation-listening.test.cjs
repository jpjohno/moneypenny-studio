'use strict';
// Exercise the actual production wake/result/end handlers. Capture and the
// assistant form are isolated: no microphone, decoder, model or network runs.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../workspace.js'),'utf8');
const part=(start,end)=>{const a=source.indexOf(start),b=source.indexOf(end,a);assert.ok(a>=0&&b>a);return source.slice(a,b);};
const handlers=part('  wakeStarter=async()=>{','  if(wake)wake.onclick=');
const start=part('function startConversation(){','function voiceState(');
const feedback=part('function updateStageVoice(','let backendVoiceStop=');
const stop=part('function stopAllVoice(){','function splitVoiceText(');
const isStop=part('function isVoiceStopCommand(','function updateStageVoice(');
const noop=()=>{},classes=()=>({add:noop,remove:noop,toggle:noop});
function harness({ready=true,locked=false}={}){
 let now=100000,captures=0,aborts=0,submissions=[],closed=0;const storage=new Map(),timers=new Map();let timerID=0;
 const element=()=>({textContent:'',hidden:false,dataset:{},attributes:{},classList:classes(),setAttribute(key,value){this.attributes[key]=value;}});
 const elements={};for(const id of ['voice-status','assistant-speak','assistant-wake','assistant-submit','assistant-dictate'])elements['#'+id]=element();
 elements['#login']={hidden:!locked};elements['#assistant-input']={value:''};elements['#assistant-answer']={getAttribute:()=>null};
 const stage=element(),startButton=element(),stopButton=element(),enableButton=element();
 const ctx={stopped:locked,conversationActive:false,conversationInvite:false,wakeFailures:0,wakeEnabled:true,wakePaused:false,wakeArmedUntil:0,wakeRestart:null,wakeStarter:null,
  activeRecognition:null,activeUtterance:null,speechEchoUntil:0,voiceReplyRequested:false,assistantRequest:0,assistantController:null,
  commandBriefing:{pause:noop,close:noop},commandLayout:{close:noop},showAssistant:noop,Date:{now:()=>now},
  document:{hidden:false,querySelector:selector=>({'[data-stage-voice]':stage,'[data-presence-talk]':startButton,'[data-voice-stop]':stopButton,'.voice-startup-enable':enableButton}[selector]||null)},
  $:selector=>elements[selector]||null,wake:elements['#assistant-wake'],localStorage:{setItem:(key,value)=>storage.set(key,value)},
  form:{requestSubmit:()=>submissions.push(elements['#assistant-input'].value)},
  closeWakeMicrophone:()=>{closed++;},isVoiceInterruption:()=>false,interruptReply:noop,
  setTimeout:fn=>{timers.set(++timerID,fn);return timerID;},clearTimeout:id=>timers.delete(id),speak:noop,
 };
 ctx.Recognition=class{
  start(){this.running=true;captures++;if(ready)this.ready();}
  ready(){this.onstart?.();}
  stop(){this.running=false;this.onend?.();}
  abort(){aborts++;this.running=false;this.onend?.();}
  result(text){this.onresult?.({resultIndex:0,results:[Object.assign([{transcript:text}],{isFinal:true})]});}
 };
 vm.createContext(ctx);
 vm.runInContext(`function stopVoice(){wakePaused=true;const old=activeRecognition;activeRecognition=null;if(old)old.abort();return Promise.resolve();}\n${isStop}\n${feedback}\n${start}\n${stop}\n${handlers}`,ctx);
 return {ctx,elements,stage,startButton,stopButton,enableButton,storage,timers,submissions,get captures(){return captures;},get aborts(){return aborts;},get closed(){return closed;},advance:ms=>{now+=ms;},restart(){for(const [id,fn] of [...timers]){timers.delete(id);fn();}}};
}
test('Start conversation upgrades the existing wake capture and accepts a plain question after 45 seconds',async()=>{
 const h=harness();await h.ctx.wakeStarter();const original=h.ctx.activeRecognition;
 assert.equal(h.captures,1);assert.equal(h.ctx.conversationActive,false);
 assert.equal(h.stage.textContent,'Wake word ready · microphone on');assert.equal(h.startButton.textContent,'Start conversation');assert.equal(h.startButton.attributes['aria-pressed'],'false');
 h.advance(60000);h.ctx.startConversation();assert.equal(h.ctx.conversationActive,true);
 assert.equal(h.ctx.activeRecognition,original);assert.equal(h.captures,1);assert.equal(h.aborts,0);
 assert.equal(h.stage.textContent,'Listening · microphone on');assert.equal(h.startButton.textContent,'Conversation is listening');assert.equal(h.startButton.attributes['aria-pressed'],'true');
 h.advance(60000);original.result('show my map');
 assert.deepEqual(h.submissions,['show my map']);assert.equal(h.ctx.voiceReplyRequested,true);
 assert.equal(h.storage.get('jjrvis-wake-enabled'),'true');
});
test('automatic wake mode still requires its name or a live short follow-up window',async()=>{
 const h=harness();await h.ctx.wakeStarter();const r=h.ctx.activeRecognition;
 r.result('show my map');assert.deepEqual(h.submissions,[]);
 r.result('Moneypenny');h.advance(16000);r.result('show my map');assert.deepEqual(h.submissions,[]);
 r.result('Hey Jarvis show my map');assert.deepEqual(h.submissions,['show my map']);
 assert.equal(h.ctx.conversationActive,false);
});
test('explicit conversation preserves speaker echo rejection and the spoken Stop command',async()=>{
 const h=harness();await h.ctx.wakeStarter();h.ctx.startConversation();const r=h.ctx.activeRecognition;
 h.ctx.activeUtterance={spokenText:'some reply'};r.result('show my map');assert.deepEqual(h.submissions,[]);
 h.ctx.activeUtterance=null;h.ctx.speechEchoUntil=h.ctx.Date.now()+800;r.result('show my map');assert.deepEqual(h.submissions,[]);
 r.result('Moneypenny stop');assert.equal(h.ctx.conversationActive,false);assert.equal(h.ctx.wakeEnabled,false);
 assert.equal(h.ctx.activeRecognition,null);assert.equal(h.closed,1);assert.equal(h.storage.get('jjrvis-wake-enabled'),'false');
 await h.ctx.wakeStarter();assert.equal(h.captures,1,'Stop must not restart capture');
});
test('listening feedback waits for capture start and does not claim a live microphone after Stop',async()=>{
 const h=harness({ready:false});await h.ctx.wakeStarter();const r=h.ctx.activeRecognition;
 h.ctx.voiceState('Listening for your next question…');
 assert.equal(h.elements['#voice-status'].textContent,'Starting microphone…');assert.equal(h.stage.dataset.state,'off');
 assert.equal(h.startButton.textContent,'Start conversation');
 assert.equal(h.enableButton.hidden,false,'the enable action stays available before capture starts');
 r.ready();assert.equal(r.listenStarted,true);h.ctx.voiceState('Listening for your next question…');
 assert.equal(h.enableButton.hidden,true,'a working microphone must not still offer Enable microphone');
 assert.equal(h.elements['#voice-status'].textContent,'Listening for your next question…');assert.equal(h.stage.dataset.state,'listening');
 h.ctx.stopAllVoice();h.ctx.voiceState('Listening for your next question…');
 assert.equal(h.elements['#voice-status'].textContent,'Microphone off · choose Start conversation to speak.');assert.equal(h.stage.dataset.state,'off');
});
test('explicit conversation shows capture starting without claiming a pressed listening control',()=>{
 const h=harness({ready:false});h.ctx.startConversation();
 assert.equal(h.ctx.conversationActive,true);assert.equal(h.startButton.textContent,'Starting microphone…');assert.equal(h.startButton.attributes['aria-pressed'],'false');
});
test('a locked workspace cannot start conversation or change its saved microphone choice',()=>{
 const h=harness({locked:true});h.ctx.startConversation();assert.equal(h.ctx.conversationActive,false);assert.equal(h.captures,0);assert.equal(h.storage.size,0);
});
test('Start conversation replaces manual dictation once instead of leaving it waiting for Finish',async()=>{
 const h=harness(),manual=new h.ctx.Recognition();h.ctx.activeRecognition=manual;manual.wakeMode=false;manual.running=true;
 h.ctx.startConversation();await new Promise(setImmediate);
 assert.equal(h.ctx.conversationActive,true);assert.equal(h.aborts,1);assert.equal(h.captures,1);
 assert.equal(h.ctx.activeRecognition.wakeMode,true);assert.notEqual(h.ctx.activeRecognition,manual);
});
test('button Stop clears the old follow-up window before automatic wake listening is enabled again',async()=>{
 const h=harness();await h.ctx.wakeStarter();h.ctx.startConversation();assert.ok(h.ctx.wakeArmedUntil>h.ctx.Date.now());
 h.ctx.stopAllVoice();assert.equal(h.ctx.wakeArmedUntil,0);
 h.ctx.wakeEnabled=true;h.ctx.wakePaused=false;await h.ctx.wakeStarter();
 h.ctx.activeRecognition.result('show my map');assert.deepEqual(h.submissions,[]);assert.equal(h.ctx.conversationActive,false);
});
test('manual dictation is labelled as dictation instead of wake-word capture',()=>{
 const h=harness();h.ctx.activeRecognition={wakeMode:false,listenStarted:true};h.ctx.voiceState('Listening · press Finish & ask when ready.');
 assert.equal(h.stage.textContent,'Dictation · microphone on');assert.equal(h.startButton.textContent,'Start conversation');assert.equal(h.startButton.attributes['aria-pressed'],'false');
});
test('three normal long quiet capture cycles keep an explicit conversation available',async()=>{
 const h=harness();await h.ctx.wakeStarter();h.ctx.startConversation();
 for(let i=0;i<3;i++){
  h.advance(11000);h.ctx.activeRecognition.stop();assert.equal(h.ctx.wakePaused,false);assert.equal(h.ctx.wakeFailures,0);
  h.restart();await new Promise(setImmediate);
 }
 assert.equal(h.ctx.conversationActive,true);assert.equal(h.captures,4);
 h.ctx.activeRecognition.result('show my map');assert.deepEqual(h.submissions,['show my map']);
});
test('three rapid empty capture endings still pause a broken explicit conversation',async()=>{
 const h=harness();await h.ctx.wakeStarter();h.ctx.startConversation();
 for(let i=0;i<3;i++){
  h.advance(100);h.ctx.activeRecognition.stop();if(i<2){h.restart();await new Promise(setImmediate);}
 }
 assert.equal(h.ctx.wakePaused,true);assert.equal(h.ctx.wakeFailures,3);assert.equal(h.captures,3);assert.equal(h.timers.size,0);
 assert.match(h.elements['#voice-status'].textContent,/ended repeatedly/);
});
test('automatic wake-only mode retains its repeated-silent-ending guard even after long captures',async()=>{
 const h=harness();await h.ctx.wakeStarter();
 for(let i=0;i<3;i++){
  h.advance(11000);h.ctx.activeRecognition.stop();if(i<2){h.restart();await new Promise(setImmediate);}
 }
 assert.equal(h.ctx.conversationActive,false);assert.equal(h.ctx.wakePaused,true);assert.equal(h.ctx.wakeFailures,3);
});
