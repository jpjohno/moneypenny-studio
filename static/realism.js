import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {FourDPlayer,createGLTFFrameLoader,disposeThreeFrame} from './fourd-player.js';
import {authoredNeutral,RigController} from './rig.js';
const $=id=>document.getElementById(id),stage=$('canvas');
const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'low-power'});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.25));renderer.setClearColor(0,0);
renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=.9;stage.append(renderer.domElement);
const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(35,1,.03,100),controls=new OrbitControls(camera,renderer.domElement);
controls.enableDamping=true;controls.dampingFactor=.1;controls.minDistance=.4;controls.maxDistance=7;controls.target.set(0,1,0);camera.position.set(0,1,3.5);
scene.add(new THREE.HemisphereLight('#f0f6ff','#45585d',1.6));
for(const [color,power,position]of [['#fff7ef',2,[1,2.6,3]],['#d8efff',.9,[-2,1.8,1.5]]]){const light=new THREE.DirectionalLight(color,power);light.position.set(...position);scene.add(light);}
let player=null,scan=null,root=null,rig=null,mode=null,epoch=0,loadController=null,disposed=false,raf=0,sequenceBounds=null,bounds=new THREE.Box3(),waveUntil=0,mouthUntil=0,blinkUntil=0;
function show(asset){if(root)scene.remove(root);root=asset?.scene??null;if(root)scene.add(root);}
function frameView(portrait=false){
 if(!root)return;
 const box=!portrait&&mode==='4d'&&sequenceBounds?sequenceBounds:new THREE.Box3().setFromObject(root),size=box.getSize(new THREE.Vector3()),centre=box.getCenter(new THREE.Vector3());bounds.copy(box);
 if(portrait){controls.target.set(centre.x,box.max.y-size.y*.12,centre.z);camera.position.set(centre.x,controls.target.y,centre.z+size.y*.62);}
 else{controls.target.copy(centre);camera.position.set(centre.x,centre.y,centre.z+Math.max(size.y*1.75,size.x*1.6));}
 controls.update();
}
function message(text){$('status').textContent=text;}
function clear(){loadController?.abort();loadController=null;player?.dispose();player=null;if(scan)disposeThreeFrame(scan);scan=null;rig=null;sequenceBounds=null;show(null);waveUntil=mouthUntil=blinkUntil=0;}
async function load(next){
 if(disposed)return;
 const own=++epoch;clear();mode=next;
 const controller=new AbortController();loadController=controller;
 const isCurrent=()=>own===epoch&&!disposed;
 $('scanMode').setAttribute('aria-pressed',String(next==='scan'));$('fourDMode').setAttribute('aria-pressed',String(next==='4d'));
 $('scanControls').hidden=next!=='scan';$('fourDControls').hidden=next!=='4d';message('Preparing the captured detail…');
 try{
  if(next==='scan'){
   $('kind').textContent='SCANNED CHARACTER / MOVEMENT STUDY';$('title').textContent='Captured detail. A familiar presence.';
   $('explanation').textContent='A real scanned character with a body rig and experimental mouth and blink controls. Pronunciation, tooth visibility and live voice still need calibration. This preview does not replace your working assistant.';
   const gltf=await createGLTFFrameLoader(new GLTFLoader(),{baseURL:location.href})({url:'/api/review-assets/scan.glb'},{signal:controller.signal});
   if(!isCurrent()){disposeThreeFrame(gltf);return;}
   scan=gltf;show(gltf);const neutral=authoredNeutral(gltf.scene);rig=new RigController({armature:gltf.scene,studioNeutral:neutral});frameView(true);
   message('Drag to turn. Try the wave, mouth and blink studies.');
  }else{
   $('kind').textContent='RECORDED 4D / CAPTURED HUMAN MOVEMENT';$('title').textContent='Movement, captured in four dimensions.';
   $('explanation').textContent='This is a recorded volumetric performance. You can turn the camera and explore the motion; it does not generate new actions or spoken replies. Only a few frames are kept in memory.';
   const url=new URL(`/api/review-assets/4d/${$('quality').value==='light'?'':'detail/'}manifest.json`,location.href),response=await fetch(url,{signal:controller.signal});
   if(!response.ok)throw new Error('The recorded preview is still being prepared. Use Reload preview in a moment.');
   const manifest=await response.json();
   if(!Array.isArray(manifest.frames)||!manifest.frames.every(frame=>/^frames\/frame\d{4}\.glb$/.test(typeof frame==='string'?frame:frame?.url)))throw new Error('The recorded preview has an unsupported frame path.');
   if(!isCurrent())return;
   const extent=manifest.bounds;
   if([extent?.min,extent?.max].every(vector=>Array.isArray(vector)&&vector.length===3&&vector.every(Number.isFinite))&&extent.min.every((value,index)=>value<=extent.max[index]))sequenceBounds=new THREE.Box3(new THREE.Vector3(...extent.min),new THREE.Vector3(...extent.max));
   const complete=manifest.metadata?.fullSequence??manifest.fullSequence??false;
   let first=true,frameError=false,lastGoodFrame=null;
   player=new FourDPlayer(manifest,{loadFrame:createGLTFFrameLoader(new GLTFLoader(),{baseURL:url.href}),showFrame:asset=>{if(!isCurrent())return;show(asset);if(asset&&first){first=false;frameView(false);}},onState:state=>{
    if(!isCurrent())return;
    $('timeline').max=String(state.frames-1);$('timeline').value=String(state.frame??0);const sec=Math.floor((state.frame??0)/state.fps);$('elapsed').textContent=`${Math.floor(sec/60)}:${String(sec%60).padStart(2,'0')}`;
    $('play').disabled=state.playing;$('pause').disabled=!state.playing;
    if(state.frame!==null&&state.frame!==lastGoodFrame){lastGoodFrame=state.frame;frameError=false;}
    if(state.frame!==null&&!frameError)message(state.buffering?'Keeping the last frame while the next arrives…':complete?'Captured performance · turn the view while it plays.':'Short movement test · the full performance is being prepared.');
   },onError:()=>{if(isCurrent()){frameError=true;message('A recorded frame could not load. Use Reload preview to retry.');}},maxCached:3,prefetch:2});
   await player.seek(0);
  }
 }catch(error){if(isCurrent()){clear();message(error.message||'This preview could not load.');}}
 finally{if(loadController===controller)loadController=null;}
}
async function usePlayer(action){const current=player,own=epoch;if(!current||disposed)return;const isCurrent=()=>current===player&&own===epoch&&!disposed;try{await action(current,isCurrent);}catch(error){if(isCurrent())message(error.message||'The recorded preview could not continue.');}}
function morph(name,value){scan?.scene.traverse(node=>{const index=node.morphTargetDictionary?.[name];if(index!==undefined)node.morphTargetInfluences[index]=value;});}
$('quality').onchange=()=>{if(mode==='4d')return load('4d');};
$('scanMode').onclick=()=>load('scan');$('fourDMode').onclick=()=>load('4d');$('reload').onclick=()=>load(mode||'4d');
$('play').onclick=()=>usePlayer(current=>current.play());$('pause').onclick=()=>usePlayer(current=>current.pause());$('restart').onclick=()=>usePlayer(async(current,isCurrent)=>{if(await current.seek(0)&&isCurrent())await current.play();});
$('timeline').oninput=()=>usePlayer(current=>current.seek(Number($('timeline').value)));
$('full').onclick=()=>frameView(false);$('portrait').onclick=()=>frameView(true);$('reset').onclick=()=>frameView(mode==='scan');
$('wave').onclick=()=>{waveUntil=performance.now()/1000+4;};$('mouth').onclick=()=>{mouthUntil=performance.now()/1000+3;};$('blink').onclick=()=>{blinkUntil=performance.now()/1000+.65;};
const resize=()=>{const {width,height}=stage.getBoundingClientRect();if(width&&height){renderer.setSize(width,height,false);camera.aspect=width/height;camera.updateProjectionMatrix();}};
const observer=new ResizeObserver(resize);observer.observe(stage);resize();
let previous=performance.now(),lastRender=0;
function tick(now){if(disposed)return;raf=requestAnimationFrame(tick);const dt=Math.min(.1,Math.max(0,(now-previous)/1000));previous=now;if(document.hidden)return;
 if(rig){const seconds=now/1000;rig.resetBody(true);rig.breathe(dt,waveUntil>seconds);if(waveUntil>seconds){const elapsed=4-(waveUntil-seconds),weight=Math.min(1,elapsed/.5,(waveUntil-seconds)/.5);rig.poseSkill('wave',Math.max(0,weight),'right',elapsed);}rig.update(dt);
  morph('viseme_aa',mouthUntil>seconds?Math.max(0,Math.sin((mouthUntil-seconds)*7))*.65:0);
  const blink=blinkUntil>seconds?Math.sin((.65-(blinkUntil-seconds))/.65*Math.PI):0;morph('eyeBlinkLeft',Math.max(0,blink));morph('eyeBlinkRight',Math.max(0,blink));
 }
 player?.update(dt);controls.update();if(now-lastRender>=1000/30){renderer.render(scene,camera);lastRender=now;}
}
raf=requestAnimationFrame(tick);document.addEventListener('visibilitychange',()=>{if(document.hidden)player?.pause();});
window.addEventListener('pagehide',event=>{if(event.persisted){player?.pause();return;}disposed=true;epoch++;clear();cancelAnimationFrame(raf);observer.disconnect();controls.dispose();renderer.dispose();});
load(new URLSearchParams(location.search).get('view')==='scan'?'scan':'4d');
