'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../workspace.js'),'utf8');
const code=source.slice(source.indexOf('function startConversation(){'),source.indexOf('function voiceState('));
function harness(locked=false){
 const calls=[],storage=new Map(),ctx={stopped:locked,activeRecognition:null,commandBriefing:{pause:()=>calls.push('pause'),close:()=>calls.push('close')},commandLayout:{close:()=>calls.push('drawer-close')},showAssistant:()=>calls.push('show'),stopVoice:()=>calls.push('stop-old-voice'),voiceState:()=>{},wakeStarter:()=>calls.push('start'),localStorage:{setItem:(k,v)=>storage.set(k,v)},Date};
 vm.createContext(ctx);vm.runInContext(code,ctx);return {ctx,calls,storage};
}
test('Start conversation explicitly arms listening and the single invitation',()=>{
 const h=harness();h.ctx.startConversation();assert.equal(h.calls.at(-1),'start');assert.equal(h.ctx.wakeEnabled,true);assert.equal(h.ctx.wakePaused,false);assert.equal(h.ctx.conversationInvite,true);assert.ok(h.ctx.wakeArmedUntil>Date.now());assert.equal(h.storage.get('jjrvis-wake-enabled'),'true');
});
test('a locked workspace cannot open the microphone or change its opt-out',()=>{
 const h=harness(true);h.ctx.startConversation();assert.deepEqual(h.calls,['show']);assert.equal(h.storage.size,0);
});
test('opening an already listening conversation does not capture twice',()=>{
 const h=harness();h.ctx.activeRecognition={};h.ctx.startConversation();assert.equal(h.calls.includes('start'),false);assert.equal(h.calls.includes('stop-old-voice'),false);
});
