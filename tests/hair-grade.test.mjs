import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {HAIR_ROSE_GRADE,hairRoseMask,hairRoseGrade,setHairTone} from '../static/appearance.js';
const luma=rgb=>rgb.reduce((sum,value,index)=>sum+value*HAIR_ROSE_GRADE.luma[index],0);
function fixture(name='VitHair',revision='v39 — reviewed clothed groom'){
 const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute([0,0,0],3));geometry.morphAttributes.position=[new THREE.Float32BufferAttribute([.1,0,0],3)];
 const material=new THREE.MeshPhysicalMaterial({name,map:new THREE.Texture(),alphaTest:.25,transparent:false,depthWrite:true});material.color.setRGB(.78,.88,.72);
 const node=new THREE.Mesh(geometry,material);node.userData.groom_revision=revision;node.morphTargetInfluences=[.4];const root=new THREE.Group();root.add(node);return {root,node,material};
}
const program=()=>({uniforms:{},fragmentShader:'void main(){\n#include <map_fragment>\n}'});
test('rose correction preserves luminance and keeps neutral and warm-brown fibres intact',()=>{
 const brown=[.30,.11,.055],grey=[.5,.5,.5],rose=[.46,.10,.11];
 assert.equal(hairRoseMask(...brown),0);assert.equal(hairRoseMask(...grey),0);assert.ok(hairRoseMask(...rose)>.75);
 assert.deepEqual(hairRoseGrade(brown),brown);assert.deepEqual(hairRoseGrade(grey),grey);assert.deepEqual(hairRoseGrade(rose,0),rose);
 const graded=hairRoseGrade(rose);assert.ok(graded[0]-graded[1]<rose[0]-rose[1],'rose dominance is reduced');assert.ok(Math.abs(luma(graded)-luma(rose))<1e-12,'brightness is retained instead of adding a bright patch');
});
test('only the selected light-blonde reviewed groom is graded, with reversible uniform changes',()=>{
 const h=fixture();setHairTone(h.root,'lightblonde');const shader=program();h.material.onBeforeCompile(shader,{});const strength=shader.uniforms.moneypennyHairRoseStrength,hook=h.material.onBeforeCompile,key=h.material.customProgramCacheKey(),version=h.material.version;
 assert.equal(strength.value,1);for(const tone of ['original','brunette','warm','darkblonde']){setHairTone(h.root,tone);assert.equal(strength.value,0,tone);setHairTone(h.root,'lightblonde');assert.equal(strength.value,1);}
 assert.equal(h.material.onBeforeCompile,hook);assert.equal(h.material.customProgramCacheKey(),key);assert.equal(h.material.version,version,'colour switches reuse the program');
 for(const other of [fixture('Performance skin'),fixture('VitHair','v38 — original'),fixture('Other imported hair')]){const hook=other.material.onBeforeCompile;setHairTone(other.root,'lightblonde');assert.equal(other.material.onBeforeCompile,hook);}
});
test('hair grading preserves alpha mask, original atlas, geometry and morph values',()=>{
 const h=fixture(),map=h.material.map,geometry=h.node.geometry,positions=geometry.getAttribute('position').array.slice(),morphs=geometry.morphAttributes,colour=h.material.color.clone();
 setHairTone(h.root,'lightblonde');const shader=program();h.material.onBeforeCompile(shader,{});
 assert.equal(h.material.map,map);assert.equal(h.node.geometry,geometry);assert.equal(geometry.morphAttributes,morphs);assert.deepEqual(geometry.getAttribute('position').array,positions);assert.deepEqual(h.node.morphTargetInfluences,[.4]);
 assert.equal(h.material.alphaTest,.25);assert.equal(h.material.transparent,false);assert.equal(h.material.depthWrite,true);
 assert.ok(shader.fragmentShader.includes('diffuseColor.rgb=mix('));assert.ok(!shader.fragmentShader.includes('diffuseColor.a='),'shader never overwrites alpha');
 setHairTone(h.root,'original');assert.deepEqual(h.material.color.toArray(),colour.toArray());
});
test('hair grade retains earlier material hooks and includes its published colour calibration',()=>{
 const h=fixture(),existing={value:2},renderer={};let called=0;
 h.material.onBeforeCompile=function(shader,r){assert.equal(this,h.material);assert.equal(r,renderer);shader.uniforms.existing=existing;called++;};h.material.customProgramCacheKey=()=> 'prior-hair';
 setHairTone(h.root,'lightblonde');const shader=program();h.material.onBeforeCompile(shader,renderer);
 assert.equal(shader.uniforms.existing,existing);assert.equal(called,1);assert.ok(h.material.customProgramCacheKey().startsWith('prior-hair|'));
 assert.ok(shader.fragmentShader.includes(`vec3(${HAIR_ROSE_GRADE.gain})`));assert.ok(shader.fragmentShader.includes(`smoothstep(${HAIR_ROSE_GRADE.blueGreen},`));assert.equal(shader.fragmentShader.split('#include <map_fragment>').length,2);
});
