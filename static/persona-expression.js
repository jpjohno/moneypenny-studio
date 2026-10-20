// A restrained resting expression uses the existing authored face shapes.
// Speech, blink and gaze remain owned by TalkingHead; no fixed mouth override.
export function installWarmExpression(head){
 if(!head.studioNeutral||!head.animMoods?.neutral)return false;
 // Gaze probabilities are callbacks bound to this head. Preserve functions
 // while copying mutable animation arrays/objects; structuredClone rejects them.
 const copy=value=>Array.isArray(value)?value.map(copy):value&&typeof value==='object'?Object.fromEntries(Object.entries(value).map(([key,item])=>[key,copy(item)])):value;
 const mood=copy(head.animMoods.neutral);
 mood.baseline={...mood.baseline,eyesLookDown:0,mouthSmile:.28,cheekSquintLeft:.035,cheekSquintRight:.035};
 // Replacing all named neutral tracks also retires their old queued motions.
 mood.anims=mood.anims.map(animation=>{
  if(animation.name==='mouth')return {name:'mouth',idle:{delay:2000,dt:[2000,2200],vs:{mouthSmile:[[.23,.3]],mouthPucker:[0],mouthRollLower:[0],mouthRollUpper:[0]}}};
  if(animation.name==='misc')return {name:'misc',delay:1800,dt:[1800],vs:{browDownLeft:[0],browDownRight:[0],browInnerUp:[.035],eyeSquintLeft:[.02],eyeSquintRight:[.02]}};
  if(animation.name==='pose')return {name:'pose',delay:12000,vs:{pose:['straight']}};
  return animation;
 });
 const headMotion=mood.anims.find(animation=>animation.name==='head');
 if(headMotion){
  headMotion.idle={delay:[1200,4500],dt:[[1800,3500]],vs:{bodyRotateX:[[-.015,.035]],bodyRotateY:[[-.09,.09]],bodyRotateZ:[[-.018,.018]]}};
  headMotion.speaking={dt:[[500,1500]],vs:{bodyRotateX:[[-.015,.05]],bodyRotateY:[[-.055,.055]],bodyRotateZ:[[-.015,.015]]}};
 }
 head.animMoods.warm=mood;return true;
}
export function setPersonaMood(head,mood='neutral'){
 head.setMood(head.studioNeutral&&mood==='neutral'&&head.animMoods?.warm?'warm':mood);
}
