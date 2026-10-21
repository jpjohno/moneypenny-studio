// A restrained resting expression uses the existing authored face shapes.
// Speech, blink and gaze remain owned by TalkingHead; no fixed mouth override.
const warmUpdates=new WeakMap();
const randomLipChannels=new Set([
 'mouthDimpleLeft','mouthDimpleRight','mouthLeft','mouthPressLeft','mouthPressRight',
 'mouthStretchLeft','mouthStretchRight','mouthShrugLower','mouthShrugUpper','mouthRollLower','mouthRollUpper',
]);

function installSpeakingSmile(head){
 if(typeof head.updateMorphTargets!=='function'||warmUpdates.has(head))return;
 const update=head.updateMorphTargets;
 const state={quietMs:0,speechQuietMs:350,randomized:null,filtered:null};
 warmUpdates.set(head,state);
 head.updateMorphTargets=function(dt){
  const elapsed=Math.min(100,Math.max(0,Number(dt)||0));
  const speaking=this.isSpeaking||this.studioSpeechActive;
  state.speechQuietMs=speaking?0:state.speechQuietMs+elapsed;
  // The vendor randomizer can hold lip rolls/presses after they settle. These
  // are not phonemes and can distort PP by several millimetres. During PCM
  // playback and its short drain, random lips yield to the audio owner; named
  // expression tracks and fixed/realtime/system controls keep their priority.
  if(this.studioNeutral&&state.speechQuietMs<350){
   if(!state.randomized&&Array.isArray(this.mtRandomized)){
    const filtered=this.mtRandomized.filter(name=>!randomLipChannels.has(name));
    // TalkingHead expects at least one randomized target. Its normal brow,
    // nose and cheek choices remain; never install an empty picker.
    if(filtered.length){state.randomized=this.mtRandomized;state.filtered=filtered;this.mtRandomized=filtered;}
   }
   const release=1-Math.exp(-elapsed/35);
   for(const key of randomLipChannels){
    const channel=this.mtAvatar?.[key];
    if(!channel||channel.fixed!=null||channel.realtime!=null||channel.system!=null||channel.newvalue!=null||channel.ref)continue;
    const target=Number.isFinite(channel.baseline)?channel.baseline:0;
    const value=(channel.value||0)+(target-(channel.value||0))*release;
    channel.base=null;channel.newvalue=Math.abs(value-target)<.001?target:value;channel.needsUpdate=true;
   }
  }else if(state.randomized){
   if(this.mtRandomized===state.filtered)this.mtRandomized=state.randomized;
   state.randomized=null;state.filtered=null;
  }
  const mouth=this.mtAvatar?.mouthSmile;
  if(this.studioNeutral&&this.mood===this.animMoods?.warm&&mouth){
   // Studio's WAV playback owns isSpeaking, independently of stateName.
   // Wait through short phrase gaps before easing the resting smile back in.
   state.quietMs=speaking?0:state.quietMs+elapsed;
   if(mouth.fixed==null&&mouth.realtime==null&&mouth.system==null){
    const target=speaking||state.quietMs<350?0:.25;
    const duration=target===0?35:550;
    const value=(mouth.value||0)+(target-(mouth.value||0))*(1-Math.exp(-elapsed/duration));
    mouth.newvalue=Math.abs(value-target)<.001?target:value;
    mouth.needsUpdate=true;
   }
  }else state.quietMs=0;
  return update.call(this,dt);
 };
}

export function installWarmExpression(head){
 if(!head.studioNeutral||!head.animMoods?.neutral)return false;
 // Gaze probabilities are callbacks bound to this head. Preserve functions
 // while copying mutable animation arrays/objects; structuredClone rejects them.
 const copy=value=>Array.isArray(value)?value.map(copy):value&&typeof value==='object'?Object.fromEntries(Object.entries(value).map(([key,item])=>[key,copy(item)])):value;
 const mood=copy(head.animMoods.neutral);
 // Animation values are added to baselines by TalkingHead. A nonzero smile
 // baseline used to double the resting smile and remain under every phoneme.
 mood.baseline={...mood.baseline,eyesLookDown:0,mouthSmile:0,cheekSquintLeft:.035,cheekSquintRight:.035};
 // Replacing all named neutral tracks also retires their old queued motions.
 mood.anims=mood.anims.map(animation=>{
  // Retire the old queued mouth motion; the existing morph update below owns
  // only the resting smile, leaving jaw and all speech shapes to lip-sync.
  if(animation.name==='mouth')return {name:'mouth',dt:[1000],vs:{}};
  if(animation.name==='misc')return {name:'misc',delay:1800,dt:[1800],vs:{browDownLeft:[0],browDownRight:[0],browInnerUp:[.035],eyeSquintLeft:[.02],eyeSquintRight:[.02]}};
  if(animation.name==='pose')return {name:'pose',delay:12000,vs:{pose:['straight']}};
  return animation;
 });
 const headMotion=mood.anims.find(animation=>animation.name==='head');
 if(headMotion){
  headMotion.idle={delay:[1200,4500],dt:[[1800,3500]],vs:{bodyRotateX:[[-.015,.035]],bodyRotateY:[[-.09,.09]],bodyRotateZ:[[-.018,.018]]}};
  headMotion.speaking={dt:[[500,1500]],vs:{bodyRotateX:[[-.015,.05]],bodyRotateY:[[-.055,.055]],bodyRotateZ:[[-.015,.015]]}};
 }
 head.animMoods.warm=mood;installSpeakingSmile(head);return true;
}
export function setPersonaMood(head,mood='neutral'){
 const selected=head.studioNeutral&&mood==='neutral'&&head.animMoods?.warm?'warm':mood;
 // Reapplying the same mood replaces every queued blink, gaze and head track
 // in TalkingHead. Adjacent speech phrases must not restart those motions.
 if(head.moodName===selected&&head.mood===head.animMoods?.[selected])return false;
 head.setMood(selected);return true;
}
