import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {Wardrobe} from '../static/wardrobe.js';
test('a multi-material garment is one controllable group with all its child meshes',()=>{
 const armature=new THREE.Group(),garment=new THREE.Group();garment.name='Blouse';garment.userData.wardrobeSlot='outer';
 garment.add(new THREE.Mesh(),new THREE.Mesh());armature.add(garment);
 const wardrobe=new Wardrobe({armature});assert.deepEqual(wardrobe.garments().map(x=>x.id),['Blouse']);
 wardrobe.setGarment('Blouse',false);assert.equal(garment.visible,false);
 wardrobe.setGarment('Blouse',true);assert.equal(garment.visible,true);
});

test('blouse palettes use matte fabric and preserve body materials',()=>{
 const armature=new THREE.Group(),blouse=new THREE.MeshPhysicalMaterial({name:'Studio crepe blouse',sheen:1}),skin=new THREE.MeshStandardMaterial({name:'Performance skin',color:'#d6b29c'});
 armature.add(new THREE.Mesh(new THREE.BoxGeometry(),blouse),new THREE.Mesh(new THREE.BoxGeometry(),skin));
 const wardrobe=new Wardrobe({armature}),before=skin.color.getHex();wardrobe.setPalette('navy');
 assert.equal(blouse.color.getHexString(),'26384e');assert.equal(blouse.sheen,.12);assert.equal(blouse.roughness,.9);assert.equal(skin.color.getHex(),before);
});
