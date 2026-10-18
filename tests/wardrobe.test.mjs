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
