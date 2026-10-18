import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {setHairTone} from '../static/appearance.js';
test('hair shade is reversible without cumulative tinting or changing the face',()=>{
 const root=new THREE.Group(),hair=new THREE.Mesh(new THREE.BufferGeometry(),new THREE.MeshStandardMaterial({name:'VitHair',color:'#ffffff'})),face=new THREE.Mesh(new THREE.BufferGeometry(),new THREE.MeshStandardMaterial({name:'skin',color:'#ddaa88'}));root.add(hair,face);
 const skin=face.material.color.clone();setHairTone(root,'darkblonde');const first=hair.material.color.clone();
 for(let i=0;i<10;i++)setHairTone(root,'darkblonde');assert.deepEqual(hair.material.color.toArray(),first.toArray());assert.ok(first.r<1);
 setHairTone(root,'original');assert.deepEqual(hair.material.color.toArray(),[1,1,1]);assert.deepEqual(face.material.color.toArray(),skin.toArray());
});
