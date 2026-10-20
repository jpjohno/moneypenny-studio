import * as THREE from 'three';
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const point=(bone)=>bone.getWorldPosition(new THREE.Vector3());

function aim(bone,from,to){
  if(from.lengthSq()<1e-10||to.lengthSq()<1e-10)return;
  const delta=new THREE.Quaternion().setFromUnitVectors(from.normalize(),to.normalize());
  const world=delta.multiply(bone.getWorldQuaternion(new THREE.Quaternion()));
  bone.quaternion.copy(bone.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(world));
  bone.updateWorldMatrix(false,true);
}

// Geometric two-bone IK: segment lengths never change, the bend plane is explicit,
// and unreachable targets clamp to the physical chain instead of stretching it.
export function solveLimb(upper,lower,end,target,pole){
  upper.updateWorldMatrix(true,true);
  const a=point(upper),b=point(lower),c=point(end),l1=a.distanceTo(b),l2=b.distanceTo(c);
  if(l1<1e-6||l2<1e-6)return {error:Infinity,clamped:true};
  let direction=target.clone().sub(a),requested=direction.length();
  if(requested<1e-6)direction.set(0,-1,0);else direction.divideScalar(requested);
  const distance=clamp(requested,Math.abs(l1-l2)+.0001,l1+l2-.0001);
  const destination=a.clone().addScaledVector(direction,distance);
  const bend=pole.clone().sub(a);bend.addScaledVector(direction,-bend.dot(direction));
  if(bend.lengthSq()<1e-8)bend.set(0,0,1).addScaledVector(direction,-direction.z);
  if(bend.lengthSq()<1e-8)bend.set(1,0,0);
  bend.normalize();
  const along=(l1*l1-l2*l2+distance*distance)/(2*distance);
  const knee=a.clone().addScaledVector(direction,along).addScaledVector(bend,Math.sqrt(Math.max(0,l1*l1-along*along)));
  aim(upper,b.clone().sub(a),knee.sub(a));
  const actualB=point(lower),actualC=point(end);
  aim(lower,actualC.sub(actualB),destination.clone().sub(actualB));
  return {error:point(end).distanceTo(target),clamped:Math.abs(requested-distance)>.002};
}

// Capture before TalkingHead substitutes its own canonical shoulder rotations.
// Imported rigs can use different bone axes even when their names match.
export function authoredNeutral(scene){
  const bones={},rest={};
  scene.traverse(b=>{if(b.isBone)bones[b.name.replaceAll('mixamorig','').replace(/^:/,'')]=b;});
  scene.updateMatrixWorld(true);
  for(const side of ['Left','Right']){
    const upper=bones[side+'Arm'],lower=bones[side+'ForeArm'],hand=bones[side+'Hand'];
    if(!upper||!lower||!hand)continue;
    const start=point(upper),length=start.distanceTo(point(lower))+point(lower).distanceTo(point(hand));
    const sign=side==='Left'?1:-1;
    // The GLB convention is Y up, +Z forward. Leave the clavicles authored;
    // lower the arms with IK instead of guessing local Euler axes.
    const target=start.clone().add(new THREE.Vector3(sign*.12,-.94,.055).multiplyScalar(length));
    solveLimb(upper,lower,hand,target,start.clone().add(new THREE.Vector3(sign*.4,-.3,-.2)));
  }
  for(const [name,bone] of Object.entries(bones))rest[name]={q:bone.quaternion.clone(),p:bone.position.clone()};
  return rest;
}

export class RigController {
  constructor(head,onState=()=>{}){
    this.head=head;this.onState=onState;this.bones={};this.rest={};this.output={};this.targets=new Map();this.smoothing=.12;
    this.root=head.armature;this.origin=this.root.position.clone();this.rootRest=this.root.quaternion.clone();
    this.root.updateMatrixWorld(true);this.space=this.root.matrixWorld.clone();
    this.root.traverse(b=>{if(b.isBone){this.bones[b.name]=b;this.rest[b.name]={q:(head.studioNeutral?.[b.name]?.q||head.poseBase?.props[`${b.name}.quaternion`]||b.quaternion).clone(),p:(head.studioNeutral?.[b.name]?.p||head.poseBase?.props[`${b.name}.position`]||b.position).clone()};}});
    this.bodyNames=Object.keys(this.bones).filter(name=>!['Head','Neck','LeftEye','RightEye'].includes(name));
    this.resetBody();this.root.updateMatrixWorld(true);
    this.neutral={};this.footRotations={};
    for(const name of ['Hips','LeftArm','RightArm','LeftHand','RightHand','LeftFoot','RightFoot','LeftUpLeg','RightUpLeg'])if(this.bones[name]){
      this.neutral[name]=point(this.bones[name]).applyMatrix4(this.space.clone().invert());
      if(name.endsWith('Foot'))this.footRotations[name]=this.bones[name].getWorldQuaternion(new THREE.Quaternion());
    }
    for(const name of this.bodyNames)this.output[name]={q:this.bones[name].quaternion.clone(),p:this.bones[name].position.clone()};
    this.rootOutput={q:this.root.quaternion.clone(),p:this.root.position.clone()};this.lastStatus='';
    this.idleTime=0;this.chestScale=this.bones.Spine2?.scale.clone();
    this.idleEuler=new THREE.Euler();this.idleRotation=new THREE.Quaternion();
  }
  breathe(dt,quiet=false){
    this.idleTime+=Math.max(0,dt);
    const chest=this.bones.Spine2;if(!chest||!this.head.studioNeutral)return;
    // A shorter inhale and longer exhale, with a slight slow change of tempo.
    // Both joins have zero velocity; speaking or gestures never reset the phase.
    const t=this.idleTime,phase=(t/5.2+.18+.012*Math.sin(t*.17))%1;
    const breath=phase<.36?-Math.cos(Math.PI*phase/.36):Math.cos(Math.PI*(phase-.36)/.64);
    chest.scale.copy(this.chestScale);chest.scale.x*=1+.003*breath;chest.scale.z*=1+.004*breath;
    // Ease the quiet/active boundary instead of snapping an idle offset off.
    this.idleBlend=(this.idleBlend??0)+((quiet?0:1)-(this.idleBlend??0))*(1-Math.exp(-Math.max(0,dt)/.6));
    const blend=this.idleBlend;
    const sway=blend*(Math.sin(t*.43)*.004+Math.sin(t*.19+.7)*.002);
    // Keep the pelvis and legs planted. Even a small pelvis rotation moves
    // both feet unless it is followed by contact IK; the torso can settle alone.
    chest.quaternion.multiply(this.idleRotation.setFromEuler(this.idleEuler.set(.002*breath,sway,-sway*.7)));
    for(const [side,phase] of [['Left',0],['Right',1.7]]){
      const arm=this.bones[side+'Arm'],forearm=this.bones[side+'ForeArm'];
      if(arm)arm.quaternion.multiply(this.idleRotation.setFromEuler(this.idleEuler.set(blend*Math.sin(t*.53+phase)*.009,0,0)));
      if(forearm)forearm.quaternion.multiply(this.idleRotation.setFromEuler(this.idleEuler.set(blend*(.006+.004*Math.sin(t*.37+phase)),0,0)));
    }
  }
  resetBody(neutral=true){
    if(neutral||this.head.studioNeutral||this.settling>0)for(const name of this.bodyNames){this.bones[name].quaternion.copy(this.rest[name].q);this.bones[name].position.copy(this.rest[name].p);}
    this.bones.Hips.position.copy(this.rest.Hips.p);
    this.root.position.copy(this.origin);this.root.quaternion.copy(this.rootRest);this.root.updateMatrixWorld(true);
  }
  world(value){return value.clone().applyMatrix4(this.space);}
  setTarget(name,value){
    if(!this.neutral[name])throw new Error('This rig has no '+name+' control.');
    const target=new THREE.Vector3(...value);
    if(!target.toArray().every(Number.isFinite)||target.length()>4)throw new Error('Target is outside the stage.');
    target.y=Math.max(name.endsWith('Foot')?this.neutral[name].y:0,target.y);
    this.targets.set(name,target);return target;
  }
  release(name){this.targets.delete(name);}
  clear(){this.targets.clear();this.onState('Rig targets released');}
  releasePose(){this.settling=.8;}
  setHips(target){
    const b=this.bones.Hips;const local=b.parent.worldToLocal(this.world(target));b.position.copy(local);this.root.updateMatrixWorld(true);
  }
  limb(name,target){
    const side=name.startsWith('Left')?'Left':'Right',leg=name.endsWith('Foot');
    const upper=this.bones[side+(leg?'UpLeg':'Arm')],lower=this.bones[side+(leg?'Leg':'ForeArm')],end=this.bones[name];
    if(!upper||!lower||!end)return {error:Infinity,clamped:true};
    const destination=this.world(target),start=point(upper);
    const pole=leg?start.clone().add(new THREE.Vector3(0,0,1)):start.clone().add(new THREE.Vector3(side==='Left'?.5:-.5,-.4,-.2));
    const result=solveLimb(upper,lower,end,destination,pole);
    if(leg){end.quaternion.copy(end.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(this.footRotations[name]));end.updateWorldMatrix(false,true);}
    return result;
  }
  supportedStep(side='right'){
    const raised=side==='left'?'LeftFoot':'RightFoot',standing=side==='left'?'RightFoot':'LeftFoot';
    const scale=(this.neutral.Hips.y-this.neutral[standing].y)/.9;
    const target=this.neutral[raised].clone().add(new THREE.Vector3(0,.4*scale,.28*scale));
    return {raised,standing,target,height:.4*scale,scale};
  }
  poseSkill(skill,weight,side='right',time=0){
    const hips=this.neutral.Hips.clone(),left=this.neutral.LeftFoot.clone(),right=this.neutral.RightFoot.clone();
    if(!hips||!left||!right)return;
    if(skill==='present'){
      const name=side==='right'?'RightHand':'LeftHand',arm=side==='right'?'RightArm':'LeftArm',sign=side==='right'?-1:1;
      const target=this.neutral[arm].clone().add(new THREE.Vector3(sign*.23,-.13,.23));
      this.limb(name,this.neutral[name].clone().lerp(target,weight));
    }else if(skill==='stretch'){
      for(const [name,sign] of [['LeftHand',1],['RightHand',-1]]){
        const target=this.neutral[name].clone().add(new THREE.Vector3(sign*.08,.08,.06));
        this.limb(name,this.neutral[name].clone().lerp(target,weight));
      }
    }else if(skill==='wave'){
      const name=side==='left'?'LeftHand':'RightHand',arm=side==='left'?'LeftArm':'RightArm',sign=side==='left'?1:-1;
      const target=this.neutral[arm].clone().add(new THREE.Vector3(sign*.12,.12,.15));
      this.limb(name,this.neutral[name].clone().lerp(target,weight));
      const hand=this.bones[name],prefix=name.startsWith('Left')?'Left':'Right',middle=this.bones[prefix+'HandMiddle1'];
      if(middle){
        const original=hand.quaternion.clone();
        // Point the fingers upward in world space, then turn the palm toward
        // the camera. Rotating an arbitrary local wrist axis twisted the hand.
        aim(hand,point(middle).sub(point(hand)),new THREE.Vector3(Math.sin(time*3.2)*.12,1,0));
        const index=this.bones[prefix+'HandIndex1'],pinky=this.bones[prefix+'HandPinky1'];
        if(index&&pinky){
          const fingers=point(middle).sub(point(hand)).normalize();
          const normal=point(index).sub(point(pinky)).cross(fingers).multiplyScalar(prefix==='Right'?-1:1);
          const forward=new THREE.Vector3(0,0,1).addScaledVector(fingers,-fingers.z).normalize();
          if(normal.lengthSq()>1e-8)aim(hand,normal,forward);
        }
        const desired=hand.quaternion.clone();hand.quaternion.copy(original).slerp(desired,weight);hand.updateWorldMatrix(false,true);
      }
    }else if(skill==='bend_forward'){
      const scale=(hips.y-left.y)/.9;
      hips.y-=.04*scale*weight;hips.z-=.12*scale*weight;this.setHips(hips);
      const pelvis=this.bones.Hips,spine=this.bones.Spine;
      const from=point(spine).sub(point(pelvis));
      const direction=this.world(new THREE.Vector3(0,Math.cos(.9*weight),Math.sin(.9*weight))).sub(this.world(new THREE.Vector3()));
      aim(pelvis,from,direction);
      this.limb('LeftFoot',left);this.limb('RightFoot',right);
      for(const [name,sign] of [['LeftHand',1],['RightHand',-1]]){
        const target=this.neutral[name].clone().lerp(new THREE.Vector3(sign*.19*scale,hips.y-.24*scale,.20*scale),weight);
        this.limb(name,target);
      }
    }else if(skill==='supported_step'){
      const step=this.supportedStep(side);
      // Shift towards the supporting leg before lifting, retaining a small
      // bend in both knees. This is a kinematic study, not balance simulation.
      hips.x+=(this.neutral[step.standing].x-hips.x)*.75*weight;
      hips.y-=.025*step.scale*weight;this.setHips(hips);
      this.limb(step.standing,this.neutral[step.standing].clone());
      const raised=this.neutral[step.raised].clone().lerp(step.target,weight);
      raised.y=this.neutral[step.raised].y+step.height*Math.min(1,weight*2)+.05*step.scale*Math.sin(Math.PI*weight);
      this.limb(step.raised,raised);
    }else if(skill==='splits'){
      const drop=hips.y-(left.y+(this.neutral.Hips.y-this.neutral.LeftUpLeg.y)+.035);
      hips.y-=drop*weight;this.setHips(hips);
      for(const [name,target,sign] of [['LeftFoot',left,1],['RightFoot',right,-1]]){
        const side=name.startsWith('Left')?'Left':'Right',a=point(this.bones[side+'UpLeg']),b=point(this.bones[side+'Leg']),c=point(this.bones[name]);
        const length=a.distanceTo(b)+b.distanceTo(c)-.001;
        const upper=this.neutral[side+'UpLeg'];const spread=Math.sqrt(Math.max(0,length*length-.035*.035));
        target.x+=(upper.x+sign*spread-target.x)*weight;
        this.limb(name,target);
        const foot=this.bones[name];const world=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),-Math.PI/2*weight).multiply(this.footRotations[name]);
        foot.quaternion.copy(foot.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(world));foot.updateWorldMatrix(false,true);
      }
      for(const [name,sign] of [['LeftHand',1],['RightHand',-1]]){
        const target=this.neutral[name].clone().lerp(new THREE.Vector3(sign*.31,.18,.12),weight);this.limb(name,target);
      }
    }else if(skill==='sit'||skill==='kneel'){
      hips.y-=(skill==='sit'?.42:.47)*weight;this.setHips(hips);
      for(const [name,target] of [['LeftFoot',left],['RightFoot',right]]){target.z+=(skill==='sit'?.12:-.30)*weight;this.limb(name,target);}
    }else if(skill==='lie_back'){
      const rotation=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),-Math.PI/2*weight);
      this.root.quaternion.copy(this.rootRest).multiply(rotation);
      const pivot=this.neutral.Hips;const offset=pivot.clone().sub(pivot.clone().applyQuaternion(rotation));offset.y-=(pivot.y-.12)*weight;
      this.root.position.copy(this.origin).add(offset);this.root.updateMatrixWorld(true);
      for(const name of ['Head','Neck'])if(this.bones[name])this.bones[name].quaternion.copy(this.rest[name].q);
    }
  }
  update(dt){
    this.settling=Math.max(0,(this.settling||0)-dt);
    if(this.targets.has('Hips'))this.setHips(this.targets.get('Hips'));
    let clamped=false;
    for(const [name,target] of this.targets)if(name!=='Hips')clamped=this.limb(name,target).clamped||clamped;
    const status=clamped?'Target beyond reach · using the nearest reachable position':this.targets.size?`${this.targets.size} rig target${this.targets.size===1?'':'s'} held`:'';
    if(status!==this.lastStatus){this.lastStatus=status;if(status)this.onState(status);}
    const alpha=1-Math.exp(-Math.max(0,dt)/this.smoothing);
    for(const name of this.bodyNames){const bone=this.bones[name],last=this.output[name];last.q.slerp(bone.quaternion,alpha);last.p.lerp(bone.position,alpha);bone.quaternion.copy(last.q);bone.position.copy(last.p);}
    this.rootOutput.q.slerp(this.root.quaternion,alpha);this.rootOutput.p.lerp(this.root.position,alpha);this.root.quaternion.copy(this.rootOutput.q);this.root.position.copy(this.rootOutput.p);this.root.updateMatrixWorld(true);
  }
}
