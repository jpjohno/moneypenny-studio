import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {rig} from './rig-fixture.mjs';
import {RigController,solveLimb} from '../static/rig.js';
import {MotionLibrary,authoredClip,retarget} from '../static/motion-library.js';
const position=b=>b.getWorldPosition(new THREE.Vector3());
test('unreachable IK targets preserve the actual leg segment lengths',()=>{
 const r=new RigController(rig()),a=r.bones.LeftUpLeg,b=r.bones.LeftLeg,c=r.bones.LeftFoot;
 const lengths=[position(a).distanceTo(position(b)),position(b).distanceTo(position(c))];
 const result=solveLimb(a,b,c,new THREE.Vector3(8,0,0),new THREE.Vector3(0,0,1));
 assert.equal(result.clamped,true);assert.ok(Math.abs(lengths[0]-position(a).distanceTo(position(b)))<1e-6);assert.ok(Math.abs(lengths[1]-position(b).distanceTo(position(c)))<1e-6);
});
test('stable body reset prevents accumulated hip-balance feedback',()=>{
 const r=new RigController(rig());
 for(let i=0;i<100;i++){r.bones.Hips.position.y+=.2;r.resetBody();r.update(1/30);}
 assert.ok(r.bones.Hips.position.distanceTo(r.rest.Hips.p)<1e-6);
});
test('splits plant both feet on the floor without changing limb lengths',()=>{
 const r=new RigController(rig());r.poseSkill('splits',1);r.root.updateMatrixWorld(true);
 for(const name of ['LeftFoot','RightFoot']){const foot=position(r.bones[name]);assert.ok(Math.abs(foot.y-r.world(r.neutral[name]).y)<.01,`${name} y=${foot.y}`);}
 assert.ok(position(r.bones.Hips).y<.25);
 for(const name of ['LeftHandMiddle3','RightHandMiddle3'])assert.ok(position(r.bones[name]).y>=0,name+' penetrates floor');
});
test('target interpolation is independent of 30 versus 60 fps',()=>{
 function run(fps){const r=new RigController(rig());r.setTarget('Hips',[0,.7,0]);for(let i=0;i<fps;i++){r.resetBody();r.update(1/fps);}return position(r.bones.Hips);}
 assert.ok(run(30).distanceTo(run(60))<.001);
});
test('animation playback crossfades back to a neutral body',async()=>{
 const head=rig(),r=new RigController(head),library=new MotionLibrary(head,r);
 const data={version:1,name:'bow',duration:2,frames:[{at:0,joints:{Spine:[0,0,0]}},{at:.5,joints:{Spine:[.4,0,0]}},{at:1,joints:{Spine:[0,0,0]}}]};
 library.items=[{id:'test'}];library.cache.set('test',[{clip:authoredClip(data,r),mapping:{}}]);await library.play('test');
 for(let i=0;i<20;i++){r.resetBody();library.update(.04);r.update(.04);}
 library.paused=true;library.seek(1);
 for(let i=0;i<25;i++){r.resetBody();library.update(.04);r.update(.04);}
 assert.ok(r.bones.Spine.quaternion.angleTo(r.rest.Spine.q)>.35,'paused pose was overwritten');
 library.paused=false;
 for(let i=0;i<100;i++){r.resetBody();library.update(.04);r.update(.04);}
 assert.equal(library.playing,false);assert.ok(r.bones.Spine.quaternion.angleTo(r.rest.Spine.q)<.01);
});

test('saved movement words match whole phrases and respect negation',()=>{
 const head=rig(),r=new RigController(head),library=new MotionLibrary(head,r);
 library.items=[{id:'bow',aliases:['take a bow']}];
 assert.equal(library.match('Please take a bow now').id,'bow');assert.equal(library.match("Don't take a bow"),null);assert.equal(library.match('A rainbow'),null);
 library.aliasOverrides.bow=['nod (slowly)'];assert.equal(library.match('Please nod (slowly)').id,'bow');
});
test('wardrobe markers follow the actual clip time and pause with it',async()=>{
 const head=rig(),r=new RigController(head),library=new MotionLibrary(head,r),events=[];
 const clip=authoredClip({version:1,name:'dressing test',duration:2,frames:[{at:0,joints:{Spine:[0,0,0]}},{at:1,joints:{Spine:[0,0,0]}}]},r);
 library.items=[{id:'test'}];library.cache.set('test',[{clip,mapping:{}}]);library.cueOverrides.test=[{at:.5,garment:'waistcoat',visible:false}];library.onCue=cue=>events.push(cue);
 await library.play('test');library.paused=true;library.update(1);assert.equal(events.length,0);
 library.paused=false;library.update(.6);assert.equal(events.length,1);library.update(.1);assert.equal(events.length,1);
});

test('animation retargeting preserves a matching rig and produces usable tracks',()=>{
 const sourceHead=rig(),targetHead=rig(),r=new RigController(targetHead),bones=[];
 sourceHead.armature.traverse(b=>{if(b.isBone)bones.push(b);});
 const source=new THREE.Skeleton(bones),arm=bones.find(b=>b.name==='LeftArm'),q=arm.quaternion.clone(),next=q.clone().multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(.3,0,0)));
 const clip=new THREE.AnimationClip('source arm movement',1,[new THREE.QuaternionKeyframeTrack('LeftArm.quaternion',[0,.5,1],[...q.toArray(),...next.toArray(),...q.toArray()])]);
 const result=retarget(source,clip,r);
 assert.equal(result.mapping.Hips,'Hips');assert.ok(result.clip.tracks.some(track=>track.name==='LeftArm.quaternion'));
 assert.ok(result.clip.tracks.every(track=>Array.from(track.values).every(Number.isFinite)));
});

test('Stop prevents a late animation load from starting playback',async()=>{
 const head=rig(),r=new RigController(head),library=new MotionLibrary(head,r);
 let release;library.load=()=>new Promise(resolve=>{release=resolve;});
 const pending=library.play('late');library.stop();
 release([{clip:authoredClip({version:1,name:'late',duration:2,frames:[{at:0,joints:{Spine:[0,0,0]}},{at:1,joints:{Spine:[.1,0,0]}}]},r)}]);
 await pending;assert.equal(library.current,null);
});

test('the Blender-baked GLB study loads and retargets actual arm movement',async()=>{
 const fs=await import('node:fs');const {GLTFLoader}=await import('three/addons/loaders/GLTFLoader.js');
 const bytes=fs.readFileSync('static/motions/studio-wave.glb'),gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
 let source;gltf.scene.traverse(node=>{if(node.isSkinnedMesh)source=node.skeleton;});assert.ok(source);
 const result=retarget(source,gltf.animations[0],new RigController(rig()));
 const arm=result.clip.tracks.find(track=>track.name==='RightArm.quaternion'),first=new THREE.Quaternion().fromArray(arm.values,0);
 let largest=0;for(let i=0;i<arm.values.length;i+=4)largest=Math.max(largest,first.angleTo(new THREE.Quaternion().fromArray(arm.values,i)));
 assert.ok(largest>.2,`baked arm motion ${largest}`);
});

test('authored neutral retains clavicles and survives upstream idle pose overrides',async()=>{
 const {authoredNeutral}=await import('../static/rig.js');
 const head=rig(),shoulder=head.armature.getObjectByName('LeftShoulder');
 const authored=shoulder.quaternion.clone();
 const upper=head.armature.getObjectByName('LeftArm'),fore=head.armature.getObjectByName('LeftForeArm'),hand=head.armature.getObjectByName('LeftHand');
 const lengths=[position(upper).distanceTo(position(fore)),position(fore).distanceTo(position(hand))];
 head.studioNeutral=authoredNeutral(head.armature);
 assert.ok(shoulder.quaternion.angleTo(authored)<1e-7);
 assert.ok(position(hand).y<position(upper).y-.3,'arm does not hang beside torso');
 assert.ok(Math.abs(position(upper).distanceTo(position(fore))-lengths[0])<1e-6);
 assert.ok(Math.abs(position(fore).distanceTo(position(hand))-lengths[1])<1e-6);
 head.poseBase={props:{'LeftShoulder.quaternion':new THREE.Quaternion().setFromEuler(new THREE.Euler(1.6,0,1.7))}};
 const r=new RigController(head);
 for(let frame=0;frame<120;frame++){
  shoulder.quaternion.copy(head.poseBase.props['LeftShoulder.quaternion']);
  r.resetBody(false);r.update(1/60);
 }
 assert.ok(shoulder.quaternion.angleTo(authored)<1e-7,'generic shoulder pose returned while idle');
});

test('breathing remains bounded and continuous across quiet and moving states',async()=>{
 const {authoredNeutral}=await import('../static/rig.js');
 const head=rig();head.studioNeutral=authoredNeutral(head.armature);const r=new RigController(head),base=r.chestScale.clone();
 for(let i=0;i<600;i++){
  r.resetBody(false);r.breathe(1/60,i>300);r.update(1/60);
  assert.ok(Math.abs(r.bones.Spine2.scale.x/base.x-1)<=.00301);
  assert.ok(Math.abs(r.bones.Spine2.scale.z/base.z-1)<=.00401);
 }
 assert.ok(Math.abs(r.idleTime-10)<1e-6);
});

test('procedural motion shares the authored neutral instead of generic shoulder axes',async()=>{
 const {authoredNeutral}=await import('../static/rig.js');const {MotionDirector}=await import('../static/motion.js');
 const head=rig();head.studioNeutral=authoredNeutral(head.armature);
 head.poseBase={props:{'LeftShoulder.quaternion':new THREE.Quaternion().setFromEuler(new THREE.Euler(1.6,0,1.7))}};
 const r=new RigController(head),motion=new MotionDirector(head,()=>{},r);
 motion.animatePose({LeftShoulder:[0,0,0]},1);
 assert.ok(r.bones.LeftShoulder.quaternion.angleTo(r.rest.LeftShoulder.q)<1e-7);
});

test('local wave lifts one hand without imposing a generic pose on both shoulders',async()=>{
 const {authoredNeutral}=await import('../static/rig.js');const head=rig();head.studioNeutral=authoredNeutral(head.armature);const r=new RigController(head);
 const left=position(r.bones.LeftHand),shoulders=['LeftShoulder','RightShoulder'].map(n=>r.bones[n].quaternion.clone());
 r.poseSkill('wave',1,'right',1);
 assert.ok(position(r.bones.RightHand).y>r.world(r.neutral.RightHand).y+.25);
 assert.ok(position(r.bones.LeftHand).distanceTo(left)<1e-6);
 ['LeftShoulder','RightShoulder'].forEach((n,i)=>assert.deepEqual(r.bones[n].quaternion.toArray(),shoulders[i].toArray()));
});
