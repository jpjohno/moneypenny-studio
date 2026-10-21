import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {inflateSync} from 'node:zlib';
import * as THREE from 'three';
import {IRIS_PALETTE,irisPaletteMask,setEyeTone,setHairTone} from '../static/appearance.js';

const eyeName='Adult_Body_Source.high-poly';
function mesh(name,map=new THREE.Texture()){
 const geometry=new THREE.BufferGeometry();
 geometry.setAttribute('position',new THREE.Float32BufferAttribute([0,0,0,1,0,0,0,1,0],3));
 geometry.morphAttributes.position=[new THREE.Float32BufferAttribute([.1,0,0,1.1,0,0,.1,1,0],3)];
 const item=new THREE.Mesh(geometry,new THREE.MeshPhysicalMaterial({name,map}));
 item.morphTargetInfluences=[.37];item.morphTargetDictionary={viseme_PP:0};return item;
}
function shader(){return {uniforms:{},fragmentShader:'void main() {\n#include <map_fragment>\n}'};}

test('iris palette leaves independent pupil and sclera atlas landmarks untouched',()=>{
 // These locations come from the source blue_eye atlas, not the mask formula.
 for(const [u,v] of [[.937,.931],[.299,.704],[.705,.299],[.5,.5],[.16,.7],[.705,.46]])
  assert.equal(irisPaletteMask(u,v),0,`pupil/sclera at ${u},${v}`);
 assert.ok(irisPaletteMask(.35,.704)>.95,'lower iris fibres receive colour');
 assert.ok(irisPaletteMask(.76,.299)>.95,'upper iris fibres receive colour');
 assert.ok(IRIS_PALETTE.gain[2]>IRIS_PALETTE.gain[1],'blue gains more than green');
});

test('eye colour is confined to exact mapped eye material and preserves speech data',()=>{
 const root=new THREE.Group(),eye=mesh(eyeName),skin=mesh('Performance skin — textured'),cornea=mesh('Corneal optical surface'),similar=mesh(eyeName+'.001'),unmapped=mesh(eyeName,null);
 root.add(eye,skin,cornea,similar,unmapped);
 const otherHooks=[skin,cornea,similar,unmapped].map(n=>n.material.onBeforeCompile);
 const geometry=eye.geometry,map=eye.material.map,attributes=eye.geometry.attributes,morphs=eye.geometry.morphAttributes,influences=[...eye.morphTargetInfluences],dictionary=eye.morphTargetDictionary;
 const white=eye.material.color.clone(),alpha=[eye.material.transparent,eye.material.opacity,eye.material.depthWrite];
 setEyeTone(root,'brightblue');const compiled=shader();eye.material.onBeforeCompile(compiled,{});
 assert.equal(compiled.uniforms.moneypennyIrisStrength.value,.85);
 assert.equal(eye.geometry,geometry);assert.equal(eye.geometry.attributes,attributes);assert.equal(eye.geometry.morphAttributes,morphs);
 assert.equal(eye.morphTargetDictionary,dictionary);assert.deepEqual(eye.morphTargetInfluences,influences);
 assert.equal(eye.material.map,map);assert.deepEqual(eye.material.color.toArray(),white.toArray(),'whole eye has no blue tint');
 assert.deepEqual([eye.material.transparent,eye.material.opacity,eye.material.depthWrite],alpha);
 for(const [i,node] of [skin,cornea,similar,unmapped].entries())assert.equal(node.material.onBeforeCompile,otherHooks[i],node.material.name);
});

test('shader keeps prior hooks and cache identity while natural colour restores uniform',()=>{
 const root=new THREE.Group(),eye=mesh(eyeName);root.add(eye);
 const renderer={},hookUniform={value:17};let calls=0;
 eye.material.onBeforeCompile=function(program,receivedRenderer){assert.equal(this,eye.material);assert.equal(receivedRenderer,renderer);program.uniforms.existingHook=hookUniform;calls++;};
 eye.material.customProgramCacheKey=function(){assert.equal(this,eye.material);return 'existing-eye-program';};
 setEyeTone(root,'brightblue');const hook=eye.material.onBeforeCompile,key=eye.material.customProgramCacheKey(),version=eye.material.version;
 const first=shader();eye.material.onBeforeCompile(first,renderer);const strength=first.uniforms.moneypennyIrisStrength;
 assert.equal(first.uniforms.existingHook,hookUniform);assert.ok(key.startsWith('existing-eye-program'));
 assert.equal(first.fragmentShader.split('#include <map_fragment>').length,2,'original map fragment remains once');
 for(const centre of IRIS_PALETTE.centres)assert.ok(first.fragmentShader.includes(`vec2(${centre})`),'GPU uses the published atlas centres');
 assert.ok(first.fragmentShader.includes(`vec3(${IRIS_PALETTE.gain})`),'GPU uses the published gain');
 for(let i=0;i<5;i++){setEyeTone(root,'natural');assert.equal(strength.value,0);setEyeTone(root,'brightblue');assert.equal(strength.value,.85);}
 assert.equal(eye.material.onBeforeCompile,hook,'toggling never stacks shader patches');
 assert.equal(eye.material.customProgramCacheKey(),key);assert.equal(eye.material.version,version,'uniform toggles need no new shader program');
 setEyeTone(root,'natural');const second=shader();eye.material.onBeforeCompile(second,renderer);
 assert.equal(second.uniforms.moneypennyIrisStrength,strength);assert.equal(strength.value,0);assert.equal(calls,2);
});

test('light blonde visibly lifts authored colour without accumulating or touching eyes/skin',()=>{
 const root=new THREE.Group(),hair=mesh('VitHair'),eye=mesh(eyeName),skin=mesh('Performance skin — textured');root.add(hair,eye,skin);
 hair.userData.groom_revision='v39 — approved clothed groom';hair.material.color.setRGB(.78,.88,.72);
 const original=hair.material.color.clone(),eyeColour=eye.material.color.clone(),skinColour=skin.material.color.clone(),map=hair.material.map,geometry=hair.geometry;
 setHairTone(root,'lightblonde');const lighter=hair.material.color.clone();
 assert.ok(lighter.r>original.r+.05&&lighter.g>original.g+.05&&lighter.b>original.b+.10,'visible lift in all colour channels');
 assert.ok(lighter.r/lighter.g<original.r/original.g,'cool the rosy cast rather than brighten it toward pink');
 assert.ok(lighter.toArray().every(v=>v<=1),'no over-white material factors');
 for(let i=0;i<10;i++)setHairTone(root,'lightblonde');assert.deepEqual(hair.material.color.toArray(),lighter.toArray());
 setHairTone(root,'brunette');setHairTone(root,'original');assert.deepEqual(hair.material.color.toArray(),original.toArray());
 assert.equal(hair.material.map,map);assert.equal(hair.geometry,geometry);assert.deepEqual(eye.material.color.toArray(),eyeColour.toArray());assert.deepEqual(skin.material.color.toArray(),skinColour.toArray());
});

// Optional private-asset acceptance: inspect the real UV/colour map instead of
// validating a second hand-written copy of the annulus implementation.
const privateGLB=new URL('../.runtime/character-workshop/Moneypenny-Style-v39.glb',import.meta.url);
function readGLB(){
 const bytes=fs.readFileSync(privateGLB);assert.equal(bytes.readUInt32LE(0),0x46546c67);
 const jsonLength=bytes.readUInt32LE(12),document=JSON.parse(bytes.subarray(20,20+jsonLength).toString());
 const binary=bytes.subarray(28+jsonLength);
 const view=index=>{const v=document.bufferViews[index];return binary.subarray(v.byteOffset||0,(v.byteOffset||0)+v.byteLength);};
 const accessor=index=>{const a=document.accessors[index];assert.equal(a.componentType,5126);const size={VEC2:2,VEC3:3}[a.type],v=document.bufferViews[a.bufferView],data=view(a.bufferView),stride=v.byteStride||size*4;return Array.from({length:a.count},(_,i)=>Array.from({length:size},(_,c)=>data.readFloatLE((a.byteOffset||0)+i*stride+c*4)));};
 return {document,view,accessor};
}
function decodePNG(bytes){
 assert.equal(bytes.subarray(0,8).toString('hex'),'89504e470d0a1a0a');
 let width,height,channels;const compressed=[];
 for(let offset=8;offset<bytes.length;){const size=bytes.readUInt32BE(offset),name=bytes.toString('ascii',offset+4,offset+8),data=bytes.subarray(offset+8,offset+8+size);if(name==='IHDR'){width=data.readUInt32BE(0);height=data.readUInt32BE(4);assert.equal(data[8],8);channels={2:3,6:4}[data[9]];assert.ok(channels);assert.equal(data[12],0,'non-interlaced atlas');}if(name==='IDAT')compressed.push(data);offset+=size+12;}
 const packed=inflateSync(Buffer.concat(compressed)),rowBytes=width*channels,result=Buffer.alloc(width*height*channels);
 const paeth=(a,b,c)=>{const p=a+b-c,pa=Math.abs(p-a),pb=Math.abs(p-b),pc=Math.abs(p-c);return pa<=pb&&pa<=pc?a:pb<=pc?b:c;};
 for(let y=0;y<height;y++)for(let x=0;x<rowBytes;x++){
  const input=y*(rowBytes+1),type=packed[input],at=y*rowBytes+x,left=x>=channels?result[at-channels]:0,up=y?result[at-rowBytes]:0,upperLeft=y&&x>=channels?result[at-rowBytes-channels]:0;
  const prediction=type===0?0:type===1?left:type===2?up:type===3?Math.floor((left+up)/2):type===4?paeth(left,up,upperLeft):NaN;assert.ok(Number.isFinite(prediction));result[at]=(packed[input+1+x]+prediction)&255;
 }
 return {width,height,pixel(u,v){const x=Math.min(width-1,Math.max(0,Math.floor(u*width))),y=Math.min(height-1,Math.max(0,Math.floor(v*height))),i=(y*width+x)*channels;return [result[i],result[i+1],result[i+2]];}};
}

test('real v39 eye UVs colour iris fibres while leaving mapped whites and forward pupils unchanged',{skip:!fs.existsSync(privateGLB)},t=>{
 const {document,view,accessor}=readGLB();
 const material=document.materials.findIndex(m=>m.name===eyeName);assert.ok(material>=0);
 const texture=document.textures[document.materials[material].pbrMetallicRoughness.baseColorTexture.index],image=document.images[texture.source],atlas=decodePNG(view(image.bufferView));
 assert.equal(image.name,'blue_eye');assert.equal(atlas.width,1024);
 let whites=0,iris=0,colouredIris=0,pupils=0;
 for(const mesh of document.meshes)for(const primitive of mesh.primitives){
  if(primitive.material!==material)continue;
  const uv=accessor(primitive.attributes.TEXCOORD_0),position=accessor(primitive.attributes.POSITION);
  for(const [u,v]of uv){const [r,g,b]=atlas.pixel(u,v),weight=irisPaletteMask(u,v);
   if(r>130&&Math.max(r,g,b)-Math.min(r,g,b)<30){whites++;assert.equal(weight,0,`white pixel ${r},${g},${b} at ${u},${v}`);}
   if(b-r>15&&b>65&&g>55){iris++;if(weight>.05)colouredIris++;}
  }
  for(const side of [-1,1])for(const index of position.map((p,i)=>[p,i]).filter(([p])=>p[0]*side>0).sort((a,b)=>b[0][2]-a[0][2]).slice(0,6).map(([,i])=>i)){
   const [u,v]=uv[index],[r,g,b]=atlas.pixel(u,v);assert.ok(Math.max(r,g,b)<35,'forward pole samples actual black pupil');assert.equal(irisPaletteMask(u,v),0);pupils++;
  }
 }
 assert.ok(whites>100,'actual eye mesh has tested white samples');assert.ok(iris>20,'actual eye mesh has tested blue fibres');assert.ok(colouredIris/iris>.7,`${colouredIris}/${iris} blue fibre samples receive colour`);assert.equal(pupils,12);t.diagnostic(`${whites} white UV samples unchanged; ${colouredIris}/${iris} blue fibre UV samples coloured; ${pupils} forward pupil samples unchanged`);
});
