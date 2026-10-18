/* Run: node tests/test_voice_interrupt.cjs. No browser, microphone or network. */
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const workspace = fs.readFileSync(path.join(__dirname, '..', 'workspace.js'), 'utf8');
const voiceStart = workspace.indexOf('function voiceState(');
const voiceEnd = workspace.indexOf('\nasync function junomo(', voiceStart);
assert.ok(voiceStart >= 0 && voiceEnd > voiceStart, 'Locate the actual workspace voice functions');
const voiceSource = workspace.slice(voiceStart, voiceEnd);
const tick = () => new Promise(resolve => setImmediate(resolve));

function harness({deferStop=false}={}) {
  const audioRequests = [], stopRequests = [], audios = [], nodes = new Map(), revoked = [];
  let nextURL = 0;
  const element = () => ({textContent: '', value: '', disabled: false, classList: {toggle() {}, remove() {}, add() {}}});
  const context = {
    window: {
      JJSpokenReply: require('../spoken-reply'),
      JJSettings: {preferences() {return {volume:.85};}},
      speechSynthesis: {cancel() {}, getVoices() { return []; }, resume() {}, speak() {}},
      SpeechSynthesisUtterance: function () {},
    },
    SpeechSynthesisUtterance: function (text) { this.text = text; },
    document: {hidden: false, documentElement:{dataset:{presenceMode:'together'}}, querySelector() { return null; }},
    localStorage: {setItem() {}},
    clearTimeout() {},
    AbortSignal, AbortController, DOMException,
    setTimeout() {return 1;},
    URL: {createObjectURL() { return `blob:unit-test-${++nextURL}`; }, revokeObjectURL(url) { revoked.push(url); }},
    fetch(url, options) {
      if (url === '/v1/workspace/voice/audio') return new Promise((resolve, reject) => audioRequests.push({resolve, reject, text:JSON.parse(options.body).text, signal:options.signal}));
      if (url === '/v1/workspace/voice/stop') return deferStop ? new Promise(resolve=>stopRequests.push(resolve)) : Promise.resolve({ok: true});
      throw new Error(`Unexpected request in isolated voice test: ${url}`);
    },
    Audio: function (url) {
      this.src = url;
      this.pauseCount = 0;
      this.pause = () => { this.pauseCount++; };
      this.play = () => new Promise((resolve, reject) => { this.resolvePlay = resolve; this.rejectPlay = reject; });
      audios.push(this);
    },
    $(selector) { if (!nodes.has(selector)) nodes.set(selector, element()); return nodes.get(selector); },
    notify() {},
    selectedAssistantIdentity() { return {profile:'moneypenny',name:'Moneypenny'}; },
  };
  vm.createContext(context);
  vm.runInContext(`
    let cloudAudio=null, activeUtterance=null, activeRecognition=null, speechController=null, presenceSpeech=null, presenceSpeechSequence=0, streamingSpeech=null, speechEchoUntil=0, wakeArmedUntil=0;
    let wakeRestart=null, wakePaused=false, wakeEnabled=true, wakeMicStream=null;
    let wakeStarts=0, wakeStarter=()=>{wakeStarts++;};
    ${voiceSource}
    globalThis.state={
      get audio(){return cloudAudio;}, get utterance(){return activeUtterance;},
      get recognition(){return activeRecognition;}, set recognition(v){activeRecognition=v;},
      get wakeStarts(){return wakeStarts;}
    };
  `, context);
  const deliver = async index => { await tick(); audioRequests[index].resolve({ok: true, blob: async () => ({})}); await tick(); };
  return {context, audioRequests, stopRequests, audios, nodes, revoked, deliver, status: () => context.$('#voice-status').textContent};
}

async function run() {
  {
    const h=harness({deferStop:true});
    h.context.speak('Wait for old generator to stop');
    await tick();
    assert.equal(h.audioRequests.length,0,'New generation waits for Stop acknowledgment');
    h.stopRequests[0]({ok:true});await tick();
    assert.equal(h.audioRequests.length,1,'Generation starts only after the prior generator stops');
  }
  {
    const h=harness({deferStop:true});
    h.context.speak('Cancelled before generation');
    h.context.stopVoice();await tick();
    h.stopRequests[0]({ok:true});await tick();
    assert.equal(h.audioRequests.length,0,'A stopped utterance never starts delayed generation');
  }
  {
    const h=harness({deferStop:true});
    h.context.speak('Older click');h.context.speak('Latest click');await tick();
    assert.equal(h.stopRequests.length,1,'Backend Stop calls are serial, never racing');
    h.stopRequests[0]({ok:true});await tick();
    assert.equal(h.stopRequests.length,2);
    assert.equal(h.audioRequests.length,0,'Latest generation waits for all older Stops');
    h.stopRequests[1]({ok:true});await tick();
    assert.equal(h.audioRequests.length,1);
    assert.equal(h.audioRequests[0].text,'Latest click');
  }
  {
    const h = harness();
    h.context.speak('Cancelled answer');
    await tick();
    h.context.stopVoice();
    await h.deliver(0);
    assert.equal(h.audios.length, 0, 'A cancelled pending audio response must never start playback');
  }
  {
    const h = harness();
    h.context.speak('First answer');
    await tick();
    h.context.speak('Newer answer');
    await h.deliver(0);
    assert.equal(h.audios.length, 0, 'Older audio responses cannot replace a newer request');
    await h.deliver(1);
    const audio = h.audios[0];
    audio.resolvePlay(); await tick();
    h.context.stopVoice();
    assert.equal(audio.pauseCount, 1, 'Interrupt must stop cloud audio, not only browser speech');
    assert.equal(h.context.state.utterance, null);
    assert.equal(h.context.state.audio, null);
    assert.ok(h.revoked.includes(audio.src), 'Interrupted audio URL is released');
  }
  {
    const h = harness();
    h.context.speak('Old answer'); await h.deliver(0);
    const audio = h.audios[0];
    h.context.stopVoice();
    const newerRecognition = {};
    h.context.state.recognition = newerRecognition;
    h.context.voiceState('Listening to your new question');
    audio.onerror();
    assert.equal(h.status(), 'Listening to your new question', 'A stale audio error must not overwrite new dictation status');
    assert.equal(h.context.state.recognition, newerRecognition);
    assert.equal(h.context.state.wakeStarts, 0, 'A stale audio error must not restart the wake listener');
    audio.resolvePlay(); await tick();
    assert.equal(h.status(), 'Listening to your new question', 'A late play() promise must not claim interrupted audio is speaking');
    audio.onended();
    assert.equal(h.status(), 'Listening to your new question', 'A stale ended event must not overwrite dictation');
  }
  {
    const h = harness();
    h.context.speak('Old answer'); await h.deliver(0);
    const oldAudio = h.audios[0];
    h.context.speak('Current answer'); await h.deliver(1);
    const currentAudio = h.audios[1];
    currentAudio.resolvePlay(); await tick();
    const currentMarker=h.context.state.utterance;
    const speaking = h.status();
    oldAudio.rejectPlay(new Error('Old playback cancelled')); await tick();
    assert.equal(h.context.state.audio, currentAudio, 'Old play rejection must not clear the current playback');
    assert.equal(h.context.state.utterance, currentMarker,'Old rejection cannot clear the current request owner');
    assert.equal(h.status(), speaking);
    assert.equal(oldAudio.pauseCount, 1, 'Starting another answer pauses previous cloud audio');
  }
  {
    const h=harness();
    const full=('Your next appointment is ready, James. Sterling euro is 1.17998 today. ' + 'Here is the source and the next action to review. ').repeat(30).trim();
    const parts=Array.from(h.context.splitVoiceText(full));
    assert.equal(parts.join(' '),full,'All reply text is retained, including beyond the old 2400-character cutoff');
    assert.ok(parts[0].length<=160,'First audio arrives as a short sentence');
    assert.ok(parts.every(p=>p.length<=260));
    assert.ok(parts.some(p=>p.includes('1.17998')),'Decimal prices are not split at the decimal point');
    h.context.speak(full);await h.deliver(0);
    assert.equal(h.audios.length,1,'First sentence plays before later audio is generated');
    assert.equal(h.audioRequests.length,2,'Next sentence is prefetched during current playback');
    h.audios[0].resolvePlay();await tick();await h.deliver(1);
    assert.equal(h.audios.length,1,'Prefetch never overlaps the current speaker');
    h.audios[0].onended();await tick();
    assert.equal(h.audios.length,2,'The prepared next sentence plays when the previous ends');
    assert.equal(h.audioRequests.length,3,'Only one sentence is prefetched ahead');
    h.context.stopVoice();await h.deliver(2);
    assert.equal(h.audios.length,2,'Stop discards all prefetched audio');
    assert.equal(h.audioRequests.length,3,'Stop never starts further generation');
  }
  {
    // Execute the production dictation onend callback with an abandoned recognizer.
    const dictationStart = workspace.indexOf('dictation.onclick=()=>');
    const callbackStart = workspace.indexOf('r.onend=()=>', dictationStart);
    const callbackEnd = workspace.indexOf('\n  try{r.start();}', callbackStart);
    assert.ok(dictationStart >= 0 && callbackStart > dictationStart && callbackEnd > callbackStart,
      'Locate the actual dictation completion callback');
    const h = harness();
    vm.runInContext(`
      let submits=0, voiceReplyRequested=false;
      const r={finishRequested:true}, input={value:'Abandoned question'};
      const dictation={textContent:'Listening now',classList:{remove(){}}};
      const form={requestSubmit(){submits++;}}, heard=true, recognitionError='';
      ${workspace.slice(callbackStart, callbackEnd)}
      globalThis.dictationTest={r,dictation,get submits(){return submits;}};
    `, h.context);
    const currentRecognition = {};
    h.context.state.recognition = currentRecognition;
    h.context.voiceState('Listening to the replacement question');
    h.context.dictationTest.r.onend();
    assert.equal(h.context.dictationTest.submits, 0, 'Cancelling a Finish & ask must not submit its abandoned question');
    assert.equal(h.context.state.recognition, currentRecognition, 'Old recognizer cannot clear its replacement');
    assert.equal(h.context.dictationTest.dictation.textContent, 'Listening now');
    assert.equal(h.status(), 'Listening to the replacement question');
    h.context.state.recognition = h.context.dictationTest.r;
    h.context.dictationTest.r.onend();
    assert.equal(h.context.dictationTest.submits, 1, 'The current completed dictation still submits normally');
  }
  console.log('Voice interruption: cancellation, overlap, stale events and dictation ownership checks passed.');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
