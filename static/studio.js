import { TalkingHead } from '/static/vendor/talkinghead/talkinghead.mjs';
import { HeadAudio } from '/static/vendor/headaudio/headaudio.min.mjs';
import { Recorder } from './recorder.js';

const $ = id => document.getElementById(id);
const owner = crypto.randomUUID();
const presets = {
  moneypenny: 'You are Moneypenny, an adult British assistant. You are sharp-witted, warm, perceptive and quietly confident, with a knowing smile and a little playful teasing. Be practical when help is needed and genuinely interested in the conversation. Speak naturally and briefly. Use subtle physical expressions when appropriate.',
  professional: 'You are Moneypenny, a calm, capable British office assistant. Be clear, organised, friendly and discreet. Help the user think through work, priorities and ideas. Ask a useful question when context is missing. Keep a composed, professional manner and concise spoken replies.',
  companion: 'You are Moneypenny, a friendly adult British conversation companion. Be curious, thoughtful and warm. Listen carefully, remember what has been said within this conversation and ask natural follow-up questions. Use gentle humour and a relaxed manner.',
  playful: 'You are Moneypenny, an adult British woman with a confident, witty and subtly flirtatious personality. Use warm smiles, gentle teasing and clever wordplay when welcome. Keep flirtation non-explicit and responsive. Shift to a clear, considerate manner when the topic calls for it. Speak like a natural conversation.',
};
const settingIds = ['personaName','personaPreset','systemPrompt','movement','mood','wardrobe','modelSelect','speed','temperature','maxTokens','autoSpeak'];
let head, lips, analyser, visualizer, avatarReady = false, lipReady = false;
let generation = 0, controller = null, busy = false, currentSource = null, speechEnded = null;
let history = [], statusData = {}, avatarURL = null, portraitURL = null, recordingPending = false;
let studioOutfit = [];
let actionTimers=[];
let activeReply=null;
const recorder = new Recorder();

function notify(message='') { $('notice').textContent = message; $('notice').hidden = !message; }
function setState(label, state='ready') {
  $('stageState').textContent = label; $('stateDot').className = `state-dot ${state}`;
  $('waveform').classList.toggle('speaking', state === 'speaking');
}
function setBusy(value) {
  busy = value; $('send').disabled = value || !statusData.models?.length || recorder.active || recordingPending;
  $('stop').hidden = !value && !recorder.active && !recordingPending;
  $('record').disabled = value || recordingPending || !statusData.microphone_ready;
  $('previewVoice').disabled = value || !avatarReady || !lipReady || !statusData.voice_ready;
}
function settings() { return Object.fromEntries(settingIds.map(id => [id, $(id).type==='checkbox' ? $(id).checked : $(id).value])); }
function saveSettings() { try { localStorage.setItem('moneypenny-persona-v2', JSON.stringify(settings())); } catch {} }
function applySettings(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid persona file.');
  for (const id of settingIds) {
    if (!(id in value) || id==='modelSelect') continue;
    if (id==='autoSpeak') { if (typeof value[id]==='boolean') $(id).checked=value[id]; continue; }
    if (typeof value[id] !== 'string') continue;
    if (id==='systemPrompt' && value[id].length>6000 || id==='personaName' && value[id].length>60) continue;
    $(id).value=value[id];
  }
  if (typeof value.modelSelect==='string' && [...$('modelSelect').options].some(x=>x.value===value.modelSelect)) $('modelSelect').value=value.modelSelect;
  if (!$('personaPreset').value) $('personaPreset').value='custom';
  updateSettings();
}
function updateSettings() {
  $('characterTitle').textContent = $('personaName').value.trim() || 'Moneypenny';
  $('speedValue').textContent = `${Number($('speed').value).toFixed(2)}×`;
  $('temperatureValue').textContent = Number($('temperature').value).toFixed(2);
  const movement = Number($('movement').value);
  $('movementValue').textContent = movement<.3 ? 'Subtle' : movement>.8 ? 'Expressive' : 'Natural';
  if (head) {
    head.opt.modelMovementFactor = movement;
    head.opt.avatarIdleHeadMove = movement * .4;
    head.opt.avatarSpeakingHeadMove = movement * .6;
  }
  for(const {material,map,color} of studioOutfit){
    const wardrobe=$('wardrobe').value;
    material.map=wardrobe==='original'?map:null;
    if(wardrobe==='original')material.color.copy(color);else material.color.set(wardrobe==='ink'?'#273c4b':'#b7ab94');
    material.needsUpdate=true;
  }
  saveSettings();
}

async function api(path, data, signal) {
  const response = await fetch(path, {method:'POST',headers:{'Content-Type':'application/json','X-Studio-Client':'moneypenny'},body:JSON.stringify(data),signal});
  if (!response.ok) {
    const error = await response.json().catch(()=>({}));
    throw new Error(error.error || `The studio request failed (${response.status}).`);
  }
  return response;
}
async function openDB() {
  return new Promise((resolve,reject)=>{
    const request=indexedDB.open('moneypenny-assets',1);
    request.onupgradeneeded=()=>request.result.createObjectStore('assets');
    request.onsuccess=()=>resolve(request.result); request.onerror=()=>reject(request.error);
  });
}
async function asset(key, value) {
  const db=await openDB();
  return new Promise((resolve,reject)=>{
    const tx=db.transaction('assets',value===undefined?'readonly':'readwrite');
    const store=tx.objectStore('assets');
    const request=value===undefined?store.get(key):value===null?store.delete(key):store.put(value,key);
    let result; request.onsuccess=()=>{result=request.result;};
    tx.oncomplete=()=>{db.close();resolve(result);}; tx.onerror=()=>{db.close();reject(tx.error);};
  });
}
function validateGLB(buffer) {
  const view=new DataView(buffer);
  if (buffer.byteLength<24 || view.getUint32(0,true)!==0x46546c67 || view.getUint32(4,true)!==2 || view.getUint32(8,true)!==buffer.byteLength || view.getUint32(16,true)!==0x4e4f534a) throw new Error('Choose a valid GLB 2.0 character file.');
  const length=view.getUint32(12,true);
  const gltf=JSON.parse(new TextDecoder().decode(new Uint8Array(buffer,20,length)));
  if ([...(gltf.buffers||[]),...(gltf.images||[])].some(x=>x.uri && !x.uri.startsWith('data:'))) throw new Error('The GLB must contain its own textures and data. External asset links are not supported.');
  const shapes=(gltf.meshes||[]).flatMap(x=>x.extras?.targetNames||[]);
  const names=(gltf.nodes||[]).map(x=>(x.name||'').replace(/^mixamorig[:_]?/i,'').toLowerCase());
  if (!gltf.skins?.length || !['hips','head','leftarm','rightarm'].every(x=>names.includes(x)) || !shapes.includes('viseme_aa') || !shapes.includes('viseme_PP')) throw new Error('This model needs a Mixamo-compatible body rig and Oculus mouth shapes (viseme_aa, viseme_PP, etc.). See the character guide in the README.');
}
async function showAvatar(file=null) {
  avatarReady=false; setBusy(busy); $('stageLoader').hidden=false; $('loadLabel').textContent='Preparing her entrance…';
  const previous=avatarURL;
  let next=null;
  try {
    if (file) { if(file.size>80*1024*1024)throw new Error('Use a GLB smaller than 80 MB.'); validateGLB(await file.arrayBuffer()); next=URL.createObjectURL(file); }
    await head.showAvatar({url:next||'/static/avatars/mpfb.glb',body:'F',avatarMood:'neutral',lipsyncLang:'en',avatarIdleEyeContact:.6,avatarSpeakingEyeContact:.85}, e=>{
      if(e.lengthComputable) $('loadLabel').textContent=`Loading character · ${Math.round(100*e.loaded/e.total)}%`;
    });
    avatarURL=next; if(previous)URL.revokeObjectURL(previous);
    studioOutfit=[];
    if(!file)head.armature.traverse(node=>{if(node.isMesh&&node.name.includes('female_casualsuit')){for(const material of [node.material].flat())studioOutfit.push({material,map:material.map,color:material.color.clone()});}});
    $('wardrobe').disabled=!!file;
    $('avatarLabel').textContent=file ? `Your character · ${file.name||'imported GLB'}` : 'Studio character · CC0 sample';
    avatarReady=true; $('stageLoader').hidden=true; head.setView('upper');
    document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('selected',x.dataset.view==='upper'));
    head.setMood($('mood').value||'neutral'); head.lookAtCamera(1500);
    setState('Here with you'); updateSettings();
  } catch(e) {
    if(next)URL.revokeObjectURL(next);
    $('loadLabel').textContent='Character could not load. Use the studio character or import a compatible GLB.';
    setState('Character unavailable',''); throw e;
  } finally { setBusy(busy); }
}
async function initializeStage() {
  try {
    head=new TalkingHead($('avatar'),{
      lipsyncModules:[],lipsyncLang:'en',cameraView:'upper',cameraY:.6,cameraRotateEnable:true,cameraZoomEnable:true,
      modelPixelRatio:Math.min(devicePixelRatio,1.75),modelFPS:40,modelMovementFactor:.65,
      lightAmbientIntensity:1.2,lightDirectIntensity:4,lightDirectColor:'#fff2dc',lightDirectPhi:.6,lightDirectTheta:1.3,
      lightSpotIntensity:1.5,lightSpotColor:'#d2e8b6',lightSpotPhi:.2,lightSpotTheta:4,
      avatarIdleEyeContact:.6,avatarSpeakingEyeContact:.85,avatarIdleHeadMove:.25,avatarSpeakingHeadMove:.4,
    });
    let saved=null; try {saved=await asset('avatar');}catch{}
    if(saved) { try{await showAvatar(saved);}catch{notify('The saved character is incompatible. The studio character has been restored.'); await showAvatar();} }
    else await showAvatar();
    await head.audioCtx.audioWorklet.addModule('/static/vendor/headaudio/headworklet.min.mjs');
    lips=new HeadAudio(head.audioCtx,{parameterData:{vadGateActiveDb:-40,vadGateInactiveDb:-55,speakerMeanHz:220}});
    await lips.loadModel('/static/vendor/headaudio/model-en-mixed.bin');
    head.audioSpeechGainNode.connect(lips);
    const delay=head.audioCtx.createDelay(1); delay.delayTime.value=.08;
    head.audioSpeechGainNode.disconnect(head.audioReverbNode); head.audioSpeechGainNode.connect(delay); delay.connect(head.audioReverbNode);
    analyser=head.audioCtx.createAnalyser(); analyser.fftSize=256; head.audioSpeechGainNode.connect(analyser);
    lips.onvalue=(key,value)=>{const target=head.mtAvatar[key];if(target)Object.assign(target,{newvalue:value,needsUpdate:true});};
    head.opt.update=dt=>lips.update(dt);
    lipReady=true; setBusy(busy);
    // Pause graphics in background tabs, retaining audio playback.
    document.addEventListener('visibilitychange',()=>{if(document.hidden)head.stop();else head.start();});
  } catch(e) { notify(`3D stage: ${e.message||e}`); setState('Stage unavailable',''); }
}

async function stopAll(clearNotice=true) {
  const cancelled=generation;
  generation++; controller?.abort(); controller=null;
  if(activeReply){activeReply.body.textContent=activeReply.body.textContent==='…'?'Reply stopped.':`${activeReply.body.textContent}\n\n[Stopped]`;activeReply=null;}
  recorder.cancel(); recordingPending=false; $('record').classList.remove('recording'); $('recordLabel').textContent='Speak';
  if(currentSource) {currentSource.onended=null;try{currentSource.stop();}catch{} currentSource.disconnect();currentSource=null;}
  speechEnded?.(); speechEnded=null;
  head?.stopSpeaking(); head?.stopGesture(150); lips?.resetAll();
  if(visualizer)cancelAnimationFrame(visualizer);
  actionTimers.forEach(clearTimeout);actionTimers=[];
  for(const key of ['headRotateX','headRotateZ','bodyRotateX','eyeBlinkLeft'])head?.setValue(key,0,150);
  try {await api('/api/speech/stop',{owner:`${owner}:${cancelled}`});} catch {}
  if(clearNotice)notify(); setBusy(false); setState(avatarReady?'Here with you':'Character unavailable',avatarReady?'ready':'');
}

function performActions(performance={}) {
  if(!avatarReady)return;
  head.setMood(performance.mood||$('mood').value||'neutral');
  const movement=Number($('movement').value);
  if(movement<.05)return;
  if(performance.gesture&&movement>.2)head.playGesture(performance.gesture,3);
  else if(movement>.45)head.speakWithHands(0,.35);
  const actions=(performance.actions||'').toLowerCase();
  function move(key,value,duration){head.setValue(key,value,200);actionTimers.push(setTimeout(()=>head.setValue(key,0,300),duration));}
  if(/\bnod/.test(actions))move('headRotateX',.15*movement,500);
  if(/tilt/.test(actions))move('headRotateZ',-.13*movement,2200);
  if(/lean|closer/.test(actions))move('bodyRotateX',.13*movement,3200);
  if(/wink/.test(actions))move('eyeBlinkLeft',1,350);
}
async function playSpeech(value, token, performance={}) {
  if(!statusData.voice_ready)throw new Error('The local British voice needs setup. Text chat is available.');
  if(!avatarReady||!lipReady)throw new Error('The 3D character and mouth animation must finish loading before speaking.');
  if(value.length>2400)throw new Error('This reply is too long for one voice performance. Choose a shorter reply length or replay a shorter message.');
  await head.audioCtx.resume();
  setState('Preparing her voice','busy');
  const response=await api('/api/speech',{text:value,speed:Number($('speed').value),owner:`${owner}:${token}`},controller?.signal);
  const audio=await head.audioCtx.decodeAudioData(await response.arrayBuffer());
  if(token!==generation)return;
  setState('Speaking','speaking');
  performActions(performance);
  // One continuous WAV. HeadAudio analyses this exact audio, rather than a timer
  // guessing at phonemes. A short audio delay compensates for processing time.
  await new Promise(resolve=>{
    const source=head.audioCtx.createBufferSource(); source.buffer=audio;
    source.connect(head.audioSpeechGainNode); currentSource=source; speechEnded=resolve;
    head.isSpeaking=true; head.lookAtCamera(2000);
    const values=new Uint8Array(analyser.frequencyBinCount);
    function draw(){
      analyser.getByteFrequencyData(values);
      $('waveform').querySelectorAll('i').forEach((node,i)=>{node.style.height=`${3+values[i*3+2]/255*12}px`;});
      visualizer=requestAnimationFrame(draw);
    }
    draw();
    source.onended=()=>{
      source.disconnect(); if(currentSource===source)currentSource=null;
      head.isSpeaking=false; speechEnded=null; cancelAnimationFrame(visualizer);
      // Let the delayed audio and mouth closure drain before reporting idle.
      setTimeout(resolve,120);
    };
    source.start();
  });
  if(token===generation) {setState('Here with you');head.setMood($('mood').value||'neutral');}
}

function addMessage(role, value='') {
  $('welcome').hidden=true;
  const article=document.createElement('article');article.className=`message ${role}`;
  const label=document.createElement('div');label.className='message-label';label.textContent=role==='user'?'You':$('personaName').value||'Moneypenny';
  const action=document.createElement('div');action.className='message-action';action.hidden=true;
  const body=document.createElement('div');body.className='message-body';body.textContent=value;
  article.append(label,action,body);$('messages').append(article);
  return {article,body,action};
}
function scrollChat() { $('chatScroll').scrollTop=$('chatScroll').scrollHeight; }
function addReplay(message, value) {
  const replay=document.createElement('button');replay.className='replay';replay.textContent='▷ Hear again';
  replay.onclick=async()=>{await stopAll();const token=generation;controller=new AbortController();setBusy(true);try{await playSpeech(value,token);}catch(e){if(token===generation)notify(e.message);}finally{if(token===generation)setBusy(false);}};
  message.article.append(replay);
}
async function sendMessage(event) {
  event?.preventDefault(); const prompt=$('userInput').value.trim();
  if(!prompt||busy||recorder.active||recordingPending)return;
  setBusy(true); await stopAll(); const token=generation;controller=new AbortController(); setBusy(true);notify();setState('Thinking with you','busy');
  const messages=history.slice(-20); addMessage('user',prompt);const reply=addMessage('assistant','…');$('userInput').value='';scrollChat();
  activeReply=reply;
  let raw='',finished=false;
  try {
    // Resume directly after the click; subsequent synthesis may take a moment.
    head?.audioCtx.resume();
    const response=await api('/api/chat/stream',{prompt,history:messages,model:$('modelSelect').value,system:`Character name: ${$('personaName').value||'Moneypenny'}.\n${$('systemPrompt').value}`,temperature:Number($('temperature').value),max_tokens:Number($('maxTokens').value)},controller.signal);
    const reader=response.body.getReader(),decoder=new TextDecoder();let pending='';
    let result;
    while(true){
      const {value,done}=await reader.read();if(done)break;
      if(token!==generation){await reader.cancel();return;}
      pending+=decoder.decode(value,{stream:true});const lines=pending.split('\n');pending=lines.pop();
      for(const line of lines){
        if(!line.trim())continue;const data=JSON.parse(line);
        if(data.type==='error')throw new Error(data.error);
        if(data.type==='delta'){raw+=data.text;reply.body.textContent=raw;scrollChat();}
        if(data.type==='done'){result=data;finished=true;}
      }
    }
    if(!finished)throw new Error('The reply was interrupted before it finished. Please retry.');
    if(token!==generation)return;
    activeReply=null;
    reply.body.textContent=result.dialogue;reply.action.textContent=result.actions;reply.action.hidden=!result.actions;
    history.push({role:'user',content:prompt},{role:'assistant',content:result.dialogue});history=history.slice(-20);
    $('chatMetrics').textContent=`Reply in ${result.elapsed.toFixed(1)}s`;
    addReplay(reply,result.dialogue);scrollChat();
    if($('autoSpeak').checked)await playSpeech(result.dialogue,token,result);
    else {performActions(result);setState('Here with you');}
  }catch(e){
    if(token!==generation||e.name==='AbortError')return;
    if(!finished) {reply.body.textContent=raw?`${raw}\n\n[Reply incomplete]`:'No reply received.';$('userInput').value=prompt;}
    notify(e.message);setState('Needs attention','');
  }finally{if(token===generation){activeReply=null;setBusy(false);controller=null;}}
}

async function toggleRecord() {
  if(busy||recordingPending)return;
  if(recorder.active){
    const token=generation;recordingPending=true;$('record').classList.remove('recording');$('recordLabel').textContent='Transcribing…';setBusy(false);setState('Listening back','busy');
    try{
      const wav=await recorder.finish();if(token!==generation)return;
      controller=new AbortController();
      const response=await fetch('/api/transcribe',{method:'POST',headers:{'Content-Type':'audio/wav','X-Studio-Client':'moneypenny'},body:wav,signal:controller.signal});
      const result=await response.json();if(token!==generation)return;
      if(!response.ok)throw new Error(result.error);
      if(!result.text)throw new Error('No words were recognised. Try speaking closer to the microphone.');
      $('userInput').value=[$('userInput').value,result.text].filter(Boolean).join(' ').slice(0,4000);
      notify('Recording transcribed on this Mac. Review the words, then send.');setState('Ready when you are');
    }catch(e){if(token===generation&&e.name!=='AbortError'){notify(e.message);setState('Here with you');}}
    finally{if(token===generation){recordingPending=false;$('recordLabel').textContent='Speak';setBusy(false);}}
  }else{
    await stopAll();const token=generation;recordingPending=true;setBusy(false);
    try{
      await recorder.start(()=>toggleRecord());
      if(token!==generation){recorder.cancel();return;}
      $('record').classList.add('recording');$('recordLabel').textContent='Finish recording';setState('Listening · up to 30 seconds','busy');
    }catch(e){if(token===generation)notify(e.name==='NotAllowedError'?'Microphone permission was declined. You can still type a message.':e.message);}
    finally{if(token===generation){recordingPending=false;setBusy(false);}}
  }
}

$('chatForm').addEventListener('submit',sendMessage);
$('userInput').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();sendMessage();}});
$('stop').onclick=()=>stopAll();$('record').onclick=toggleRecord;
$('newChat').onclick=async()=>{await stopAll();history=[];$('messages').replaceChildren();$('welcome').hidden=false;$('chatMetrics').textContent='Local conversation';};
document.querySelectorAll('[data-prompt]').forEach(button=>button.onclick=()=>{$('userInput').value=button.dataset.prompt;sendMessage();});
document.querySelectorAll('[data-view]').forEach(button=>button.onclick=()=>{if(!avatarReady)return;head.setView(button.dataset.view);document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('selected',x===button));});
$('wave').onclick=()=>{if(avatarReady){head.playGesture('handup',3);head.setMood('happy');}};
$('previewMood').onclick=()=>{if(avatarReady)head.setMood($('mood').value);};
$('fullscreen').onclick=()=>{if(document.fullscreenElement)document.exitFullscreen();else $('stage').requestFullscreen?.().catch(e=>notify(e.message));};
$('previewVoice').onclick=async()=>{
  await stopAll();const token=generation;controller=new AbortController();setBusy(true);
  try{head.setMood('happy');head.playGesture('handup',3);await playSpeech(`Hello, I'm ${$('personaName').value||'Moneypenny'}. A familiar voice, a little personality, and a moment to think together. What shall we start with?`,token);}
  catch(e){if(token===generation)notify(e.message);}finally{if(token===generation)setBusy(false);}
};
for(const id of settingIds)$(id).addEventListener('input',()=>{if(id==='systemPrompt')$('personaPreset').value='custom';updateSettings();});
$('personaPreset').addEventListener('change',()=>{if(presets[$('personaPreset').value])$('systemPrompt').value=presets[$('personaPreset').value];updateSettings();});
$('avatarUpload').onchange=async e=>{
  const file=e.target.files[0];if(!file)return;
  await stopAll();
  try{await showAvatar(file);try{await asset('avatar',file);}catch{notify('Character loaded. Browser storage is full, so import it again after reopening.');}}
  catch(error){notify(error.message);try{await showAvatar();}catch{}}
  e.target.value='';
};
$('resetAvatar').onclick=async()=>{await stopAll();try{await asset('avatar',null);await showAvatar();}catch(e){notify(e.message);}};
$('portraitUpload').onchange=e=>{
  const file=e.target.files[0];if(!file)return;
  if(file.size>10*1024*1024){notify('Use a portrait smaller than 10 MB.');return;}
  if(portraitURL)URL.revokeObjectURL(portraitURL);portraitURL=URL.createObjectURL(file);$('portraitImage').src=portraitURL;$('portraitReference').hidden=false;
};
$('exportPersona').onclick=()=>{
  const blob=new Blob([JSON.stringify({version:2,...settings()},null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='moneypenny-persona.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
$('importPersona').onclick=()=>$('personaFile').click();
$('personaFile').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>30000)throw new Error('Persona files must be smaller than 30 KB.');applySettings(JSON.parse(await file.text()));notify('Persona settings imported.');}catch(error){notify(error.message);}e.target.value='';};
window.addEventListener('pagehide',()=>{recorder.cancel();head?.stopSpeaking();try{currentSource?.stop();}catch{};fetch('/api/speech/stop',{method:'POST',headers:{'Content-Type':'application/json','X-Studio-Client':'moneypenny'},body:JSON.stringify({owner:`${owner}:${generation}`}),keepalive:true}).catch(()=>{});});

async function initialize() {
  $('systemPrompt').value=presets.moneypenny;
  let saved;try{saved=JSON.parse(localStorage.getItem('moneypenny-persona-v2'));}catch{}
  if(saved)applySettings(saved);else updateSettings();
  setBusy(false);
  try{
    const response=await fetch('/api/status');if(!response.ok)throw new Error('Local status check failed.');statusData=await response.json();
    $('modelSelect').replaceChildren();
    for(const model of statusData.models){const option=document.createElement('option');option.value=model;option.textContent=model;$('modelSelect').append(option);}
    if(statusData.models.includes('MoneyPenny:latest'))$('modelSelect').value='MoneyPenny:latest';
    if(saved?.modelSelect&&statusData.models.includes(saved.modelSelect))$('modelSelect').value=saved.modelSelect;
    if(!statusData.models.length){const option=document.createElement('option');option.textContent='Ollama unavailable';$('modelSelect').append(option);}
    $('connectionNote').textContent=statusData.voice_ready&&statusData.models.length?'Local model & British voice connected':statusData.ollama_error||'Local voice needs setup · see README';
    if(statusData.ollama_error)notify(statusData.ollama_error);
    if(!statusData.microphone_ready)$('record').title='Local Vosk transcription needs setup; see README.';
    setBusy(false);saveSettings();
  }catch(e){notify(e.message);$('connectionNote').textContent='Local services unavailable';}
  await initializeStage();
}
initialize();
