import * as THREE from 'three';

export const MOTION_SKILLS=['reach','wave','jig','dance','walk','turn','stretch','bow','sit','kneel','lie_back','splits','supported_step','bend_forward','idle','custom','present'];
const ease=x=>x*x*(3-2*x);
const clamp=(x,a,b)=>Math.min(b,Math.max(a,x));

// A body director runs after TalkingHead's face/body pass. Speech and movement
// remain separate: a persona can move without having to generate spoken text.
export class MotionDirector {
  constructor(head,onState=()=>{},rig=null) {
    this.rig=rig;
    this.head=head;this.onState=onState;this.bones={};this.rest={};this.queue=[];this.active=null;this.clock=0;this.nextDecision=6;
    this.origin=head.armature.position.clone();this.rootRotation=head.armature.quaternion.clone();
    head.armature.traverse(bone=>{if(bone.isBone){this.bones[bone.name]=bone;this.rest[bone.name]=(rig?.rest[bone.name]?.q||head.studioNeutral?.[bone.name]?.q||head.poseBase?.props[`${bone.name}.quaternion`]||bone.quaternion).clone();}});
    this.hipsPosition=this.bones.Hips.position.clone();this.autonomous=true;this.activity=.45;this.persona='';this.engaged=false;
    this.height=head.avatarHeight||1.75;
    this.onChoosePlan=null;this.planning=false;this.heading=0;this.currentHeading=0;this.nextStepAt=null;
  }
  stop(){this.queue=[];this.nextStepAt=null;if(this.active){this.active.release=this.clock;this.active.frozenHeading=this.currentHeading;this.heading=this.currentHeading;}this.nextDecision=this.clock+5;}
  resetPlacement(){this.queue=[];this.active=null;this.nextStepAt=null;this.heading=0;this.currentHeading=0;this.head.armature.quaternion.copy(this.rootRotation);this.head.armature.position.copy(this.origin);this.nextDecision=this.clock+5;}
  plan(plan,source='instruction') {
    if(!plan?.steps?.length)return false;
    if(['conversation','persona'].includes(source)&&[this.active,...this.queue].some(step=>step&&!['conversation','persona'].includes(step.source)))return false;
    this.stop();this.active=null;
    this.queue=plan.steps.filter(x=>MOTION_SKILLS.includes(x.skill)).map(x=>({...x,duration:clamp(Number(x.duration)||4,1,20),intensity:clamp(Number(x.intensity)||.6,.1,1),source}));
    this.nextStepAt=this.clock;
    return !!this.queue.length;
  }
  animatePose(pose,weight) {
    for(const [name,angles] of Object.entries(pose)){
      const bone=this.bones[name];if(!bone||!this.rest[name])continue;
      const rotation=new THREE.Quaternion().setFromEuler(new THREE.Euler(...angles));
      const desired=this.rest[name].clone().multiply(rotation);
      bone.quaternion.slerp(desired,weight);
    }
  }
  bodyTarget(target,side) {
    const b=this.bones;const sign=side==='left'?1:-1;
    const ref={shoulder:side==='left'?'RightArm':'LeftArm',head:'Head',chin:'Head',ear:'Head',nose:'Head',chest:'Spine2',belly:'Spine',hip:'Hips',knee:side==='left'?'LeftLeg':'RightLeg'}[target]||'Spine';
    const point=b[ref].getWorldPosition(new THREE.Vector3());
    const forward=new THREE.Vector3(0,0,1).applyQuaternion(this.head.armature.getWorldQuaternion(new THREE.Quaternion()));
    point.addScaledVector(forward,this.height*({belly:.073,chest:.075,chin:.045,nose:.078,ear:.035,head:.035,hip:.075,knee:.045,shoulder:.018}[target]||.04));
    if(target==='belly')point.y-=this.height*.012;
    if(target==='head')point.y+=this.height*.065;
    if(target==='chin')point.y+=this.height*.015;
    if(target==='nose')point.y+=this.height*.055;
    if(target==='ear'){point.x+=sign*this.height*.04;point.y+=this.height*.055;}
    return point;
  }
  reach(target,side,weight) {
    const prefix=side==='left'?'Left':'Right';
    const hand=this.bones[prefix+'Hand'];if(!hand)return;
    const end=this.bones[prefix+'HandMiddle1']||hand;
    const chain=[...(end!==hand?[hand]:[]),this.bones[prefix+'ForeArm'],this.bones[prefix+'Arm'],this.bones[prefix+'Shoulder']].filter(Boolean);
    this.head.armature.updateMatrixWorld(true);
    const destination=this.bodyTarget(target,side);
    const start=end.getWorldPosition(new THREE.Vector3());destination.lerpVectors(start,destination,weight);
    for(let iteration=0;iteration<18;iteration++){
      for(const joint of chain){
        const origin=joint.getWorldPosition(new THREE.Vector3());
        const from=end.getWorldPosition(new THREE.Vector3()).sub(origin).normalize();
        const to=destination.clone().sub(origin).normalize();
        const delta=new THREE.Quaternion().setFromUnitVectors(from,to);
        const local=joint.parent.getWorldQuaternion(new THREE.Quaternion()).invert()
          .multiply(delta.multiply(joint.getWorldQuaternion(new THREE.Quaternion())));
        joint.quaternion.slerp(local,.65);joint.updateWorldMatrix(false,true);
      }
      if(end.getWorldPosition(new THREE.Vector3()).distanceTo(destination)<.008)break;
    }
    this.reachError=end.getWorldPosition(new THREE.Vector3()).distanceTo(this.bodyTarget(target,side));
  }
  autonomousChoice() {
    const playful=/play|dance|jig|lively|expressive|energetic/i.test(this.persona);
    const choices=playful&&this.activity>.65?['dance','jig','turn','stretch','walk']:['idle','present','idle','stretch','turn'];
    let skill=choices[Math.floor(Math.random()*choices.length)];
    if(skill===this.lastAutonomousSkill&&skill!=='idle')skill='idle';
    this.lastAutonomousSkill=skill;
    const side=this.lastPresentationSide==='left'?'right':'left';
    if(skill==='present')this.lastPresentationSide=side;
    this.queue=[{skill,side,duration:skill==='idle'?3:5+Math.random()*3,intensity:playful&&this.activity>.65?.25+this.activity*.4:.12+this.activity*.2,source:'persona'}];
    this.nextStepAt=this.clock;
  }
  applyHeading(heading){
    const root=this.head.armature,yaw=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),heading);
    const relative=this.rootRotation.clone().invert().multiply(root.quaternion);
    root.quaternion.copy(this.rootRotation).multiply(yaw).multiply(relative);
    const offset=root.position.clone().sub(this.origin).applyQuaternion(yaw);
    root.position.copy(this.origin).add(offset);this.currentHeading=heading;
  }
  beginStep(start){
    this.active={...this.queue.shift(),start};this.nextStepAt=null;
    this.onState(`${this.active.source==='persona'?'Persona chose':'Moving'} · ${this.active.skill.replaceAll('_',' ')}`);
  }
  update(milliseconds) {
    // This is elapsed animation time, not a physics integration step. Dropping
    // time above 100 ms made a busy 5 fps stage play at half speed. Evaluate the
    // final pose once, carrying any elapsed time across queued step boundaries.
    const dt=Number.isFinite(milliseconds)?Math.max(0,milliseconds)/1000:0;
    const previousClock=this.clock;this.clock+=dt;
    if(this.engaged&&this.active?.source==='persona'&&this.active.release===undefined)this.stop();
    if(!this.active&&this.queue.length)this.beginStep(this.nextStepAt??previousClock);
    while(this.active&&this.clock+1e-9>=this.active.start+this.active.duration){
      const completed=this.active,end=completed.start+completed.duration;
      const directTurn=completed.skill==='turn'&&!['persona','conversation'].includes(completed.source);
      this.heading=(completed.frozenHeading??(this.heading+(directTurn?Math.PI:0)))%(Math.PI*2);
      this.active=null;this.rig?.releasePose();
      if(this.queue.length)this.beginStep(end);
      else {this.nextStepAt=null;this.onState(this.autonomous?'Persona movement enabled':'Movement paused');}
    }
    if(!this.active){
      this.head.armature.position.copy(this.origin);this.head.armature.quaternion.copy(this.rootRotation);this.applyHeading(this.heading);
      if(this.autonomous&&!this.engaged&&this.clock>=this.nextDecision){
        this.autonomousChoice();this.nextDecision=this.clock+12+(1-this.activity)*25;
        if(this.onChoosePlan&&!this.planning){this.planning=true;Promise.resolve(this.onChoosePlan()).finally(()=>{this.planning=false;});}
      }
      return;
    }
    const a=this.active,t=this.clock-a.start,p=clamp(t/a.duration,0,1),k=a.intensity;
    const deliberate=['supported_step','bend_forward'].includes(a.skill);
    // Quick gestures respond promptly. Short authored steps still reach their
    // pose instead of spending their whole duration in overlapping fades.
    const fade=Math.min(deliberate?1.2:.38,a.duration*(deliberate?.4:.25)),releaseTime=deliberate?1.2:.4;
    let w=ease(clamp(t/fade,0,1))*ease(clamp((a.duration-t)/fade,0,1));
    if(a.release!==undefined)w*=1-ease(clamp((this.clock-a.release)/releaseTime,0,1));
    const pose={};let root=new THREE.Euler(),offset=new THREE.Vector3();
    const set=(name,x=0,y=0,z=0)=>{pose[name]=[x,y,z];};
    const beat=Math.sin(t*Math.PI*3.4),other=Math.sin(t*Math.PI*3.4+Math.PI);
    switch(a.skill){
      case 'jig':case 'dance': {
        const jig=a.skill==='jig',rate=jig?1: .55;
        const cycle=Math.sin(t*Math.PI*3.4*rate),opposite=-cycle;
        set('Hips',0,.15*cycle*k,.08*cycle*k);set('Spine',0,0,-.07*cycle*k);
        set('LeftUpLeg',-.35*Math.max(0,cycle)*k,0,.1*k);set('RightUpLeg',-.35*Math.max(0,opposite)*k,0,-.1*k);
        set('LeftLeg',.65*Math.max(0,opposite)*k);set('RightLeg',.65*Math.max(0,cycle)*k);
        set('LeftArm',-.2*k,0,-(.25+.25*cycle)*k);set('RightArm',-.2*k,0,(.25-.25*cycle)*k);
        set('LeftForeArm',-.7*k);set('RightForeArm',-.7*k);
        offset.y=Math.abs(cycle)*.045*k;offset.x=Math.sin(t*2)*.055*k;root.y=Math.sin(t*.8)*.22*k;break;
      }
      case 'walk':set('LeftUpLeg',beat*.35*k);set('RightUpLeg',other*.35*k);set('LeftLeg',Math.max(0,-beat)*.55*k);set('RightLeg',Math.max(0,beat)*.55*k);set('LeftArm',other*.22*k);set('RightArm',beat*.22*k);offset.y=Math.abs(beat)*.015;offset.x=Math.sin(p*Math.PI*2)*.22*k;break;
      case 'turn':if(['persona','conversation'].includes(a.source))root.y=Math.sin(p*Math.PI)*.45*k;break;
      case 'stretch':if(!this.head.studioNeutral){set('LeftArm',-.2,0,-1.75*k);set('RightArm',-.2,0,1.75*k);}set('Spine',-.06*k,0,.025*Math.sin(t)*k);break;
      case 'bow':set('Spine',.55*k);set('Spine1',.25*k);set('Head',.15*k);break;
      case 'sit':break;
      case 'kneel':break;
      case 'lie_back':break;
      case 'splits':break;
      case 'supported_step':case 'bend_forward':case 'wave':case 'present':break;
      case 'reach':break;
      case 'custom': {
        const frames=a.frames||[];
        const right=frames.findIndex(f=>f.at>=p);const end=frames[right<0?frames.length-1:right],start=frames[Math.max(0,right-1)]||end;
        if(start&&end){const u=ease(clamp((p-start.at)/Math.max(.001,end.at-start.at),0,1));for(const name of new Set([...Object.keys(start.joints),...Object.keys(end.joints)])){const x=start.joints[name]||[0,0,0],y=end.joints[name]||[0,0,0];pose[name]=x.map((v,i)=>v+(y[i]-v)*u);}}break;
      }
      default:set('Spine',0,Math.sin(t*.7)*.035*k,Math.sin(t*.9)*.025*k);
    }
    this.animatePose(pose,w);
    const q=this.rootRotation.clone().multiply(new THREE.Quaternion().setFromEuler(root));
    this.head.armature.quaternion.copy(this.rootRotation).slerp(q,w);
    this.head.armature.position.copy(this.origin).addScaledVector(offset,w);
    if(this.rig&&['splits','sit','kneel','lie_back','supported_step','bend_forward','wave','present'].includes(a.skill))this.rig.poseSkill(a.skill,a.skill==='present'?w*k:w,a.side,t);
    if(this.rig&&this.head.studioNeutral&&a.skill==='stretch')this.rig.poseSkill('stretch',w*k);
    if(a.skill==='reach')this.reach(a.target,a.side,w);
    const directTurn=a.skill==='turn'&&!['persona','conversation'].includes(a.source);
    const heading=a.frozenHeading??(this.heading+(directTurn?Math.PI*ease(clamp(t/Math.max(.2,a.duration-.3),0,1)):0));
    this.applyHeading(heading);
    this.head.armature.updateMatrixWorld(true);
    if(p>=1||a.release!==undefined&&this.clock-a.release>releaseTime){this.heading=heading%(Math.PI*2);this.active=null;this.rig?.releasePose();this.onState(this.autonomous?'Persona movement enabled':'Movement paused');}
  }
}

// The authored character resets generic upstream body poses each frame. Queue
// speaking gestures in its own director so they survive that reset, while
// imported characters can retain TalkingHead's original gesture implementation.
export function queueConversationGesture(director,performance={},movement=.5){
  if(!director?.head?.studioNeutral)return false;
  const amount=Number(movement),gesture=typeof performance.gesture==='string'?performance.gesture.trim().toLowerCase():'';
  if(!Number.isFinite(amount)||amount<=.2||(!gesture&&amount<=.45))return false;
  const pending=[director.active,...director.queue].filter(Boolean);
  if(pending.some(step=>!['persona','conversation'].includes(step.source)))return false;
  // One response may arrive in many speech phrases. Keep the current eased
  // movement instead of repeatedly restarting its fade-in on every phrase.
  if(pending.some(step=>step.source==='conversation'&&step.release===undefined))return true;
  const side=director.lastConversationSide==='left'?'right':'left';
  // Finger-specific hints such as thumbup/ok are acknowledged with a supported
  // open palm; this does not claim those individual finger poses are authored.
  const accepted=director.plan({steps:[{skill:'present',side,duration:3,
    intensity:.18+.16*clamp(amount,0,1)}]},'conversation');
  if(accepted)director.lastConversationSide=side;
  return accepted;
}

export function movementFromText(value) {
  const lower=value.toLowerCase(),found=[];
  if(/\b(?:don't|do not|avoid|without|stop)\b/.test(lower))return null;
  const duration=lower.match(/(?:for|hold)\s+(\d+)\s*seconds?/);
  const bend=lower.match(/\bbend\s+(?:over|forward|down)\b/);
  if(bend)found.push({at:bend.index,step:{skill:'bend_forward',duration:duration?clamp(Number(duration[1]),1,20):8,intensity:1}});
  const step=lower.match(/\b(?:(?:put|place|rest|raise|lift)\s+(?:(?:your|her|my|one|the)\s+)?(?:(left|right)\s+)?(?:foot|leg)|one\s+(?:foot|leg))\s+(?:up\s+)?on\s+(?:(?:the|a|toilet|closed)\s+)*(?:seat|step|stool|lid)\b/);
  if(step)found.push({at:step.index,step:{skill:'supported_step',side:step[1]||'right',duration:duration?clamp(Number(duration[1]),1,20):8,intensity:1}});
  for(const match of lower.matchAll(/(?:touch|rest|place|put|reach)[^.?!]{0,45}?(shoulder|belly button|belly|navel|head|chin|chest|hip|knee|ear|nose)/g))found.push({at:match.index,step:{skill:'reach',target:/belly|navel/.test(match[1])?'belly':match[1],side:match[0].includes('left hand')?'left':'right',duration:duration?clamp(Number(duration[1]),1,20):5}});
  for(const [pattern,skill] of [[/\bwave\b/,'wave'],[/\bjig\b/,'jig'],[/\bdanc(?:e|ing)\b/,'dance'],[/\bsplits\b/,'splits'],[/lie.*back|lying.*back/,'lie_back'],[/\bkneel/,'kneel'],[/\bsit\b/,'sit'],[/\bstretch/,'stretch'],[/\bwalk/,'walk'],[/turn around|\bspin\b/,'turn'],[/\bbow\b/,'bow']]){
    const match=lower.match(pattern);if(match&&!(skill==='dance'&&found.some(x=>x.step.skill==='jig')))found.push({at:match.index,step:{skill,duration:duration?clamp(Number(duration[1]),1,20):['jig','dance','walk'].includes(skill)?10:6,intensity:.8}});
  }
  return found.length?{steps:found.sort((a,b)=>a.at-b.at).slice(0,8).map(x=>x.step)}:null;
}
