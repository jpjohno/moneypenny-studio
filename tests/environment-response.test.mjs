import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import {WebGLMaterials} from 'three/src/renderers/webgl/WebGLMaterials.js';
import {prepareCharacterMaterials} from '../static/appearance.js';
const renderer={capabilities:{getMaxAnisotropy:()=>4}};
function fixture(){
 const root=new THREE.Group(),names=['Performance skin — textured','Studio crepe blouse','VitHair','Adult_Body_Source.high-poly','Corneal optical surface'];
 const meshes=names.map(name=>{const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute([0,0,0],3));geometry.morphAttributes.position=[new THREE.Float32BufferAttribute([.05,0,0],3)];const mesh=new THREE.Mesh(geometry,new THREE.MeshPhysicalMaterial({name,map:new THREE.Texture(),normalMap:new THREE.Texture(),roughness:.6,alphaTest:name==='VitHair'?.25:0,transmission:name==='Corneal optical surface'?1:0}));mesh.morphTargetInfluences=[.45];root.add(mesh);return mesh;});
 return {root,meshes,skin:meshes[0].material,cloth:meshes[1].material};
}
function refresh(material,environment){
 const uniforms=THREE.UniformsUtils.clone(THREE.ShaderLib.physical.uniforms);
 uniforms.envMapIntensity.value=.75;
 // Run the pinned Three implementation. It sees the existing scene map in both
 // cases; an explicit material envMap decides whether its local scalar uploads.
 WebGLMaterials({}, {get:()=>({envMap:environment,envMapRotation:new THREE.Euler()})}).refreshMaterialUniforms(uniforms,material,1,600,null);
 return uniforms;
}
test('existing shared room map makes skin/fabric strengths reach actual Three uniforms',()=>{
 const inherited=fixture(),explicit=fixture(),environment=new THREE.Texture();environment.mapping=THREE.CubeUVReflectionMapping;
 prepareCharacterMaterials(inherited.root,renderer);
 assert.equal(inherited.skin.envMap,null);assert.equal(inherited.skin.envMapIntensity,.8);
 assert.equal(refresh(inherited.skin,environment).envMapIntensity.value,.75,'without explicit map, the old material scalar never uploads');
 prepareCharacterMaterials(explicit.root,renderer,environment);
 for(const [material,intensity]of[[explicit.skin,.62],[explicit.cloth,.3]]){
  assert.equal(material.envMap,environment,'reuse the scene map itself, not a clone');const uniforms=refresh(material,environment);
  assert.equal(uniforms.envMap.value,environment);assert.equal(uniforms.envMapIntensity.value,intensity);
 }
});
test('environment response preserves geometry/mouth targets/maps and eye/hair/glass response',()=>{
 const baseline=fixture(),updated=fixture(),environment=new THREE.Texture(),before=updated.meshes.map(mesh=>({geometry:mesh.geometry,positions:mesh.geometry.attributes.position.array.slice(),morphs:mesh.geometry.morphAttributes,map:mesh.material.map,normal:mesh.material.normalMap}));
 prepareCharacterMaterials(baseline.root,renderer);prepareCharacterMaterials(updated.root,renderer,environment);
 updated.meshes.forEach((mesh,index)=>{const old=before[index];assert.equal(mesh.geometry,old.geometry);assert.deepEqual(mesh.geometry.attributes.position.array,old.positions);assert.equal(mesh.geometry.morphAttributes,old.morphs);assert.deepEqual(mesh.morphTargetInfluences,[.45]);assert.equal(mesh.material.map,old.map);assert.equal(mesh.material.normalMap,old.normal);});
 for(const index of[2,3,4]){
  const a=baseline.meshes[index].material,b=updated.meshes[index].material;
  for(const field of['envMap','envMapIntensity','alphaTest','transparent','opacity','depthWrite','transmission','clearcoat','roughness'])assert.equal(b[field],a[field],`${b.name} ${field}`);
  assert.deepEqual(b.color.toArray(),a.color.toArray());
 }
});
test('shared room texture survives material teardown and repeated preparation',()=>{
 const h=fixture(),environment=new THREE.Texture();let disposals=0;environment.addEventListener('dispose',()=>disposals++);
 prepareCharacterMaterials(h.root,renderer,environment);prepareCharacterMaterials(h.root,renderer,environment);
 assert.equal(h.skin.envMap,environment);assert.equal(h.cloth.envMap,environment);
 h.skin.dispose();h.cloth.dispose();assert.equal(disposals,0,'material ownership must never dispose the scene environment');
});
