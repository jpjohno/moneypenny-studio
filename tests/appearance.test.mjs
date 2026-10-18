import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {setHairTone,prepareCharacterMaterials} from '../static/appearance.js';
test('hair shade is reversible without cumulative tinting or changing the face',()=>{
 const root=new THREE.Group(),hair=new THREE.Mesh(new THREE.BufferGeometry(),new THREE.MeshStandardMaterial({name:'VitHair',color:'#ffffff'})),face=new THREE.Mesh(new THREE.BufferGeometry(),new THREE.MeshStandardMaterial({name:'skin',color:'#ddaa88'}));root.add(hair,face);
 const skin=face.material.color.clone();setHairTone(root,'darkblonde');const first=hair.material.color.clone();
 for(let i=0;i<10;i++)setHairTone(root,'darkblonde');assert.deepEqual(hair.material.color.toArray(),first.toArray());assert.ok(first.r<1);
 setHairTone(root,'original');assert.deepEqual(hair.material.color.toArray(),[1,1,1]);assert.deepEqual(face.material.color.toArray(),skin.toArray());
});
test('local presentation preserves skin textures, hair masks and facial shapes',()=>{
 const root=new THREE.Group(),map=new THREE.Texture(),normal=new THREE.Texture();
 const skin=new THREE.MeshPhysicalMaterial({name:'Performance skin — textured',map,normalMap:normal,specularIntensity:.64});
 const hair=new THREE.MeshStandardMaterial({name:'VitHair',map,alphaTest:.32});
 const face=new THREE.Mesh(new THREE.BufferGeometry(),skin),strands=new THREE.Mesh(new THREE.BufferGeometry(),hair);
 const cornea=new THREE.Mesh(new THREE.BufferGeometry(),new THREE.MeshPhysicalMaterial({transmission:1}));
 face.morphTargetInfluences=[.4,.7];root.add(face,strands,cornea);
 prepareCharacterMaterials(root,{capabilities:{getMaxAnisotropy:()=>16}});
 assert.equal(face.material,skin);assert.equal(skin.map,map);assert.equal(skin.normalMap,normal);
 assert.deepEqual(face.morphTargetInfluences,[.4,.7]);assert.equal(map.anisotropy,8);
 assert.equal(hair.alphaTest,.32);assert.equal(hair.depthWrite,true);assert.equal(hair.alphaToCoverage,true);
 assert.equal(skin.specularIntensity,.5);assert.ok(face.castShadow&&face.receiveShadow);
 assert.equal(cornea.castShadow,false);assert.equal(cornea.receiveShadow,false);
});
