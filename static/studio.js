import { TalkingHead } from './vendor/talkinghead/talkinghead.mjs';
import { HeadAudio } from './vendor/headaudio/headaudio.min.mjs';
import { Recorder } from './recorder.js';
import * as THREE from 'three';
import { MotionDirector, movementFromText } from './motion.js';
import { Wardrobe } from './wardrobe.js';
import { LiveSession, SpeechSegmenter, SpeechPipeline, controlIntent } from './live.js';

import { RigController, authoredNeutral } from './rig.js';
import { RigView } from './rig-view.js';
import { MotionLibrary } from './motion-library.js';
import { StudioTools } from './studio-tools.js';
import { prepareSampleMaterials, prepareCharacterMaterials, setLook, setHairTone } from './appearance.js';
import { PoseCorrectives } from './correctives.js';
import { SeatSupport } from './seat-support.js';
import { actionOnly, movementAcknowledgement, wardrobeCommand } from './action-commands.js';
import { chooseModel } from './model-choice.js';
import { renderProfile,StageActivity } from './render-budget.js';
import { studioFetch as fetch,studioURL,parentOrigins,STUDIO_BASE } from './studio-paths.js';
import {PresenceAudio} from './presence-audio.js';

const $ = id => document.getElementById(id);
const jarvisEmbed=new URLSearchParams(location.search).get('embed')==='jarvis';
const proxiedPresence=jarvisEmbed&&STUDIO_BASE==='/presence/';
const jarvisOrigins=parentOrigins();
const defaultParentOrigin=jarvisOrigins.includes(location.origin)?location.origin:jarvisOrigins[0];
let jarvisParentOrigin=(()=>{try{const origin=new URL(document.referrer).origin;return jarvisOrigins.includes(origin)?origin:defaultParentOrigin;}catch{return defaultParentOrigin;}})();
function postPresence(type,detail={}){if(jarvisEmbed&&parent!==window)parent.postMessage({type,...detail},jarvisParentOrigin);}
const owner = crypto.randomUUID();
const presets = {
  moneypenny: 'You are Moneypenny, an adult British assistant. You are sharp-witted, warm, perceptive and quietly confident, with a knowing smile and a little playful teasing. Be practical when help is needed and genuinely interested in the conversation. Speak naturally and briefly. Use subtle physical expressions when appropriate.',
  professional: 'You are Moneypenny, a calm, capable British office assistant. Be clear, organised, friendly and discreet. Help the user think through work, priorities and ideas. Ask a useful question when context is missing. Keep a composed, professional manner and concise spoken replies.',
  companion: 'You are Moneypenny, a friendly adult British conversation companion. Be curious, thoughtful and warm. Listen carefully, remember what has been said within this conversation and ask natural follow-up questions. Use gentle humour and a relaxed manner.',
  playful: 'You are Moneypenny, an adult British woman with a confident, witty and subtly flirtatious personality. Use warm smiles, gentle teasing and clever wordplay when welcome. Keep flirtation non-explicit and responsive. Shift to a clear, considerate manner when the topic calls for it. Speak like a natural conversation.',
};
const settingIds = ['personaName','personaPreset','systemPrompt','movement','mood','wardrobe','footwear','blouseColor','hairTone','lightingLook','lightBrightness','autonomy','aiMotion','activity','behaviourPrompt','modelSelect','speed','mouthTiming','temperature','maxTokens','autoSpeak'];
let head, lips, analyser, visualizer, avatarReady = false, lipReady = false;
let generation = 0, controller = null, busy = false, currentSource = null, speechEnded = null;
let history = [], statusData = {}, avatarURL = null, portraitURL = null, recordingPending = false;
let studioOutfit = [],disposeAppearance=null;
let actionTimers=[];
let activeReply=null;
let motion=null,wardrobe=null,liveSession=null,speechGate=null,speechDelay=null,userSpeaking=false,listenEpoch=0,liveTranscription=null,interruption=Promise.resolve();
let quietUntil=Number(localStorage.getItem('moneypenny-quiet-until')||0),reminderPolling=false;
let turnStarted=0,firstVoiceAt=0;
let rig=null,rigView=null,motionLibrary=null,tools=null,poseCorrectives=null,seatSupport=null;
let stageActivity=null,parentStageVisible=true,renderFrames=0;
let presenceAudio=null;
const recorder = new Recorder();

function notify(message='') { $('notice').textContent = message; $('notice').hidden = !message; }
function setState(label, state='ready') {
  $('stageState').textContent = label; $('stateDot').className = `state-dot ${state}`;
  $('waveform').classList.toggle('speaking', state === 'speaking');
}
function setBusy(value) {
  for(const id of ['playMotion','pauseMotion','stopLibraryMotion','pinFeet','releaseTarget','resetRig','planMotion','stopMotion','previewSeatPose'])$(id).disabled=!avatarReady;
  busy = value; $('send').disabled = value || !statusData.models?.length || recorder.active || recordingPending;
  stageActivity?.update({active:value||!!head?.isSpeaking||!!motion?.active||!!motionLibrary?.playing});
  $('stop').hidden = !value && !recorder.active && !recordingPending;
  $('record').disabled = value || recordingPending || !statusData.microphone_ready || !!liveSession?.active;
  $('previewVoice').disabled = value || !avatarReady || !lipReady || !statusData.voice_ready;
}
function settings() { return Object.fromEntries(settingIds.map(id => [id, $(id).type==='checkbox' ? $(id).checked : $(id).value])); }
function saveSettings() { if(jarvisEmbed)return;try { localStorage.setItem('moneypenny-persona-v2', JSON.stringify(settings())); } catch {} }
function applySettings(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid persona file.');
  for (const id of settingIds) {
    if (!(id in value) || id==='modelSelect') continue;
    if ($(id).type==='checkbox') { if (typeof value[id]==='boolean') $(id).checked=value[id]; continue; }
    if (typeof value[id] !== 'string') continue;
    if (id==='systemPrompt' && value[id].length>6000 || id==='personaName' && value[id].length>60) continue;
    $(id).value=value[id];
  }
  if (typeof value.modelSelect==='string' && [...$('modelSelect').options].some(x=>x.value===value.modelSelect)) $('modelSelect').value=value.modelSelect;
  if (!$('personaPreset').value) $('personaPreset').value='custom';
  if(!$('wardrobe').value)$('wardrobe').value='casual';
  updateSettings();
}
function updateSettings() {
  $('characterTitle').textContent = $('personaName').value.trim() || 'Moneypenny';
  $('speedValue').textContent = `${Number($('speed').value).toFixed(2)}×`;
  $('mouthTimingValue').textContent = `${Number($('mouthTiming').value)} ms`;
  if(speechDelay)speechDelay.delayTime.setTargetAtTime(Number($('mouthTiming').value)/1000,head.audioCtx.currentTime,.04);
  $('temperatureValue').textContent = Number($('temperature').value).toFixed(2);
  const movement = Number($('movement').value);
  $('movementValue').textContent = movement<.3 ? 'Subtle' : movement>.8 ? 'Expressive' : 'Natural';
  if (head) {
    head.opt.modelMovementFactor = movement;
    head.opt.avatarIdleHeadMove = movement * .4;
    head.opt.avatarSpeakingHeadMove = movement * .6;
    setLook(head,$('lightingLook').value,$('lightBrightness').value);
    if(head.studioNeutral&&head.armature)setHairTone(head.armature,$('hairTone').value);
  }
  if(statusData.models?.length)$('connectionNote').textContent=`${$('modelSelect').value} · ${statusData.voice_ready?'British voice connected':'voice needs setup'}`;
  wardrobe?.set($('wardrobe').value,$('footwear').value);
  wardrobe?.setPalette($('blouseColor').value);
  if(motion){motion.autonomous=$('autonomy').checked;motion.activity=Number($('activity').value);motion.persona=$('behaviourPrompt').value+' '+$('systemPrompt').value;}
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
function frameCharacter(view,plan=null) {
  const lying=plan?.steps?.some(step=>step.skill==='lie_back');
  const low=plan?.steps?.some(step=>['splits','kneel','sit'].includes(step.skill));
  const embeddedPortrait=jarvisEmbed&&view==='upper';
  head.setView(view,{cameraY:view==='full'?(lying?.75:low?.35:0):embeddedPortrait?.78:.6,cameraDistance:view==='head'?.8:embeddedPortrait?.25:0,cameraRotateX:lying?-.35:0});
  document.querySelectorAll('[data-view]').forEach(button=>button.classList.toggle('selected',button.dataset.view===view));
}
async function showAvatar(file=null, localCharacter=null) {
  avatarReady=false; setBusy(busy); $('stageLoader').hidden=false; $('loadLabel').textContent='Preparing her entrance…';
  const previous=avatarURL;
  let next=null;
  try {
    if (file) { if(file.size>80*1024*1024)throw new Error('Use a GLB smaller than 80 MB.'); validateGLB(await file.arrayBuffer()); next=URL.createObjectURL(file); }
    wardrobe?.dispose();rigView?.dispose();motionLibrary?.dispose();seatSupport?.dispose();disposeAppearance?.();disposeAppearance=null;
    head.studioNeutral=null;
    await head.showAvatar({url:next||studioURL(localCharacter?.url||'/static/avatars/mpfb.glb'),body:'F',avatarMood:'neutral',lipsyncLang:'en',avatarIdleEyeContact:.6,avatarSpeakingEyeContact:.85}, e=>{
      if(e.lengthComputable) $('loadLabel').textContent=`Loading character · ${Math.round(100*e.loaded/e.total)}%`;
    },gltf=>{if(localCharacter)head.studioNeutral=authoredNeutral(gltf.scene);});
    avatarURL=next; if(previous)URL.revokeObjectURL(previous);
    rig=new RigController(head,value=>{$('rigState').textContent=value;});
    rigView=new RigView(head,rig,(name,target,held)=>tools?.rigChanged(name,target,held));
    rigView.show($('showRig').checked);rigView.select($('rigTarget').value);
    motionLibrary=new MotionLibrary(head,rig,value=>{$('libraryState').textContent=value;});
    poseCorrectives=new PoseCorrectives(head.armature);
    seatSupport=new SeatSupport(head.scene,rig);
    try{motionLibrary.mapping=JSON.parse(localStorage.getItem('moneypenny-bone-map')||'{}');}catch{}
    motion=new MotionDirector(head,value=>{$('motionState').textContent=value;},rig);
    tools?.refreshMotions().catch(error=>notify(error.message));
    motion.onChoosePlan=async()=>{
      if(busy||userSpeaking||document.hidden||!$('autonomy').checked)return;
      const choices=motionLibrary.items.filter(item=>motionLibrary.autoIds.includes(item.id));
      if(choices.length&&!$('aiMotion').checked&&!head.studioNeutral){motion.queue=[];motion.active=null;motion.nextDecision=motion.clock+20+(1-motion.activity)*20;motionLibrary.loop=false;try{await motionLibrary.play(choices[Math.floor(Math.random()*choices.length)].id,0,'persona');}catch{}return;}
      // The embedded face shares JJRVIS's answer model; local idle motion needs no competing model load.
      if(jarvisEmbed||!$('aiMotion').checked||!$('modelSelect').value)return;
      const epoch=generation,persona=$('behaviourPrompt').value;
      try{
        const plan=await(await api('/api/motion/plan',{prompt:'Choose one short physical activity for yourself now, based on your movement personality and recent conversation. Use custom keyframes for original gestures, or an existing skill. Recent conversation: '+history.slice(-2).map(x=>x.content).join(' ').slice(0,600),persona,model:$('modelSelect').value})).json();
        if(epoch===generation&&!busy&&!userSpeaking&&$('autonomy').checked)motion.plan(plan,'persona');
      }catch{};
    };
    wardrobe=new Wardrobe(head);
    motionLibrary.onProgress=(time,duration)=>{$('motionPosition').disabled=false;$('motionPosition').max=String(duration);if(document.activeElement!==$('motionPosition'))$('motionPosition').value=String(time);$('motionTime').textContent=`${time.toFixed(1)} / ${duration.toFixed(1)} s`;};
    motionLibrary.onCue=cue=>{try{wardrobe.setGarment(cue.garment,cue.visible);const garment=wardrobe.garments().find(item=>item.id===cue.garment);$('cueState').textContent=`${garment?.name||cue.garment} ${cue.visible?'visible':'removed'} at ${cue.at}s`;}catch(error){notify(error.message);}};
    try{motionLibrary.autoIds=JSON.parse(localStorage.getItem('moneypenny-autonomous-clips')||'["studio-stretch"]');motionLibrary.aliasOverrides=JSON.parse(localStorage.getItem('moneypenny-motion-aliases')||'{}');motionLibrary.cueOverrides=JSON.parse(localStorage.getItem('moneypenny-garment-cues')||'{}');}catch{}
    tools?.refreshGarments();
    if(!file&&!localCharacter)disposeAppearance=prepareSampleMaterials(head.armature);
    else if(localCharacter)prepareCharacterMaterials(head.armature,head.renderer);
    setLook(head,$('lightingLook').value,$('lightBrightness').value);
    studioOutfit=[];
    if(!file&&!localCharacter)head.armature.traverse(node=>{if(node.isMesh&&node.name.includes('female_casualsuit')){for(const material of [node.material].flat())studioOutfit.push({material,map:material.map,color:material.color.clone()});}});
    const fitted=!!file||!!localCharacter;
    $('wardrobe').disabled=fitted;$('footwear').disabled=fitted;
    $('avatarLabel').textContent=file ? `Your character · ${file.name||'imported GLB'}` : localCharacter?.label||'Studio character · CC0 sample';
    avatarReady=true; $('stageLoader').hidden=true; frameCharacter('upper');
    stageActivity?.update();
    document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('selected',x.dataset.view==='upper'));
    head.setMood($('mood').value||'neutral'); head.lookAtCamera(1500);
    setState('Here with you'); updateSettings();
  } catch(e) {
    if(next)URL.revokeObjectURL(next);
    $('loadLabel').textContent='Character could not load. Use the studio character or import a compatible GLB.';
    setState('Character unavailable',''); throw e;
  } finally { setBusy(busy); }
}
const appearanceIds=['blouseColor','hairTone','lightingLook','lightBrightness'];
let appearanceSnapshot='',appearanceSaveTimer=null;
async function syncAppearance(){
 try{
  const next=await(await api('/api/appearance')).json(),key=JSON.stringify(next);if(key===appearanceSnapshot)return;appearanceSnapshot=key;
  for(const id of appearanceIds)if(typeof next[id]==='string')$(id).value=next[id];
  if(head){setLook(head,$('lightingLook').value,$('lightBrightness').value);setHairTone(head.armature,$('hairTone').value);wardrobe?.setPalette($('blouseColor').value);}
 }catch{/* Keep the current appearance when the connection is unavailable. */}
}
function saveAppearance(){
 if(jarvisEmbed)return;clearTimeout(appearanceSaveTimer);appearanceSaveTimer=setTimeout(async()=>{try{const next=Object.fromEntries(appearanceIds.map(id=>[id,$(id).value]));await api('/api/appearance',next);appearanceSnapshot=JSON.stringify(next);}catch{notify('This appearance change could not be saved. Your current preview remains available.');}},400);
}
async function initializeStage() {
  try {
    await syncAppearance();
    const profile=renderProfile({pixelRatio:devicePixelRatio,narrow:matchMedia('(max-width:760px)').matches,embedded:jarvisEmbed});
    head=new TalkingHead($('avatar'),{
      lipsyncModules:[],lipsyncLang:'en',cameraView:'upper',cameraY:.6,cameraRotateEnable:true,cameraZoomEnable:false,
      dracoDecoderPath:studioURL('/vendor/three/examples/jsm/libs/draco/'),
      // TalkingHead multiplies this scale by the display's pixel ratio itself.
      modelPixelRatio:profile.pixelRatioScale,modelFPS:profile.activeFPS,modelMovementFactor:.65,
      lightAmbientIntensity:.65,lightDirectIntensity:2.4,lightDirectColor:'#fff2e6',lightDirectPhi:.8,lightDirectTheta:1.1,
      lightSpotIntensity:1.1,lightSpotColor:'#d9e5ef',lightSpotPhi:.3,lightSpotTheta:4,
      avatarIdleEyeContact:.6,avatarSpeakingEyeContact:.85,avatarIdleHeadMove:.25,avatarSpeakingHeadMove:.4,
    });
    head.renderer.setClearColor(0x000000,0);head.scene.background=null;
    head.renderer.toneMappingExposure=.85;
    head.renderer.shadowMap.enabled=profile.shadows;head.renderer.shadowMap.type=THREE.PCFSoftShadowMap;
    head.lightDirect.castShadow=profile.shadows;head.lightDirect.shadow.mapSize.set(profile.shadowSize,profile.shadowSize);head.lightDirect.shadow.bias=-.0002;head.lightDirect.shadow.normalBias=.008;
    Object.assign(head.lightDirect.shadow.camera,{left:-2,right:2,top:2,bottom:-2,near:.05,far:10});
    $('avatar').dataset.presenceSession=crypto.randomUUID();
    stageActivity=new StageActivity(head,profile,{onChange:state=>{$('avatar').dataset.renderFps=String(state.fps);$('avatar').dataset.rendering=String(state.running);}});
    stageActivity.update({documentVisible:!document.hidden,parentVisible:parentStageVisible});
    // Orbiting is active work too. Keep full motion cadence through damping.
    let orbitSettled=null;
    head.controls.addEventListener('start',()=>{clearTimeout(orbitSettled);stageActivity.update({interacting:true});});
    head.controls.addEventListener('end',()=>{clearTimeout(orbitSettled);orbitSettled=setTimeout(()=>stageActivity.update({interacting:false}),800);});
    if('IntersectionObserver' in window)new IntersectionObserver(entries=>{const entry=entries[0];if(entry)stageActivity.update({inView:entry.isIntersecting&&entry.intersectionRatio>.01});},{threshold:[0,.01]}).observe($('stage'));
    window.__moneypennyRenderStats=()=>({...stageActivity.status(),frames:renderFrames,audioState:head.audioCtx.state,canvasWidth:head.renderer.domElement.width,canvasHeight:head.renderer.domElement.height,calls:head.renderer.info.render.calls,triangles:head.renderer.info.render.triangles});
    let saved=null; try {saved=await asset('avatar');}catch{}
    if(saved) { try{await showAvatar(saved);}catch{notify('The saved character is incompatible. The studio character has been restored.'); await showAvatar();} }
    else if(statusData.character_candidate_ready) {
      try{await showAvatar(null,{url:'/api/character/default',label:statusData.character_revision==='style-v29'?'Moneypenny · fitted crepe blouse':statusData.character_revision==='style-v28'?'Moneypenny · crepe blouse':statusData.character_revision==='style-v27'?'Moneypenny · tailored fit v27':statusData.character_revision==='style-v26'?'Moneypenny · balanced character v26':statusData.character_revision==='free-surface-reviewed'?'Moneypenny · free character study':statusData.character_revision==='surface-v9'?'Moneypenny · surface study v9':'Moneypenny · local performance candidate'});}
      catch{notify('The local performance character could not load. The studio sample has been restored.');await showAvatar();}
    } else await showAvatar();
    if(!jarvisEmbed){const floor=new THREE.Mesh(new THREE.PlaneGeometry(6,6),new THREE.ShadowMaterial({opacity:.22}));floor.rotation.x=-Math.PI/2;floor.position.y=-.003;floor.receiveShadow=true;head.scene.add(floor);}
    await head.audioCtx.audioWorklet.addModule(studioURL('/static/vendor/headaudio/headworklet.min.mjs'));
    lips=new HeadAudio(head.audioCtx,{parameterData:{vadGateActiveDb:-40,vadGateInactiveDb:-55,speakerMeanHz:220}});
    await lips.loadModel(studioURL('/static/vendor/headaudio/model-en-mixed.bin'));
    head.audioSpeechGainNode.connect(lips);
    const delay=head.audioCtx.createDelay(1);speechDelay=delay;delay.delayTime.value=Number($('mouthTiming').value)/1000;
    speechGate=head.audioCtx.createGain();
    head.audioSpeechGainNode.disconnect(head.audioReverbNode); head.audioSpeechGainNode.connect(delay); delay.connect(speechGate);speechGate.connect(head.audioReverbNode);
    analyser=head.audioCtx.createAnalyser(); analyser.fftSize=256; head.audioSpeechGainNode.connect(analyser);
    lips.onvalue=(key,value)=>{const target=head.mtAvatar[key];if(target)Object.assign(target,{newvalue:value,needsUpdate:true});};
    head.opt.update=dt=>{
      renderFrames++;
      if(renderFrames%30===0)$('avatar').dataset.renderFrames=String(renderFrames);
      stageActivity.update({active:busy||userSpeaking||head.isSpeaking||!!motion?.active||!!motion?.queue.length||!!motionLibrary?.playing||!!rig?.targets.size});
      lips.update(dt);if(!rig)return;
      const seconds=dt/1000;
      if((busy||userSpeaking)&&motionLibrary?.currentSource==='persona')motionLibrary.stop();
      rig.resetBody(!!motion?.active||!!motion?.queue.length||motionLibrary?.playing||rig.targets.size>0);
      rig.breathe(seconds,!!motion?.active||!!motionLibrary?.playing);
      if(motionLibrary?.playing)motionLibrary.update(seconds);
      else if(motion){motion.engaged=busy||userSpeaking;motion.update(dt);}
      rig.update(seconds);
      const stage=$('avatar'),skill=motion?.active?.skill||'idle',facing=String(Math.round((motion?.currentHeading||0)*180/Math.PI));
      if(stage.dataset.motion!==skill)stage.dataset.motion=skill;
      if(stage.dataset.facing!==facing)stage.dataset.facing=facing;
      poseCorrectives?.update(seconds);seatSupport?.update(motionLibrary?.playing?null:motion);if(rigView?.visible)rigView.update();
    };
    liveSession=new LiveSession({audioContext:head.audioCtx,onState:value=>$('liveState').textContent=value,
      onStart:()=>{
        userSpeaking=true;listenEpoch++;liveTranscription?.abort();motion?.stop();
        interruption=stopAll(false);setState('Listening to you','busy');$('liveState').textContent='Listening to you';
      },onEnd:audio=>handleLiveTurn(audio),onLevel:probability=>$('micLevel').value=probability,
      onError:error=>{notify(error.name==='NotAllowedError'?'Microphone permission is needed for live conversation.':error.message);updateLiveControls();},
    });
    lipReady=true; setBusy(busy);postPresence('moneypenny-presence-ready');
    stageActivity.update({documentVisible:!document.hidden,parentVisible:parentStageVisible});
    document.addEventListener('visibilitychange',()=>stageActivity.update({documentVisible:!document.hidden}));
    window.addEventListener('pagehide',()=>stageActivity.update({documentVisible:false}));
    window.addEventListener('pageshow',()=>stageActivity.update({documentVisible:!document.hidden}));
  } catch(e) { notify(`3D stage: ${e.message||e}`); setState('Stage unavailable','');postPresence('moneypenny-presence-error',{message:'The live character or voice could not start. Open Moneypenny Studio to retry.'}); }
}

async function stopAll(clearNotice=true,cancelLocalVoice=true) {
  const cancelled=generation;
  generation++; controller?.abort(); controller=null;motionLibrary?.stop();
  const stopGeneration=generation;
  if(speechGate)speechGate.gain.setValueAtTime(0,head.audioCtx.currentTime);
  if(activeReply){activeReply.body.textContent=activeReply.body.textContent==='…'?'Reply stopped.':`${activeReply.body.textContent}\n\n[Stopped]`;activeReply=null;}
  recorder.cancel(); recordingPending=false; $('record').classList.remove('recording'); $('recordLabel').textContent='Record note';
  if(currentSource) {currentSource.onended=null;try{currentSource.stop();}catch{} currentSource.disconnect();currentSource=null;}
  speechEnded?.(); speechEnded=null;
  head?.stopSpeaking();if(head)head.isSpeaking=false;head?.stopGesture(150); lips?.resetAll();
  if(visualizer)cancelAnimationFrame(visualizer);
  actionTimers.forEach(clearTimeout);actionTimers=[];
  for(const key of ['headRotateX','headRotateZ','bodyRotateX','eyeBlinkLeft'])head?.setValue(key,0,150);
  if(cancelLocalVoice&&!proxiedPresence)try {await api('/api/speech/stop',{owner:`${owner}:${cancelled}`});} catch {}
  if(generation===stopGeneration){if(clearNotice)notify();setBusy(false);setState(userSpeaking?'Listening to you':avatarReady?'Here with you':'Character unavailable',avatarReady?'ready':'');}
}

function performActions(performance={}) {
  if(!avatarReady)return;
  head.setMood(performance.mood||$('mood').value||'neutral');
  const directed=motionLibrary?.playing&&motionLibrary.currentSource!=='persona'||[motion?.active,...(motion?.queue||[])].some(step=>step&&!['persona','conversation'].includes(step.source));
  if(directed)return;
  const movement=Number($('movement').value);
  if(movement<.05)return;
  if(performance.gesture&&movement>.2)head.playGesture(performance.gesture,3);
  else if(movement>.45)head.speakWithHands(0,.35);
  const actions=(performance.actions||'').toLowerCase();
  const plan=movementFromText(actions);if(plan)motion?.plan(plan,'conversation');
  function move(key,value,duration){head.setValue(key,value,200);actionTimers.push(setTimeout(()=>head.setValue(key,0,300),duration));}
  if(/\bnod/.test(actions))move('headRotateX',.15*movement,500);
  if(/tilt/.test(actions))move('headRotateZ',-.13*movement,2200);
  if(/lean|closer/.test(actions))move('bodyRotateX',.13*movement,3200);
  if(/wink/.test(actions))move('eyeBlinkLeft',1,350);
}
async function prepareSpeech(value, token) {
  if(!statusData.voice_ready)throw new Error('The local British voice needs setup. Text chat is available.');
  if(!avatarReady||!lipReady)throw new Error('The 3D character and mouth animation must finish loading before speaking.');
  if(value.length>2400)throw new Error('This reply is too long for one voice performance. Choose a shorter reply length or replay a shorter message.');
  await head.audioCtx.resume();
  if(!currentSource)setState('Preparing her voice','busy');
  const response=await api('/api/speech',{text:value,speed:Number($('speed').value),owner:`${owner}:${token}`},controller?.signal);
  const audio=await head.audioCtx.decodeAudioData(await response.arrayBuffer());
  if(token!==generation)throw new DOMException('Stopped','AbortError');
  return audio;
}
async function playPrepared(audio, token, performance={}) {
  if(token!==generation)return;
  if(speechGate)speechGate.gain.setValueAtTime(1,head.audioCtx.currentTime);
  setState('Speaking','speaking');
  if(turnStarted&&!firstVoiceAt){firstVoiceAt=(performanceNow()-turnStarted)/1000;$('chatMetrics').dataset.firstVoiceSeconds=firstVoiceAt.toFixed(2);$('chatMetrics').textContent=`Voice in ${firstVoiceAt.toFixed(1)}s`;}
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
    if(!jarvisEmbed&&!document.hidden)draw();
    source.onended=()=>{
      source.disconnect(); if(currentSource===source)currentSource=null;
      head.isSpeaking=false; speechEnded=null; cancelAnimationFrame(visualizer);
      // Let the delayed audio and mouth closure drain before reporting idle.
      resolve();
    };
    source.start();performance.onStarted?.();
  });
  if(token===generation) {setState(liveSession?.active?'Listening':'Here with you');head.setMood($('mood').value||'neutral');}
}
async function playSpeech(value, token, performance={}) {
  await playPrepared(await prepareSpeech(value,token),token,performance);
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
async function sendMessage(event,spokenOverride=null) {
  event?.preventDefault(); const prompt=(spokenOverride||$('userInput').value).trim();
  if(!prompt||busy||recorder.active||recordingPending)return;
  setBusy(true); await stopAll(); const token=generation;controller=new AbortController(); setBusy(true);notify();setState('Thinking with you','busy');
  try{if(await handleControl(prompt)){setBusy(false);return;}}catch(error){notify(error.message);setBusy(false);return;}
  const requestedMotion=movementFromText(prompt);
  const libraryMatch=(!requestedMotion||requestedMotion.steps.length===1)&&motionLibrary?.match(prompt);
  const clothes=wardrobeCommand(prompt);let localAck='',actionStatus='',queuedSkills=[];
  try{
    if((requestedMotion||libraryMatch||clothes)&&!avatarReady)throw new Error('The character is still loading. Try the action again once she appears.');
    if(libraryMatch){motion?.stop();rig?.clear();await motionLibrary.play(libraryMatch.id);frameCharacter('full');localAck=`I’ll perform ${libraryMatch.name} now.`;actionStatus='Saved movement started';queuedSkills=['custom'];}
    else if(requestedMotion){rig?.clear();if(!motion?.plan(requestedMotion,'instruction'))throw new Error('The movement could not be queued.');frameCharacter('full',requestedMotion);localAck=movementAcknowledgement(requestedMotion);actionStatus='Movement queued';queuedSkills=requestedMotion.steps.map(step=>step.skill);}
    if(clothes){
      if(!wardrobe?.reference)throw new Error('These outfit presets belong to the studio sample. Use this character’s fitted garment controls instead.');
      if(clothes.outfit)$('wardrobe').value=clothes.outfit;if(clothes.footwear)$('footwear').value=clothes.footwear;updateSettings();
      const outfitName=$('wardrobe').selectedOptions[0].textContent,shoeName=$('footwear').selectedOptions[0].textContent;
      localAck+=(localAck?' ':'')+(clothes.outfit==='base'?'The added outer layers are hidden. This sample’s fixed base clothes stay on.':`Outfit selection updated: ${[clothes.outfit?outfitName:null,clothes.footwear?shoeName:null].filter(Boolean).join(', ')}.`);actionStatus+=(actionStatus?' · ':'')+'Wardrobe updated';
    }
  }catch(error){addMessage('user',prompt);addMessage('assistant',error.message);$('userInput').value='';notify(error.message);setBusy(false);scrollChat();return;}
  if(token!==generation)return;
  if(localAck&&actionOnly(prompt)){
    addMessage('user',prompt);const entry=addMessage('assistant',localAck);entry.article.dataset.controller='local-action';entry.action.textContent=actionStatus;entry.action.hidden=false;
    history.push({role:'user',content:prompt},{role:'assistant',content:localAck});history=history.slice(-20);$('userInput').value='';$('chatMetrics').textContent='Local action · no model wait';scrollChat();
    try{if($('autoSpeak').checked&&voiceAllowed())await playSpeech(localAck,token);}catch(error){if(token===generation)notify(error.message);}finally{if(token===generation){setBusy(false);controller=null;setState('Here with you');}}
    return;
  }
  const messages=history.slice(-20); addMessage('user',prompt);const reply=addMessage('assistant','…');$('userInput').value='';scrollChat();
  turnStarted=performanceNow();firstVoiceAt=0;delete $('chatMetrics').dataset.firstVoiceSeconds;delete $('chatMetrics').dataset.replyDoneSeconds;
  activeReply=reply;
  let raw='',finished=false;
  let firstPerformance=true;
  const speaking=$('autoSpeak').checked&&voiceAllowed();
  const pipeline=new SpeechPipeline(part=>prepareSpeech(part,token),audio=>{
    const performance=firstPerformance?{mood:'happy',actions:raw.match(/\*([^*]+)\*/)?.[1]||''}:{};firstPerformance=false;
    return playPrepared(audio,token,performance);
  });
  const segmenter=new SpeechSegmenter(part=>pipeline.push(part));
  try {
    // Resume directly after the click; subsequent synthesis may take a moment.
    head?.audioCtx.resume();
    const response=await api('/api/chat/stream',{prompt,history:messages,persona_id:tools?.personaId,avatar_motion:queuedSkills,model:$('modelSelect').value,system:`Character name: ${$('personaName').value||'Moneypenny'}.\n${$('systemPrompt').value}`,temperature:Number($('temperature').value),max_tokens:Number($('maxTokens').value)},controller.signal);
    const reader=response.body.getReader(),decoder=new TextDecoder();let pending='';
    let result;
    while(true){
      const {value,done}=await reader.read();if(done)break;
      if(token!==generation){await reader.cancel();return;}
      pending+=decoder.decode(value,{stream:true});const lines=pending.split('\n');pending=lines.pop();
      for(const line of lines){
        if(!line.trim())continue;const data=JSON.parse(line);
        if(data.type==='error')throw new Error(data.error);
        if(data.type==='delta'){raw+=data.text;reply.body.textContent=raw;if(speaking)segmenter.update(raw);scrollChat();}
        if(data.type==='done'){result=data;finished=true;}
      }
    }
    if(!finished)throw new Error('The reply was interrupted before it finished. Please retry.');
    if(token!==generation)return;
    activeReply=null;
    reply.body.textContent=result.dialogue;reply.action.textContent=result.actions;reply.action.hidden=!result.actions;
    history.push({role:'user',content:prompt},{role:'assistant',content:result.dialogue});history=history.slice(-20);
    $('chatMetrics').dataset.replyDoneSeconds=result.elapsed.toFixed(2);if(!firstVoiceAt)$('chatMetrics').textContent=`Reply in ${result.elapsed.toFixed(1)}s`;
    addReplay(reply,result.dialogue);scrollChat();
    if(speaking){segmenter.update(raw,true);await pipeline.done();}
    else {performActions(result);setState('Here with you');}
  }catch(e){
    if(token!==generation||e.name==='AbortError')return;
    await stopAll(false);
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
    finally{if(token===generation){recordingPending=false;$('recordLabel').textContent='Record note';setBusy(false);}}
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

function voiceAllowed(){return quietUntil!==-1&&Date.now()>=quietUntil;}
function performanceNow(){return window.performance.now();}
function updateLiveControls(){
  const active=!!liveSession?.active;
  $('liveToggle').textContent=active?'■ Stop live conversation':'◉ Start live conversation';
  $('liveToggle').classList.toggle('active',active);
  if(!active){$('liveState').textContent='Microphone off';$('micLevel').value=0;}
  $('resumeButton').hidden=voiceAllowed();
  setBusy(busy);
}
function setQuiet(until){quietUntil=until;localStorage.setItem('moneypenny-quiet-until',String(until));updateLiveControls();}
async function handleControl(prompt){
  const intent=controlIntent(prompt);if(!intent)return false;
  addMessage('user',prompt);
  if(intent.type==='quiet'){
    setQuiet(intent.delay?Date.now()+intent.delay*1000:-1);
    addMessage('assistant',intent.delay?`I'll stay quiet for ${Math.round(intent.delay/60*10)/10} minutes. You can speak to me again whenever you like.`:'I’ll stay quiet. Say “resume” or ask another question when you want to talk.');
    setState('Quiet · still listening');
  }else if(intent.type==='resume'){setQuiet(0);addMessage('assistant','I’m here. What would you like to talk about?');setState('Listening');}
  else{
    await api('/api/reminders',{text:prompt,delay:intent.delay});setQuiet(Date.now()+intent.delay*1000);
    addMessage('assistant',`I’ll check back at ${new Date(Date.now()+intent.delay*1000).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}. Keep the studio open for the follow-up.`);
    $('followupState').textContent='Follow-up saved';setState('Quiet until your follow-up');
  }
  $('userInput').value='';scrollChat();return true;
}
async function handleLiveTurn(audio){
  const epoch=listenEpoch;userSpeaking=false;
  $('liveState').textContent='Transcribing locally…';setState('Listening back','busy');
  liveTranscription=new AbortController();
  try{
    const response=await fetch('/api/transcribe',{method:'POST',headers:{'Content-Type':'audio/wav','X-Studio-Client':'moneypenny'},body:audio,signal:liveTranscription.signal});
    const data=await response.json();if(!response.ok)throw new Error(data.error);
    if(epoch!==listenEpoch||!liveSession.active)return;
    const words=(data.text||'').trim();if(!words){$('liveState').textContent='Listening';return;}
    await interruption;if(epoch!==listenEpoch||!liveSession.active)return;
    $('liveState').textContent='Listening · speak to interrupt';
    if(!controlIntent(words))setQuiet(0);
    await sendMessage(null,words);
  }catch(error){if(epoch===listenEpoch&&error.name!=='AbortError'){notify(error.message);$('liveState').textContent='Listening · previous transcription failed';}}
}
async function pollReminders(){
  if(jarvisEmbed||reminderPolling||document.hidden)return;reminderPolling=true;
  try{
    const response=await fetch('/api/reminders');if(!response.ok)return;
    const data=await response.json();const list=data.reminders||[];
    $('followupState').textContent=list.length?`${list.length} follow-up${list.length===1?'':'s'} saved`:'';
    const due=list.find(item=>item.due<=data.now);
    if(!due||busy||userSpeaking)return;
    const claimed=await (await api(`/api/reminders/${due.id}/claim`,{})).json();if(!claimed.claimed)return;
    setQuiet(0);const message='You asked me to check back with you. How are you getting on?';
    const entry=addMessage('assistant',message);entry.action.textContent=`Your follow-up: ${due.text}`;entry.action.hidden=false;scrollChat();
    if($('autoSpeak').checked&&avatarReady&&lipReady){await stopAll(false);const token=generation;controller=new AbortController();setBusy(true);try{await playSpeech(message,token);}finally{if(token===generation)setBusy(false);}}
  }catch{}finally{reminderPolling=false;}
}

$('liveToggle').onclick=async()=>{
  if(!liveSession){notify('Wait for the character and voice system to finish loading.');return;}
  if(liveSession.active){listenEpoch++;liveTranscription?.abort();await liveSession.stop();await stopAll();userSpeaking=false;updateLiveControls();return;}
  $('autoSpeak').checked=true;setQuiet(0);
  api('/api/listening/warm',{}).catch(()=>{});
  const started=liveSession.start();updateLiveControls();await started;updateLiveControls();
};
$('quietButton').onclick=async()=>{await stopAll();setQuiet(-1);setState('Quiet · microphone unchanged');};
$('resumeButton').onclick=()=>{setQuiet(0);setState(liveSession?.active?'Listening':'Here with you');};
$('planMotion').onclick=async()=>{
  const prompt=$('motionPrompt').value.trim();if(!prompt||!motion)return;
  if(/\b(?:don't|do not|avoid|without|stop)\b/i.test(prompt)){motionLibrary?.stop();motion.stop();$('motionState').textContent='Movement request cancelled';return;}
  $('planMotion').disabled=true;
  try{const matched=motionLibrary?.match(prompt);if(matched){motion.stop();await motionLibrary.play(matched.id);frameCharacter('full');return;}motionLibrary?.stop();rig?.clear();const local=movementFromText(prompt);if(!local&&!$('aiMotion').checked){notify('No matching movement is saved yet. Add a compatible animation and give it these movement words.');return;}const plan=local||await(await api('/api/motion/plan',{prompt,persona:$('behaviourPrompt').value,model:$('modelSelect').value})).json();motion.plan(plan,'choreography');frameCharacter('full',plan);}
  catch(error){notify(error.message);}finally{$('planMotion').disabled=false;}
};
$('stopMotion').onclick=()=>{motionLibrary?.stop();motion?.stop();$('autonomy').checked=false;updateSettings();$('motionState').textContent='Independent movement paused';};
$('previewSeatPose').onclick=async()=>{await stopAll();motionLibrary?.stop();rig?.clear();motion?.plan({steps:[{skill:'supported_step',side:$('seatPoseSide').value,duration:8,intensity:1}]});frameCharacter('full');};
if(!jarvisEmbed)setInterval(pollReminders,2500);

$('chatForm').addEventListener('submit',sendMessage);
$('userInput').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();sendMessage();}});
$('stop').onclick=async()=>{listenEpoch++;liveTranscription?.abort();userSpeaking=false;await stopAll();await liveSession?.stop();updateLiveControls();};$('record').onclick=toggleRecord;
$('newChat').onclick=async()=>{await stopAll();history=[];$('messages').replaceChildren();$('welcome').hidden=false;$('chatMetrics').textContent='Local conversation';};
document.querySelectorAll('[data-prompt]').forEach(button=>button.onclick=()=>{$('userInput').value=button.dataset.prompt;sendMessage();});
document.querySelectorAll('[data-view]').forEach(button=>button.onclick=()=>{if(!avatarReady)return;frameCharacter(button.dataset.view);});
$('wave').onclick=async()=>{if(avatarReady){motion?.stop();motionLibrary?.stop();head.setMood('happy');if(head.studioNeutral)motion.plan({steps:[{skill:'wave',duration:4,intensity:.7}]});else try{await motionLibrary.play('studio-wave');}catch(error){notify(error.message);}}};
$('previewMood').onclick=()=>{if(avatarReady)head.setMood($('mood').value);};
$('fullscreen').onclick=()=>{if(document.fullscreenElement)document.exitFullscreen();else $('stage').requestFullscreen?.().catch(e=>notify(e.message));};
$('previewVoice').onclick=async()=>{
  await stopAll();const token=generation;controller=new AbortController();setBusy(true);
  try{head.setMood('happy');motion?.stop();if(head.studioNeutral)motion.plan({steps:[{skill:'wave',duration:4,intensity:.7}]});else try{await motionLibrary?.play('studio-wave');}catch{}await playSpeech(`Hello, I'm ${$('personaName').value||'Moneypenny'}. A familiar voice, a little personality, and a moment to think together. What shall we start with?`,token);}
  catch(e){if(token===generation)notify(e.message);}finally{if(token===generation)setBusy(false);}
};
for(const id of settingIds)$(id).addEventListener('input',()=>{if(id==='systemPrompt')$('personaPreset').value='custom';if(['systemPrompt','personaName','modelSelect','personaPreset'].includes(id))tools?.markDirty();updateSettings();if(appearanceIds.includes(id))saveAppearance();});
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
window.addEventListener('pagehide',()=>{presenceAudio?.cancel();recorder.cancel();liveSession?.stop();head?.stopSpeaking();try{currentSource?.stop();}catch{};if(!proxiedPresence)fetch('/api/speech/stop',{method:'POST',headers:{'Content-Type':'application/json','X-Studio-Client':'moneypenny'},body:JSON.stringify({owner:`${owner}:${generation}`}),keepalive:true}).catch(()=>{});});

if(jarvisEmbed){
  presenceAudio=new PresenceAudio({
    stopAudio:()=>stopAll(false,false),setBusy,emit:postPresence,
    decode:async bytes=>{
      if(!avatarReady||!lipReady)throw new Error('Moneypenny is still preparing her character and voice.');
      await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error('Tap Moneypenny once to enable her voice on this device.')),2500);head.audioCtx.resume().then(()=>{clearTimeout(timer);resolve();},error=>{clearTimeout(timer);reject(error);});});
      if(head.audioCtx.state!=='running')throw new Error('Tap Moneypenny once to enable her voice on this device.');
      return head.audioCtx.decodeAudioData(bytes);
    },
    playAudio:(audio,{onStarted})=>playPrepared(audio,generation,{onStarted,mood:$('mood').value||'neutral'}),
    drain:()=>new Promise(resolve=>setTimeout(resolve,Math.round((speechDelay?.delayTime.value||0)*1000)+30)),
  });
  let pointerStart=null;
  $('avatar').addEventListener('pointerdown',event=>{pointerStart={x:event.clientX,y:event.clientY,id:event.pointerId};});
  $('avatar').addEventListener('pointerup',event=>{const start=pointerStart;pointerStart=null;if(start&&start.id===event.pointerId&&Math.hypot(event.clientX-start.x,event.clientY-start.y)<=8){head?.audioCtx.resume().catch(()=>{});postPresence('moneypenny-presence-activate');}});
  $('avatar').addEventListener('pointercancel',()=>{pointerStart=null;});
  window.addEventListener('message',async event=>{
    if(!jarvisOrigins.includes(event.origin)||event.source!==parent)return;
    jarvisParentOrigin=event.origin;
    const message=event.data||{};
    if(message.type==='jjrvis-presence-visibility'&&typeof message.visible==='boolean'){parentStageVisible=message.visible;stageActivity?.update({parentVisible:message.visible});return;}
    if(message.type==='jjrvis-presence-status'){if(avatarReady&&lipReady)postPresence('moneypenny-presence-ready');return;}
    if(message.type==='jjrvis-stop'){const brokerAudio=presenceAudio.id!==null;presenceAudio.cancel();await stopAll(false,!brokerAudio);return;}
    if(message.type==='jjrvis-audio'){await presenceAudio.play(message);return;}
    if(message.type==='jjrvis-audio-end'){await presenceAudio.end(message);return;}
    if(message.type==='jjrvis-wave'&&avatarReady){motion?.stop();motionLibrary?.stop();head.setMood('happy');motion?.plan({steps:[{skill:'wave',duration:4,intensity:.65}]});return;}
    if(message.type!=='jjrvis-speak'||typeof message.text!=='string'||!message.text.trim())return;
    if(proxiedPresence){postPresence('moneypenny-presence-error',{requestId:message.requestId,message:'Voice is supplied by the connected workspace.'});return;}
    presenceAudio.cancel();
    if(!avatarReady||!lipReady){postPresence('moneypenny-presence-error',{requestId:message.requestId,message:'Moneypenny is still preparing her character and voice.'});return;}
    if(message.text.length>24000){postPresence('moneypenny-presence-error',{requestId:message.requestId,message:'This reply exceeds the supported voice length.'});return;}
    await stopAll(false);const token=generation;controller=new AbortController();setBusy(true);
    try{
      let started=false;
      const pipeline=new SpeechPipeline(part=>prepareSpeech(part,token),audio=>playPrepared(audio,token,{mood:message.mood||'neutral',actions:message.actions||'look attentive and speak naturally',onStarted:()=>{if(!started){started=true;postPresence('moneypenny-presence-speaking',{requestId:message.requestId});}}}));
      const segmenter=new SpeechSegmenter(part=>pipeline.push(part));segmenter.update(message.text.trim(),true);await pipeline.done();
    }
    catch(error){if(token===generation){notify(error.message);postPresence('moneypenny-presence-error',{requestId:message.requestId,message:'Speech playback unavailable.'});}}
    finally{if(token===generation)setBusy(false);postPresence('moneypenny-presence-idle',{requestId:message.requestId});}
  });
}

async function initialize() {
  $('systemPrompt').value=presets.moneypenny;
  let saved;try{saved=JSON.parse(localStorage.getItem('moneypenny-persona-v2'));}catch{}
  if(saved)applySettings(saved);else updateSettings();
  setBusy(false);
  try{
    const response=await fetch('/api/status'+(jarvisEmbed?'?quick=1':''));if(!response.ok)throw new Error('Local status check failed.');statusData=await response.json();
    $('modelSelect').replaceChildren();
    for(const model of statusData.models){const option=document.createElement('option');option.value=model;option.textContent=model;$('modelSelect').append(option);}
    $('modelSelect').value=chooseModel(statusData.models,saved?.modelSelect);
    if(!statusData.models.length){const option=document.createElement('option');option.textContent='Ollama unavailable';$('modelSelect').append(option);}
    $('connectionNote').textContent=statusData.voice_ready&&statusData.models.length?'Local model & British voice connected':statusData.ollama_error||'Local voice needs setup · see README';
    if(statusData.ollama_error)notify(statusData.ollama_error);
    if(!statusData.microphone_ready)$('record').title='Local Vosk transcription needs setup; see README.';
    setBusy(false);saveSettings();
  }catch(e){notify(e.message);$('connectionNote').textContent='Local services unavailable';}
  await initializeStage();
  if(jarvisEmbed){try{await motionLibrary?.refresh();}catch{}return;}
  tools=new StudioTools({getRig:()=>rig,getRigView:()=>rigView,getLibrary:()=>motionLibrary,getMotion:()=>motion,getWardrobe:()=>wardrobe,settings,applySettings,post:api,notify,frame:frameCharacter,stopConversation:stopAll,
    resetConversation:async()=>{await stopAll();history=[];$('messages').replaceChildren();$('welcome').hidden=false;},
    download:(filename,value)=>{const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}});
  try{await tools.start();}catch(error){notify(error.message);}
  updateLiveControls();pollReminders();
}
initialize();

if(jarvisEmbed){document.addEventListener('visibilitychange',()=>{if(!document.hidden)syncAppearance();});setInterval(()=>{if(!document.hidden)syncAppearance();},15000);}
