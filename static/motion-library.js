import * as THREE from 'three';
import {studioFetch as fetch} from './studio-paths.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { BVHLoader } from 'three/addons/loaders/BVHLoader.js';
import { retargetClip } from 'three/addons/utils/SkeletonUtils.js';
import {validateAnimationSequence} from './animation-builder.js';
const canonical=name=>name.replace(/^mixamorig[:_]?/i,'').replace(/[^a-z0-9]/gi,'').toLowerCase();
const aliases={Hips:['hip','pelvis'],Spine:['abdomen','lowerback'],Spine1:['chest','upperback'],Spine2:['chest2','thorax'],Neck:['neck','lowerneck'],Head:['head']};
for(const [side,prefix] of [['Left','l'],['Right','r']])for(const [bone,other] of [['Shoulder','collar'],['Arm','shoulder'],['ForeArm','elbow'],['Hand','wrist'],['UpLeg','hip'],['Leg','knee'],['Foot','ankle']])aliases[side+bone]=[prefix+other];
const smooth=x=>x*x*x*(x*(x*6-15)+10);

export function authoredClip(data,rig){
  if(data.version!==1||!Array.isArray(data.frames)||data.frames.length<2||data.frames.length>12||!(data.duration>=1&&data.duration<=20))throw new Error('Invalid authored motion.');
  const names=new Set(data.frames.flatMap(frame=>Object.keys(frame.joints||{}))),tracks=[];
  for(const name of names){
    if(!rig.rest[name])continue;
    const times=[],values=[];
    for(let i=0;i<=Math.ceil(data.duration*30);i++){
      const t=Math.min(data.duration,i/30),p=t/data.duration;
      const right=data.frames.findIndex(f=>f.at>=p),end=data.frames[right<0?data.frames.length-1:right],start=data.frames[Math.max(0,right-1)]||end;
      const a=start.joints[name]||[0,0,0],b=end.joints[name]||[0,0,0],u=smooth(Math.max(0,Math.min(1,(p-start.at)/Math.max(.001,end.at-start.at))));
      if([...a,...b].some(v=>!Number.isFinite(v)||Math.abs(v)>2.8))throw new Error('Invalid joint rotation.');
      const q=rig.rest[name].q.clone().multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(...a.map((v,j)=>v+(b[j]-v)*u))));
      times.push(t);values.push(...q.toArray());
    }
    tracks.push(new THREE.QuaternionKeyframeTrack(name+'.quaternion',times,values));
  }
  if(!tracks.length)throw new Error('This movement has no matching bones.');
  return new THREE.AnimationClip(data.name,data.duration,tracks);
}

export function retarget(source,clip,rig,mapping={}){
  if(!Number.isFinite(clip.duration)||clip.duration<=0||clip.duration>120||clip.tracks.length>400)throw new Error('Use a movement clip between 0 and 120 seconds with fewer than 400 tracks.');
  const sourceNames=new Map(source.bones.map(b=>[canonical(b.name),b.name])),names={};
  for(const name of Object.keys(rig.bones)){
    const candidates=[mapping[name],name,...(aliases[name]||[])].filter(Boolean);
    const match=candidates.map(x=>sourceNames.get(canonical(x))).find(Boolean);if(match)names[name]=match;
  }
  if(!names.Hips||!names.LeftUpLeg||!names.RightUpLeg||!names.Spine)throw new Error('Map at least the hips, spine and both upper legs before retargeting this skeleton.');
  const root=rig.head.armature.clone(true),bones=[];root.traverse(b=>{if(b.isBone){b.position.copy(rig.rest[b.name].p);b.quaternion.copy(rig.rest[b.name].q);bones.push(b);}});
  const target=new THREE.SkinnedMesh(new THREE.BufferGeometry(),new THREE.MeshBasicMaterial());target.add(root);target.updateMatrixWorld(true);target.bind(new THREE.Skeleton(bones));
  const sourceHips=source.bones.find(b=>b.name===names.Hips);sourceHips.updateWorldMatrix(true,false);
  const height=Math.abs(sourceHips.getWorldPosition(new THREE.Vector3()).y)||1;
  const converted=retargetClip(target,source,clip,{names,hip:names.Hips,scale:Math.abs(rig.neutral.Hips.y)/height,fps:30,trim:[0,Math.min(clip.duration,60)],preserveBonePositions:true});
  for(const track of converted.tracks){
    track.name=track.name.replace(/^\.bones\[([^\]]+)\]/,'$1');
    // Keep imported locomotion in the stage. Preserve the vertical hip motion.
    if(track.name==='Hips.position')for(let i=0;i<track.values.length;i+=3){track.values[i]=rig.rest.Hips.p.x;track.values[i+2]=rig.rest.Hips.p.z;}
    if(!Array.from(track.values).every(Number.isFinite))throw new Error('Retargeting produced invalid transforms.');
  }
  target.geometry.dispose();target.material.dispose();return {clip:converted,mapping:names};
}

export class MotionLibrary {
  constructor(head,rig,onState=()=>{}){
    Object.assign(this,{head,rig,onState});this.items=[];this.cache=new Map();this.mixer=new THREE.AnimationMixer(head.armature);this.current=null;this.currentSequence=null;this.onSequence=null;this.clock=0;this.speed=1;this.blend=.6;this.loop=false;this.paused=false;this.request=0;this.mapping={};this.autoIds=['studio-stretch'];this.aliasOverrides={};this.cueOverrides={};this.onCue=()=>{};this.onProgress=()=>{};this.firedCues=new Set();
    const tracks=rig.bodyNames.map(name=>new THREE.QuaternionKeyframeTrack(name+'.quaternion',[0,1],[...rig.rest[name].q.toArray(),...rig.rest[name].q.toArray()]));
    tracks.push(new THREE.VectorKeyframeTrack('Hips.position',[0,1],[...rig.rest.Hips.p.toArray(),...rig.rest.Hips.p.toArray()]));
    this.base=this.mixer.clipAction(new THREE.AnimationClip('neutral',1,tracks));this.base.play();
    this.poseCache=Object.fromEntries(Object.entries(rig.rest).map(([name,value])=>[name,{q:value.q.clone(),p:value.p.clone()}]));
    this.mixer.addEventListener('finished',event=>{if(event.action===this.current){this.stop();this.onState('Movement complete');}});
  }
  get playing(){return !!this.currentSequence||!!this.current||this.fadeUntil>this.clock;}
  get canPause(){return !this.currentSequence;}
  async refresh(){const response=await fetch('/api/motion/library');if(!response.ok)throw new Error('Motion library unavailable.');this.items=(await response.json()).motions;return this.items;}
  async load(id){
    if(this.cache.has(id))return this.cache.get(id);
    const item=this.items.find(x=>x.id===id);if(!item)throw new Error('Choose a library movement.');
    const response=await fetch(item.url);if(!response.ok)throw new Error('Animation asset unavailable.');
    let clips,source=null;
    if(item.format==='sequence'){
      const sequence=validateAnimationSequence(await response.json());
      const entries=[{sequence,clip:{name:sequence.name,duration:sequence.steps.reduce((sum,step)=>sum+step.duration,0)},mapping:{}}];
      this.cache.set(id,entries);return entries;
    }
    if(item.format==='motion')clips=[authoredClip(await response.json(),this.rig)];
    else if(item.format==='bvh'){const result=new BVHLoader().parse(await response.text());clips=[result.clip];source=result.skeleton;}
    else{
      const buffer=await response.arrayBuffer();const manager=new THREE.LoadingManager();manager.setURLModifier(url=>{if(!url.startsWith('blob:')&&!url.startsWith('data:'))throw new Error('External animation resources are blocked.');return url;});
      const gltf=await new GLTFLoader(manager).parseAsync(buffer,'');clips=gltf.animations;
      gltf.scene.traverse(node=>{if(node.isSkinnedMesh&&!source)source=node.skeleton;});
      if(!source){const bones=[];gltf.scene.traverse(node=>{if(this.rig.bones[node.name]||Object.values(this.mapping).includes(node.name))bones.push(node);});source=new THREE.Skeleton(bones);}
      // Animation textures/meshes are never added to the live character scene.
      gltf.scene.traverse(node=>{if(node.isMesh){node.geometry.dispose();for(const material of [node.material].flat())material.dispose();}});
    }
    if(!clips?.length)throw new Error('No animation clips found.');
    const entries=clips.slice(0,20).map(clip=>source?retarget(source,clip,this.rig,this.mapping):{clip,mapping:{}});
    this.cache.set(id,entries);return entries;
  }
  async play(id,index=0,source='instruction'){
    const token=++this.request;const clips=await this.load(id);if(token!==this.request)return null;const entry=clips[index];if(!entry)throw new Error('Choose a clip from this file.');
    if(entry.sequence){this.playSequence(entry.sequence,source);this.currentId=id;return entry;}
    if(this.currentSequence)this.stop();
    const action=this.mixer.clipAction(entry.clip).reset().setEffectiveTimeScale(this.speed).setEffectiveWeight(1);action.clampWhenFinished=true;action.setLoop(this.loop?THREE.LoopRepeat:THREE.LoopOnce,this.loop?Infinity:1);
    const previous=this.current;this.paused=false;action.play();
    if(previous!==action)action.crossFadeFrom(previous||this.base,this.blend,false);this.current=action;this.currentId=id;this.currentSource=source;this.firedCues.clear();this.lastClipTime=0;this.fadeUntil=0;this.onState((source==='persona'?'Persona chose · ':'Playing · ')+entry.clip.name);return entry;
  }
  playSequence(value,source='instruction'){
    const sequence=validateAnimationSequence(value);
    if(typeof this.onSequence!=='function')throw new Error('The animation builder is still preparing the body controller.');
    this.stop();
    const director=this.onSequence({steps:sequence.steps},source);
    if(!director||typeof director.update!=='function'||typeof director.stop!=='function')throw new Error('This animation could not be queued.');
    this.currentSequence={sequence,director,start:director.clock};this.currentSource=source;this.currentId=null;this.fadeUntil=0;this.paused=false;
    this.onState('Playing · '+sequence.name+' · use Stop to end the sequence');return sequence;
  }
  sample(dt){
    // Three's property mixer skips writes for unchanged values. Restore its last
    // desired pose after TalkingHead's pass, including while paused, before sampling.
    for(const [name,value] of Object.entries(this.poseCache)){this.rig.bones[name].quaternion.copy(value.q);this.rig.bones[name].position.copy(value.p);}
    this.mixer.update(dt);
    for(const [name,value] of Object.entries(this.poseCache)){value.q.copy(this.rig.bones[name].quaternion);value.p.copy(this.rig.bones[name].position);}
  }
  seek(seconds){if(this.currentSequence){this.onState('Sequences use Preview and Stop. Timeline seeking is available for imported clips.');return;}if(!this.current||!Number.isFinite(seconds))return;this.current.time=Math.max(0,Math.min(this.current.getClip().duration-.001,seconds));this.sample(0);this.onProgress(this.current.time,this.current.getClip().duration);}
  match(text){
    const value=text.toLowerCase();if(/\b(?:don't|do not|stop|avoid|without)\b/.test(value))return null;
    return this.items.map(item=>({item,words:this.aliasOverrides[item.id]||item.aliases||[]})).filter(({words})=>words.some(word=>word.length>2&&new RegExp('(?:^|\\W)'+word.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'(?:$|\\W)','i').test(value))).sort((a,b)=>Math.max(...b.words.map(x=>x.length))-Math.max(...a.words.map(x=>x.length)))[0]?.item||null;
  }
  stop(){this.request++;if(this.currentSequence){this.currentSequence.director.stop();this.currentSequence=null;}if(this.current){this.current.fadeOut(this.blend);this.base.reset().setEffectiveWeight(1).fadeIn(this.blend).play();this.fadeUntil=this.clock+this.blend;this.current=null;}this.paused=false;}
  update(dt){this.clock+=dt;
    if(this.currentSequence){
      const playing=this.currentSequence,{sequence,director}=playing;
      if(this.paused){this.paused=false;this.onState('Sequences use Preview and Stop. Pause is available for imported clips.');}
      director.update(dt*1000*this.speed);
      const duration=sequence.steps.reduce((sum,step)=>sum+step.duration,0),elapsed=Math.max(0,director.clock-playing.start);
      this.onProgress(Math.min(duration,elapsed),duration);
      if(!director.active&&!director.queue.length){
        if(this.loop){const next=this.onSequence({steps:sequence.steps},this.currentSource);if(!next||typeof next.update!=='function'){this.currentSequence=null;this.onState('Animation stopped.');}else {playing.director=next;playing.start=next.clock;}}
        else {this.currentSequence=null;director.nextDecision=Math.max(director.nextDecision,director.clock+3);this.onState('Animation complete');}
      }
      return;
    }
    if(this.current){this.current.paused=this.paused;this.current.timeScale=this.speed;}this.sample(dt);
    if(this.current){this.onProgress(this.current.time,this.current.getClip().duration);const time=this.current.time;if(time<this.lastClipTime)this.firedCues.clear();const cues=this.cueOverrides[this.currentId]||[];for(const [i,cue] of cues.entries())if(time>=cue.at&&!this.firedCues.has(i)){this.firedCues.add(i);this.onCue(cue);}this.lastClipTime=time;}
  }
  dispose(){this.stop();this.mixer.stopAllAction();this.mixer.uncacheRoot(this.head.armature);this.cache.clear();}
}
